# app/routers/session_start.py  (or inside your existing session router)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as ORMSession

from app.services.storage import get_db
from app.db.schema import Session as SessionModel

router = APIRouter(tags=["session"])

@router.post("/session/start")
def start_session(db: ORMSession = Depends(get_db)):
    try:
        s = SessionModel()
        db.add(s)
        db.commit()
        db.refresh(s)
        return {"session_id": s.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"failed to start session: {e}")
