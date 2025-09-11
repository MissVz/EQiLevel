# app/api/v1/debug_router.py (if you don’t already have it)
from fastapi import APIRouter
from sqlalchemy import text
from app.services.storage import SessionLocal

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])

@router.get("/db")
def debug_db():
    with SessionLocal() as db:
        info = {"db_url": db.bind.url.render_as_string(hide_password=True)}
        # Use actual table names
        n_sessions = db.execute(text("SELECT COUNT(*) FROM sessions")).scalar()
        n_turns    = db.execute(text("SELECT COUNT(*) FROM turns")).scalar()
        return {"info": info, "counts": {"sessions": n_sessions, "turns": n_turns}}
