# app/routers/session_start.py  (or inside your existing session router)
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session as ORMSession

from app.services.storage import get_db, get_or_create_user, bind_user_to_session
from app.db.schema import Session as SessionModel

router = APIRouter(tags=["session"])

@router.post("/session/start")
def start_session(
    db: ORMSession = Depends(get_db),
    user_name: str | None = Body(None, embed=True),
    user_id: int | None = Body(None, embed=True),
):
    try:
        s = SessionModel()
        db.add(s)
        db.commit()
        db.refresh(s)
        # Optional: bind to a user
        try:
            uid = None
            if user_id:
                uid = int(user_id)
            elif user_name and user_name.strip():
                uid = get_or_create_user(user_name.strip())
            if uid:
                bind_user_to_session(s.id, uid)
        except Exception:
            pass
        return {"session_id": s.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"failed to start session: {e}")
