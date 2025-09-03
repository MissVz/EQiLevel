# app/services/storage.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db.schema import Base, Session as DBSession, Turn
from app.models import MCP, EmotionSignals, PerformanceSignals, TurnRequest

_engine = create_engine("sqlite:///./eqilevel.db", future=True)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)

def init_db():
    Base.metadata.create_all(bind=_engine)

def db_health() -> tuple[bool, str | None]:
    """
    Check DB availability with a trivial query.
    Returns (ok, error_message).
    ok=True if a trivial query succeeds; otherwise False and the error string.
    """
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True, None
    except Exception as e:
        return False, str(e)
    
def log_turn_full(req: TurnRequest, em: EmotionSignals, perf: PerformanceSignals, mcp: MCP, reply_text: str, reward: float = 0.0):
    with SessionLocal() as db:
        # ensure session
        sid = req.session_id or "default"
        sess = db.get(DBSession, sid)
        if not sess:
            sess = DBSession(id=sid)
            db.add(sess)
            db.flush()

        # never allow NULL to hit DB
        safe_reply = (reply_text or "").strip() or "[no_reply]"

        db.add(Turn(
            session_id=sid,
            user_text=req.user_text,
            reply_text=safe_reply,
            emotion=em.model_dump(),
            performance=perf.model_dump(),
            mcp=mcp.model_dump(),
            reward=reward
        ))
        db.commit()

def log_reward(ctx, reward: float, new_mcp: MCP):
    # optional separate logging
    pass

def log_turn(ctx, reply_text: str, reward: float):
    # optional separate logging
    pass
