# app/main.py
import os
from dotenv import load_dotenv

# Load .env before any imports that read env vars (like storage.py)
load_dotenv()

from app.api.v1.admin_router import router as admin_router
from app.api.v1.debug_router import router as debug_router
from app.api.v1.health_router import router as health_router
from app.api.v1.metrics_router import router as metrics_router
from app.api.v1.turn_logger_router import router as turn_logger_router
from app.db.schema import Turn
from app.models import TurnRequest, TurnContext, TutorReply, MCP
from app.services import emotion, mcp, policy, tutor, reward, storage
from app.services.metrics import compute_metrics
from app.services.storage import SessionLocal, db_health, init_db
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print(f"[startup] DATABASE_URL set?: {'yes' if os.getenv('DATABASE_URL') else 'no'}")
    print(f"[startup] OPENAI_API_KEY loaded?: {'yes' if os.getenv('OPENAI_API_KEY') else 'no'}")
    yield

app = FastAPI(title="EQiLevel API", lifespan=lifespan)

# (Optional) CORS — keep origins tight for your front end(s)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Include routers
app.include_router(admin_router)
app.include_router(debug_router)
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(turn_logger_router)

# ================================= GETs =============================
@app.get("/health")  # (optional) keep a super-light liveness root if you want backward compatibility
def health_root():
    return {"status": "ok"}

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
