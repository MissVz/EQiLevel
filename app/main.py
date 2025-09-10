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
from app.api.v1.session_router import router as session_router
from app.api.v1.turn_logger_router import router as turn_logger_router

from app.db.schema import Turn
from app.models import TurnRequest, TurnContext, TutorReply, MCP
from app.services import emotion, mcp, policy, tutor, reward, storage
from app.services.metrics import compute_metrics
from app.services.storage import SessionLocal, db_health, init_db

from fastapi import FastAPI, UploadFile, Depends, status, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from contextlib import asynccontextmanager
from src.audio.transcribe_to_json import transcribe_audio
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
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*",
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

# ================================= GETs =============================
@app.get("/health")  # (optional) keep a super-light liveness root if you want backward compatibility
def health_root():
    return {"status": "ok"}


# -------- Serve built SPA (if present) and root redirect --------
try:
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    if os.path.isdir(web_dir):
        app.mount("/web", StaticFiles(directory=web_dir, html=True), name="web")
except Exception as _e:
    # Don't fail API startup if web assets are missing
    pass


@app.get("/", include_in_schema=False)
def root_redirect():
    # Prefer web UI if built; otherwise docs
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    target = "/web" if os.path.isdir(web_dir) else "/docs"
    return RedirectResponse(target)

@app.get("/metrics")
def metrics(session_id: Optional[str] = None):
    """
    Telemetry dashboard; optional session_id narrows to one learner/session.
    Example:
      /metrics
      /metrics?session_id=s1
    """
    return compute_metrics(session_id)

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
async def session_turn(request: Request, file: UploadFile = File(None), session_id: int = Form(None), user_text: str = Form(None)):
    # Support both JSON (text turns) and multipart/form-data (audio uploads)
    transcript = None
    # If JSON body, extract fields
    try:
        ct = request.headers.get("content-type", "")
        if "application/json" in ct:
            payload = await request.json()
            user_text = payload.get("user_text")
            session_id = payload.get("session_id")
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

    # 1) analyze
    em = emotion.classify(text_input)
    perf = emotion.estimate_perf(text_input)
    # 2) build MCP
    r = reward.compute(em, perf)
    mcp_state = mcp.build(em, perf, text_input)
    # 3) policy update
    mcp_updated = policy.update(mcp_state, r)
    # 4) tutor reply
    try:
        text = tutor.generate(text_input, mcp_updated)
        if not text or not str(text).strip():
            text = "[Tutor] Let’s try a simpler example together."
    except Exception as gen_err:
        print(f"[session] Tutor error: {gen_err}")
        text = "[Tutor] Quick hint: try a smaller step — we’ll fix generation next."
    # 5) persist safely EVERYTHING including reward
    try:
        # Build a TurnRequest for logging
        req_obj = TurnRequest(user_text=text_input, session_id=session_id)
        storage.log_turn_full(req_obj, em, perf, mcp_updated, text, reward=float(r))
    except Exception as log_err:
        print(f"[storage] Logging failed: {log_err}")
    return TutorReply(text=text, mcp=mcp_updated, reward=float(r))

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
            return JSONResponse(content=transcript_json)
        return JSONResponse(content={"error": "Transcript not found."}, status_code=500)
    finally:
        os.remove(tmp_path)
