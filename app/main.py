# app/main.py
import os
from dotenv import load_dotenv

# Load .env before any imports that read env vars (like storage.py)
load_dotenv()

import tempfile
import json

from app.api.v1.admin_router import router as admin_router
from app.api.v1.debug_router import router as debug_router
from app.api.v1.emotion_router import router as emotion_router
from app.api.v1.health_router import router as health_router
from app.api.v1.metrics_router import router as metrics_router
from app.api.v1.objectives_router import router as objectives_router
from app.api.v1.users_router import router as users_router
from app.api.v1.settings_router import router as settings_router
from app.api.v1.session_router import router as session_router
from app.api.v1.turn_logger_router import router as turn_logger_router

from app.db.schema import Turn
from app.models import TurnRequest, TurnContext, TutorReply, MCP
from app.services import emotion, mcp, policy, tutor, reward, storage
from app.services.metrics import compute_metrics
from app.services.storage import SessionLocal, db_health, init_db, dialogue_messages, get_user_for_session
from app.services import objectives as objsvc

from fastapi import FastAPI, UploadFile, Depends, status, File, Form, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
import re
from src.audio.transcribe_to_json import transcribe_audio
import time
import asyncio
from typing import Optional



@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"[startup] DATABASE_URL set?: {'yes' if os.getenv('DATABASE_URL') else 'no'}")
    print(f"[startup] OPENAI_API_KEY loaded?: {'yes' if os.getenv('OPENAI_API_KEY') else 'no'}")
    try:
        from app.services import emotion as emotion_svc
        device = emotion_svc.get_emotion_model_device()
        print(f"[startup] Emotion model device: {device}")
        rt = emotion_svc.torch_runtime_info()
        print(
            "[startup] Torch runtime: torch={torch}, torchaudio={torchaudio}, "
            "speechbrain={speechbrain}, cuda_available={cuda_available}, "
            "cuda_device_count={cuda_device_count}, device_name={device_name}".format(**rt)
        )
    except Exception as e:
        print(f"[startup] Emotion model device check failed: {e}")
    yield

app = FastAPI(title="EQiLevel API", lifespan=lifespan)

