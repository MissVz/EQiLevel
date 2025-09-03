# app/services/storage.py
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker
from app.db.schema import Base, Session as DBSession, Turn
from app.models import MCP, EmotionSignals, PerformanceSignals, TurnRequest
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

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
    
def fetch_turns(
    session_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    since_minutes: Optional[int] = None,
    order: str = "desc",
) -> List[Turn]:
    """
    Fetch recent turns for admin inspection.
    - session_id: optional filter
    - limit: max 200
    - offset: pagination
    - since_minutes: filter by recency
    - order: 'desc' or 'asc'
    """
    limit = max(1, min(limit, 200))
    order_desc = order.lower() != "asc"

    with SessionLocal() as db:
        stmt = select(Turn)
        if session_id:
            stmt = stmt.where(Turn.session_id == session_id)

        if since_minutes and since_minutes > 0:
            cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
            stmt = stmt.where(Turn.created_at >= cutoff)

        stmt = stmt.order_by(Turn.id.desc() if order_desc else Turn.id.asc())
        stmt = stmt.offset(max(0, offset)).limit(limit)

        rows = db.execute(stmt).scalars().all()
        return rows

def log_reward(ctx, reward: float, new_mcp: MCP):
    # optional separate logging
    pass

def log_turn(ctx, reply_text: str, reward: float):
    # optional separate logging
    pass

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