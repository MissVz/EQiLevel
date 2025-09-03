# app/main.py
import os
from app.db.schema import Turn
from app.models import TurnRequest, TurnContext, TutorReply, MCP
from app.services import emotion, mcp, policy, tutor, reward, storage
from app.services.metrics import compute_metrics
from app.services.storage import SessionLocal
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional

load_dotenv()

print(f"[startup] OPENAI_API_KEY loaded?: {'yes' if os.getenv('OPENAI_API_KEY') else 'no'}")

app = FastAPI(title="EQiLevel API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    try:
        storage.init_db()
        print("[startup] Database initialized successfully.")
    except Exception as e:
        print(f"[startup] Database initialization FAILED: {e}")

# ================================= GETs =============================
@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/health/full")
def health_full():
    # OpenAI key check
    key_ok = bool(os.getenv("OPENAI_API_KEY"))

    # DB check
    db_ok, db_err = storage.db_health()

    overall_ok = key_ok and db_ok
    payload = {
        "status": "ok" if overall_ok else "degraded",
        "components": {
            "openai_key": "present" if key_ok else "missing",
            "database":  "up"      if db_ok  else "down"
        },
        "errors": {}
    }
    if not db_ok:
        payload["errors"]["database"] = db_err

    code = status.HTTP_200_OK if overall_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=code)

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

@app.post("/session", response_model=TutorReply)
def session_turn(req: TurnRequest):
    # 1) analyze
    em = emotion.classify(req.user_text)
    perf = emotion.estimate_perf(req.user_text)
    # 2) build MCP
    # compute reward BEFORE policy.update (baseline for this turn)
    r = reward.compute(em, perf)   # <-- returns a float
    mcp_state = mcp.build(em, perf, req.user_text)
    # 3) policy update
    mcp_updated = policy.update(mcp_state, r)
    # 4) tutor reply
    try:
        text = tutor.generate(req.user_text, mcp_updated)
        if not text or not str(text).strip():
            text = "[Tutor] Let’s try a simpler example together."
    except Exception as gen_err:
        print(f"[session] Tutor error: {gen_err}")
        text = "[Tutor] Quick hint: try a smaller step — we’ll fix generation next."
    # 5) persist safely EVERYTHING including reward
    try:
        storage.log_turn_full(req, em, perf, mcp_updated, text, reward=float(r))
    except Exception as log_err:
        print(f"[storage] Logging failed: {log_err}")
    return TutorReply(text=text, mcp=mcp_updated, reward=float(r))
