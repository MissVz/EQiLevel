# app/services/storage.py
import os
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from sqlalchemy import create_engine, text, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session as ORMSession

from app.db.schema import  Session as SessionModel, Turn, Base, User, SessionUser, Setting

from app.models import MCP, EmotionSignals, PerformanceSignals, TurnRequest

# ---- engine & session factory ------------------------------------------------

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

# ---- FastAPI dependency ------------------------------------------------------
def get_db():
    """
    FastAPI dependency: yields a database session and ensures close.
    from fastapi import Depends
    def route(db: ORMSession = Depends(get_db)):
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---- init & health -----------------------------------------------------------
def init_db() -> None:
    Base.metadata.create_all(bind=engine)

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
    
# ---- helpers -----------------------------------------------------------------
def _as_int(value, fieldname="value"):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{fieldname} must be int or a numeric string")

def resolve_session_id(db: ORMSession, session_id: Optional[str]) -> int:
    """
    Accept int / numeric string / non-numeric client key.
    Create or reuse a SessionModel row and always return a numeric sessions.id.
    """
    if session_id is None:
        s = SessionModel()
        db.add(s); db.commit(); db.refresh(s)
        return s.id

    if isinstance(session_id, int):
        return session_id

    if isinstance(session_id, str) and session_id.isdigit():
        return int(session_id)

    # For any other (non-numeric) string key, create a new Session row
    if isinstance(session_id, str):
        s = SessionModel()
        db.add(s); db.commit(); db.refresh(s)
        return s.id
    

# ---- admin queries -----------------------------------------------------------
    
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

# ---- users -------------------------------------------------------------------
def get_or_create_user(name: str) -> int:
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    with SessionLocal() as db:
        u = db.execute(select(User).where(func.lower(User.name) == name.lower())).scalar_one_or_none()
        if u:
            return int(u.id)
        u = User(name=name)
        db.add(u)
        db.commit(); db.refresh(u)
        return int(u.id)

def list_users(query: str | None = None, limit: int = 20) -> list[User]:
    limit = max(1, min(limit, 50))
    with SessionLocal() as db:
        stmt = select(User)
        if query:
            q = f"%{query.strip().lower()}%"
            stmt = stmt.where(func.lower(User.name).like(q))
        stmt = stmt.order_by(User.name.asc()).limit(limit)
        return db.execute(stmt).scalars().all()

def bind_user_to_session(session_id: int, user_id: int) -> None:
    with SessionLocal() as db:
        exists = db.execute(select(SessionUser).where(SessionUser.session_id == session_id)).scalar_one_or_none()
        if exists:
            return
        db.add(SessionUser(session_id=session_id, user_id=user_id))
        db.commit()

def sessions_for_user(user_id: int) -> list[int]:
    with SessionLocal() as db:
        rows = db.execute(select(SessionUser.session_id).where(SessionUser.user_id == user_id)).scalars().all()
        return [int(x) for x in rows]

def get_user_for_session(session_id: int) -> User | None:
    with SessionLocal() as db:
        su = db.execute(select(SessionUser).where(SessionUser.session_id == session_id)).scalar_one_or_none()
        if not su:
            return None
        u = db.get(User, su.user_id)
        return u

# ---- app settings (key/value) -----------------------------------------------
def get_setting(key: str) -> str | None:
    with SessionLocal() as db:
        row = db.get(Setting, key)
        return row.value if row else None

def set_setting(key: str, value: str | None) -> None:
    with SessionLocal() as db:
        row = db.get(Setting, key)
        if value is None or value == "":
            if row:
                db.delete(row); db.commit()
            return
        if row:
            row.value = value
        else:
            db.add(Setting(key=key, value=value))
        db.commit()

def get_system_prompt() -> str | None:
    return get_setting("system_prompt")

def dialogue_messages(session_id: int, limit: int = 8) -> list[dict]:
    """
    Return recent dialogue for a session as OpenAI-style messages, oldest→newest.
    Each DB row becomes two messages: {role:'user', content:user_text},
    then {role:'assistant', content:reply_text}.
    """
    limit = max(1, min(limit, 20))
    with SessionLocal() as db:
        rows = (
            db.execute(
                select(Turn)
                .where(Turn.session_id == _as_int(session_id, "session_id"))
                .order_by(Turn.id.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    rows = list(reversed(rows))
    messages: list[dict] = []
    for r in rows:
        ut = (r.user_text or "").strip()
        rt = (r.reply_text or "").strip()
        if ut:
            messages.append({"role": "user", "content": ut})
        if rt:
            messages.append({"role": "assistant", "content": rt})
    return messages

# ---- logging -----------------------------------------------------------------
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
    reward: float = 0.0,
    objective_code: str | None = None,
):
    """
    Persist a tutor turn:
    - ensures the Session row exists (by id or client_key)
    - inserts a Turn row with emotion/performance/mcp/reward payloads
    """
    with SessionLocal() as db:
        # Resolve to numeric FK (create Session row if needed)
        sid = resolve_session_id(db, req.session_id)
        if not isinstance(sid, int):
            raise ValueError(f"invalid session id: {sid!r}")

        # ensure session exists (in case you disabled creation above)
        sess = db.get(SessionModel, sid)
        if not sess:
            raise ValueError(f"Session {sid} does not exist")

        # never allow NULL/empty to hit DB
        safe_reply = (reply_text or "").strip() or "[no_reply]"

        perf_payload = perf.model_dump()
        if objective_code:
            try:
                perf_payload = {**perf_payload, "objective_code": str(objective_code)}
            except Exception:
                pass

        db.add(Turn(
            session_id=sid,
            user_text=req.user_text,
            reply_text=safe_reply,
            emotion=em.model_dump(),
            performance=perf_payload,
            mcp=mcp.model_dump(),
            reward=reward
        ))
        db.commit()
