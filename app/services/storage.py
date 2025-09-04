# app/services/storage.py
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker
from app.db.schema import Base, Session as DBSession, Turn
from app.models import MCP, EmotionSignals, PerformanceSignals, TurnRequest
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

# 1) Require DATABASE_URL (Postgres)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Set it to your Postgres URL, e.g. postgresql+psycopg2://eqi:eqipw@localhost:5432/eqilevel"
    )

# 2) Engine
engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)

# 3) Session factory
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    future=True,
)

# 4) Create tables in the same DB the app uses
def init_db() -> None:
    Base.metadata.create_all(bind=engine)

def _as_int(value, fieldname="value"):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{fieldname} must be int or a numeric string")

def db_health() -> Tuple[bool, str | None]:
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
    - session_id: optional filter (accepts int or numeric str)
    - limit: max 200
    - offset: pagination
    - since_minutes: filter by recency
    - order: 'desc' or 'asc'
    """
    limit = max(1, min(limit, 200))
    order_desc = order.lower() != "asc"

    with SessionLocal() as db:
        stmt = select(Turn)
        if session_id is not None:
            stmt = stmt.where(Turn.session_id == _as_int(session_id, "session_id"))

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

def log_turn_full(
    req: TurnRequest,
    em: EmotionSignals,
    perf: PerformanceSignals,
    mcp: MCP,
    reply_text: str,
    reward: float = 0.0
):
    """
    Persist a tutor turn:
    - ensures the Session row exists (by id)
    - inserts a Turn row with emotion/performance/mcp/reward payloads
    """
    with SessionLocal() as db:
        # 🔧 make sure session_id is an int for BIGINT FK
        sid = _as_int(req.session_id, "session_id")

        # ensure session exists (create if missing)
        sess = db.get(DBSession, sid)
        if not sess:
            # Disallow implicit creation
            raise ValueError(f"Session {sid} does not exist")

        # never allow NULL/empty to hit DB
        safe_reply = (reply_text or "").strip() or "[no_reply]"

        db.add(Turn(
            session_id=sid,                # BIGINT FK
            user_text=req.user_text,
            reply_text=safe_reply,
            emotion=em.model_dump(),
            performance=perf.model_dump(),
            mcp=mcp.model_dump(),
            reward=reward
        ))
        db.commit()