# (Optional) CORS – keep origins tight for your front end(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Include routers
app.include_router(admin_router)
app.include_router(debug_router)
app.include_router(emotion_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(session_router)
app.include_router(turn_logger_router)
app.include_router(objectives_router)
app.include_router(users_router)
app.include_router(settings_router)

# ================================= GETs =============================
@app.get("/health")  # (optional) keep a super-light liveness root if you want backward compatibility
def health_root():
    return {"status": "ok"}


# -------- Serve built SPA (if present) and root redirect --------
try:
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    if os.path.isdir(web_dir):
        app.mount("/web", StaticFiles(directory=web_dir, html=True), name="web")
        index_html = os.path.join(web_dir, "index.html")
        def _serve_spa_index():
            try:
                return FileResponse(index_html)
            except Exception:
                # Fallback to docs if index is missing
                return RedirectResponse("/docs")
        # Map top-level SPA routes to the built index so client routing works
        for path in ("/session", "/chat", "/admin", "/metrics", "/settings"):
            app.add_api_route(path, _serve_spa_index, include_in_schema=False, name=f"spa_{path.strip('/')}")
    # Serve favicon if present
    fav_path = os.path.join(os.path.dirname(__file__), "favicon.ico")
    if os.path.isfile(fav_path):
        @app.get("/favicon.ico", include_in_schema=False)
        def _favicon():
            return FileResponse(fav_path, media_type="image/x-icon")
except Exception as _e:
    # Don't fail API startup if web assets are missing
    pass


@app.get("/", include_in_schema=False)
def root_redirect():
    # Prefer web UI if built; otherwise docs
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    target = "/web" if os.path.isdir(web_dir) else "/docs"
    return RedirectResponse(target)

# NOTE: Public UI also uses client-side route "/metrics". The API variant
# lives under /api/v1/metrics (see metrics_router). The direct /metrics
# endpoint here was removed to avoid conflicting with the SPA route.

# ================================= POSTs =============================
@app.post("/analyze")
def analyze(req: TurnRequest):
    em = emotion.classify(req.user_text)                  # -> EmotionSignals
    perf = emotion.estimate_perf(req.user_text)           # optional
    return {"emotion": em.model_dump(), "performance": perf.model_dump()}

@app.post("/echo")
def echo(req: TurnRequest):
    return {"ok": True, "user_text": req.user_text, "session_id": req.session_id}

@app.post("/mcp/build", response_model=MCP)
def build_mcp(ctx: TurnContext):
    return mcp.build(ctx.emotion, ctx.performance, ctx.transcript)

@app.post("/policy/step", response_model=MCP)
def policy_step(ctx: TurnContext):
    r = reward.compute(ctx.emotion, ctx.performance)      # perf + emotion
    new_mcp = policy.update(ctx.mcp, r)                   # Q-learning step
    storage.log_reward(ctx, r, new_mcp)
    return new_mcp

@app.post("/tutor/reply", response_model=TutorReply)
def tutor_reply(ctx: TurnContext):
    text = tutor.generate(ctx.transcript, ctx.mcp)        # GPT-4o with MCP
    r = reward.compute(ctx.emotion, ctx.performance)
    storage.log_turn(ctx, text, r)
    return TutorReply(text=text, mcp=ctx.mcp, reward=r)


# Updated /session endpoint: accepts audio (optional), transcribes if present, then proceeds as before
@app.post(
    "/session",
    responses={
        200: {
            "description": "Tutor reply with updated MCP and reward signal.",
            "content": {
                "application/json": {
                    "example": {
                        "text": "Let's try a simpler example: 1/2 + 1/3 = 5/6. Want to give it a go?",
                        "mcp": {
                            "emotion": {"label": "frustrated", "sentiment": -0.4},
                            "performance": {"correct": None, "attempts": None, "time_to_solve_sec": None, "accuracy_pct": None},
                            "learning_style": {"visual": 0.0, "auditory": 0.0, "reading_writing": 0.0, "kinesthetic": 0.0},
                            "tone": "warm",
                            "pacing": "slow",
                            "difficulty": "down",
                            "style": "mixed",
                            "next_step": "example"
                        },
                        "reward": 0.45
                    }
                }
            },
        }
    },
    status_code=status.HTTP_200_OK,
)
async def session_turn(request: Request, file: UploadFile = File(None), session_id: int = Form(None), user_text: str = Form(None), objective_code: str = Form(None), chat_history_turns: int = Form(None)):
    # Support both JSON (text turns) and multipart/form-data (audio uploads)
    transcript = None
    # If JSON body, extract fields
    hist_lim = None
    try:
        ct = request.headers.get("content-type", "")
        if "application/json" in ct:
            payload = await request.json()
            user_text = payload.get("user_text")
            session_id = payload.get("session_id")
            try:
                h = payload.get("chat_history_turns")
                if isinstance(h, (int, float)):
                    hist_lim = int(h)
                elif isinstance(h, str) and h.strip().isdigit():
                    hist_lim = int(h.strip())
            except Exception:
                pass
    except Exception:
        pass
    if file is not None:
        # Save uploaded file to temp, transcribe
        file_bytes = await file.read()
        print(f"[audio debug] Received file: {file.filename}, size: {len(file_bytes)} bytes")
        print(f"[audio debug] First 100 bytes: {file_bytes[:100]}")
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        print(f"[audio debug] Temp WAV file saved at: {tmp_path}")
        try:
            output_dir = tempfile.mkdtemp()
            transcript = None
            detected_language = None
            # Try English first
            try:
                transcribe_audio(tmp_path, output_dir=output_dir, language="en")
            except Exception as whisper_err:
                print(f"[whisper] Transcription error (en): {whisper_err}")
                import traceback
                traceback.print_exc()
            for fname in os.listdir(output_dir):
                if fname.endswith("_transcript.json"):
                    with open(os.path.join(output_dir, fname), "r", encoding="utf-8") as f:
                        transcript_json = json.load(f)
                        detected_language = transcript_json.get('language')
                        print(f"[whisper] Detected language (en): {detected_language}")
                        transcript = transcript_json.get("text", "")
                    break
            # If transcript is empty, try Spanish
            if not transcript or not transcript.strip():
                print("[whisper] Empty transcript with English, retrying with Spanish...")
                try:
                    transcribe_audio(tmp_path, output_dir=output_dir, language="es")
                except Exception as whisper_err:
                    print(f"[whisper] Transcription error (es): {whisper_err}")
                    import traceback
                    traceback.print_exc()
                for fname in os.listdir(output_dir):
                    if fname.endswith("_transcript.json"):
                        with open(os.path.join(output_dir, fname), "r", encoding="utf-8") as f:
                            transcript_json = json.load(f)
                            detected_language = transcript_json.get('language')
                            print(f"[whisper] Detected language (es): {detected_language}")
                            transcript = transcript_json.get("text", "")
                        break
        finally:
            # Do not delete tmp_path so user can inspect it
            print(f"[audio debug] Temp WAV file retained for inspection: {tmp_path}")
    # If no audio, try to get user_text from form
    if transcript:
        text_input = transcript
    elif user_text:
        text_input = user_text
    else:
        text_input = ""
        session_id = None

    # Enforce required fields: session_id and objective_code; user bound to session
    if session_id is None:
        raise HTTPException(status_code=400, detail="session_id is required")
    # Determine objective from JSON/form parsed below
    oc_candidate = objective_code
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            payload = await request.json()
            oc_candidate = payload.get("objective_code")
    except Exception:
        pass
    if not oc_candidate or not str(oc_candidate).strip():
        raise HTTPException(status_code=400, detail="objective_code is required")
    # Verify session has a user
    try:
        bound = get_user_for_session(int(session_id))
    except Exception:
        bound = None
    if bound is None:
        raise HTTPException(status_code=400, detail="username is required: start session with user_name before sending turns")

    # 1) analyze
    em = emotion.classify(text_input)
    perf = emotion.estimate_perf(text_input)
    # 2) build MCP
    r = reward.compute(em, perf)
    mcp_state = mcp.build(em, perf, text_input)
    # 3) preliminary policy update (pre-reply)
    mcp_pre = policy.update(mcp_state, r)
    # 4) tutor reply
    try:
        hist = []
        try:
            if session_id is not None:
                _env_lim = int(os.getenv("CHAT_HISTORY_TURNS", "8"))
                _lim = max(1, min(20, int(hist_lim if hist_lim is not None else (chat_history_turns if chat_history_turns is not None else _env_lim))))
                hist = dialogue_messages(int(session_id), limit=_lim)
        except Exception as _:
            pass
        # Optional curriculum objective per-turn (JSON body only)
        objectives = []
        try:
            oc = None
            if request.headers.get("content-type", "").startswith("application/json"):
                payload = await request.json()
                oc = payload.get("objective_code")
            else:
                oc = objective_code
            if oc:
                o = objsvc.find_by_code(str(oc))
                if o:
                    objectives = [o]
        except Exception:
            pass
        text = tutor.generate(text_input, mcp_pre, history=hist, objectives=objectives)
        if not text or not str(text).strip():
            text = "[Tutor] Let’s try a simpler example together."
    except Exception as gen_err:
        print(f"[session] Tutor error: {gen_err}")
        text = "[Tutor] Quick hint: try a smaller step — we’ll fix generation next."
    # 4b) reward shaping with reply + final policy update
    r2 = reward.shape_with_reply(r, mcp_pre, text)
    mcp_updated = policy.update(mcp_state, r2)
    # 5) persist safely EVERYTHING including reward
    try:
        # Build a TurnRequest for logging
        req_obj = TurnRequest(user_text=text_input, session_id=session_id)
        # include objective code if provided
        try:
            oc_for_log = None
            if request.headers.get("content-type", "").startswith("application/json"):
                payload = await request.json()
                oc_for_log = payload.get("objective_code")
            else:
                oc_for_log = objective_code
        except Exception:
            oc_for_log = None
        storage.log_turn_full(req_obj, em, perf, mcp_updated, text, reward=float(r2), objective_code=oc_for_log)
    except Exception as log_err:
        print(f"[storage] Logging failed: {log_err}")
    return TutorReply(text=text, mcp=mcp_updated, reward=float(r2), transcript=text_input)

# Transcribe endpoint
@app.post("/transcribe")
def transcribe(file: UploadFile = File(...)):
    # Save uploaded file to a temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name
    # Run transcription (output_dir is temp, return result directly)
    try:
        output_dir = tempfile.mkdtemp()
        transcript = None
        detected_language = None
        transcript_json = None
        # Try English first
        transcribe_audio(tmp_path, output_dir=output_dir, language="en")
        for fname in os.listdir(output_dir):
            if fname.endswith("_transcript.json"):
                with open(os.path.join(output_dir, fname), "r", encoding="utf-8") as f:
                    transcript_json = json.load(f)
                    detected_language = transcript_json.get('language')
                    print(f"[whisper] Detected language (en): {detected_language}")
                    transcript = transcript_json.get("text", "")
                break
        # If transcript is empty, try Spanish
        if not transcript or not transcript.strip():
            print("[whisper] Empty transcript with English, retrying with Spanish...")
            transcribe_audio(tmp_path, output_dir=output_dir, language="es")
            for fname in os.listdir(output_dir):
                if fname.endswith("_transcript.json"):
                    with open(os.path.join(output_dir, fname), "r", encoding="utf-8") as f:
                        transcript_json = json.load(f)
                        detected_language = transcript_json.get('language')
                        print(f"[whisper] Detected language (es): {detected_language}")
                        transcript = transcript_json.get("text", "")
                    break
        if transcript:
            # Return full JSON from Whisper if available; otherwise a minimal payload
            return JSONResponse(content=transcript_json or {
                "text": transcript,
                "language": detected_language,
                "audio_file": file.filename,
            })
        else:
            return JSONResponse(content={"error": "Transcript not found."}, status_code=500)
    finally:
        os.remove(tmp_path)


# ============================ WebSocket: /ws/voice =============================
# Whisper model cache for streaming partials
_ws_whisper_model = None
_fw_model = None  # optional faster-whisper

def _sanitize_partial_text(text: str) -> str:
    """
    Make partial transcripts more stable/compact:
    - collapse whitespace
    - limit repetitive phrases like "thank you"
    - clamp to a manageable size (last ~220 chars) to avoid UI growth
    """
    if not text:
        return ""
    t = str(text).strip()
    if not t:
        return ""
    # Normalize whitespace
    t = re.sub(r"\s+", " ", t)
    # Collapse excessive "thank you" hallucinations
    t = re.sub(r"(?i)(?:\bthank you\b[.!?,;:]?\s*){3,}", "Thank you. ", t)
    # Avoid unbounded growth: keep tail which tends to contain the latest words
    if len(t) > 220:
        t = t[-220:]
    return t


def _should_emit_partial(new_text: str, last_text: str) -> bool:
    """Only emit if there is meaningful progress."""
    if not new_text:
        return False
    if not last_text:
        return True
    if new_text == last_text:
        return False
    # If new text only extends a little, skip to reduce spam
    if new_text.startswith(last_text) and (len(new_text) - len(last_text) < 8):
        return False
    return True


def _quick_transcribe_text(audio_path: str, language: str = "en") -> str:
    """Lightweight helper for partials; reuses a cached Whisper model."""
    global _ws_whisper_model, _fw_model
    try:
        # Try faster-whisper first for lower latency (optional dependency)
        try:
            from faster_whisper import WhisperModel  # type: ignore
            import torch  # type: ignore
            if _fw_model is None:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
                _fw_model = WhisperModel("base", device=device, compute_type=compute_type)
            segments, info = _fw_model.transcribe(audio_path, language=language)
            text = " ".join(seg.text.strip() for seg in segments)
            if text.strip():
                return text.strip()
        except Exception:
            pass
        import whisper, torch  # type: ignore
        if _ws_whisper_model is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _ws_whisper_model = whisper.load_model("base", device=device)
        result = _ws_whisper_model.transcribe(audio_path, language=language)
        return str(result.get("text", "")).strip()
    except Exception as _e:
        return ""


@app.websocket("/ws/voice")
async def ws_voice(websocket: WebSocket):
    """
    Minimal streaming stub: client sends small audio/webm chunks while recording.
    On stop (client sends {"event":"stop"}), we run Whisper transcription on the
    buffered file and return both the transcript and a tutor reply using the same
    pipeline as /session. This lays groundwork for incremental decoding later.
    """
    await websocket.accept()
    tmp_path = None
    output_dir = None
    session_id = None
    hist_lim = None
    ws_objective = None
    try:
        # Parse query params: ?session_id=123
        try:
            query = websocket.query_params
            if query and "session_id" in query:
                sid = query.get("session_id")
                if isinstance(sid, str) and sid.strip().isdigit():
                    session_id = int(sid)
            # Optional: ?hist=12 or ?chat_history_turns=12
            if query and ("hist" in query or "chat_history_turns" in query):
                h = query.get("hist") or query.get("chat_history_turns")
                if isinstance(h, str) and h.strip().isdigit():
                    hist_lim = max(1, min(20, int(h.strip())))
            # Optional objective code
            if query and "objective_code" in query:
                ws_objective = query.get("objective_code")
        except Exception:
            pass

        await websocket.send_json({"type": "ready"})

        # Enforce required params for streaming as well
        if session_id is None:
            await websocket.send_json({"type": "error", "message": "session_id is required"})
            try: await websocket.close()
            except Exception: pass
            return
        if not ws_objective or not str(ws_objective).strip():
            await websocket.send_json({"type": "error", "message": "objective_code is required"})
            try: await websocket.close()
            except Exception: pass
            return
        try:
            if get_user_for_session(int(session_id)) is None:
                await websocket.send_json({"type": "error", "message": "username is required: start session with user_name before streaming"})
                try: await websocket.close()
                except Exception: pass
                return
        except Exception:
            pass

        # Prepare a temp file to append chunks
        fd, tmp_path = tempfile.mkstemp(suffix=".webm")
        os.close(fd)
        output_dir = tempfile.mkdtemp()

        last_partial_ts = 0.0
        partial_task: asyncio.Task | None = None
        last_bytes_at = 0.0
        started_at = 0.0  # set on first bytes
        last_partial_sent: str = ""
        last_partial_at = 0.0

        # Fail-safe timeouts configurable via env
        MAX_STREAM_SECONDS = float(os.getenv("STREAM_MAX_SECONDS", "25"))
        STALE_PARTIAL_SECONDS = float(os.getenv("STREAM_STALE_PARTIAL_SECONDS", "10"))

        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=3.0)
            except asyncio.TimeoutError:
                # If we've received audio and there has been silence for a while, finalize automatically
                try:
                    has_audio = os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0
                except Exception:
                    has_audio = False
                if has_audio and (time.time() - last_bytes_at) > 2.5:
                    # Synthesize a stop event
                    msg = {"text": json.dumps({"event": "stop"})}
                else:
                    # No data yet; keep waiting
                    continue
            if msg.get("type") == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
                # Append bytes to tmp file
                with open(tmp_path, "ab") as f:
                    f.write(msg["bytes"])
                last_bytes_at = time.time()
                if started_at == 0.0:
                    started_at = last_bytes_at
                # Throttled partial transcription every ~1.2s
                now = time.time()
                if (now - last_partial_ts) >= 1.2 and (partial_task is None or partial_task.done()):
                    loop = asyncio.get_running_loop()
                    async def _do_partial():
                        nonlocal last_partial_sent, last_partial_at
                        try:
                            text = await loop.run_in_executor(None, lambda: _quick_transcribe_text(tmp_path, "en"))
                            text = _sanitize_partial_text(text)
                            if _should_emit_partial(text, last_partial_sent):
                                last_partial_sent = text
                                last_partial_at = time.time()
                                try:
                                    await websocket.send_json({"type": "partial", "text": text})
                                except Exception:
                                    pass
                        except Exception:
                            # Swallow partial decode errors to avoid noisy task exceptions
                            pass
                    partial_task = asyncio.create_task(_do_partial())
                    last_partial_ts = now
                continue
            if "text" in msg and msg["text"]:
                try:
                    data = json.loads(msg["text"])
                except Exception:
                    data = {"event": msg["text"]}
                ev = data.get("event")
                # Extra server-side failsafes:
                #  - Max stream duration (25s)
                #  - No new partial for 10s while having audio -> finalize
                if started_at and (time.time() - started_at) > MAX_STREAM_SECONDS:
                    ev = "stop"
                if (not ev) and last_partial_at and (time.time() - last_partial_at) > STALE_PARTIAL_SECONDS and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                    ev = "stop"

                if ev == "stop":
                    # Run transcription and reply
                    transcript = ""
                    try:
                        transcribe_audio(tmp_path, output_dir=output_dir, language="en")
                        transcript_json = None
                        for fname in os.listdir(output_dir):
                            if fname.endswith("_transcript.json"):
                                with open(os.path.join(output_dir, fname), "r", encoding="utf-8") as f:
                                    transcript_json = json.load(f)
                                    break
                        if transcript_json:
                            transcript = transcript_json.get("text", "")
                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": f"transcribe failed: {e}"})

                    # Build reply using same pipeline with reward shaping
                    em = emotion.classify(transcript)
                    perf = emotion.estimate_perf(transcript)
                    r = reward.compute(em, perf)
                    mcp_state = mcp.build(em, perf, transcript)
                    mcp_pre = policy.update(mcp_state, r)
                    try:
                        hist = []
                        try:
                            if session_id is not None:
                                _lim = hist_lim if hist_lim is not None else int(os.getenv("CHAT_HISTORY_TURNS", "8"))
                                hist = dialogue_messages(int(session_id), limit=_lim)
                        except Exception:
                            pass
                        text = tutor.generate(transcript, mcp_pre, history=hist)
                        if not text or not str(text).strip():
                            text = "[Tutor] Let’s try a simpler example together."
                    except Exception as gen_err:
                        print(f"[ws/session] Tutor error: {gen_err}")
                        text = "[Tutor] Quick hint: try a smaller step — we’ll fix generation next."

                    # Persist full turn (best-effort)
                    try:
                        r2 = reward.shape_with_reply(r, mcp_pre, text)
                        mcp_updated = policy.update(mcp_state, r2)
                        req_obj = TurnRequest(user_text=transcript, session_id=session_id)
                        storage.log_turn_full(req_obj, em, perf, mcp_updated, text, reward=float(r2), objective_code=ws_objective)
                    except Exception as log_err:
                        print(f"[ws/storage] Logging failed: {log_err}")

                    await websocket.send_json({
                        "type": "final",
                        "transcript": transcript,
                        "reply": {"text": text, "mcp": mcp_updated.model_dump(), "reward": float(r2)}
                    })
                    try:
                        await websocket.close()
                    except Exception:
                        pass
                    break
                else:
                    # Unknown event; ignore
                    pass
    except WebSocketDisconnect:
        pass
    finally:
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        try:
            if output_dir and os.path.isdir(output_dir):
                # leave for debugging if desired
                pass
        except Exception:
            pass
