from typing import Optional
from fastapi import APIRouter, Query, Body

from app.services import storage

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("")
def list_users(q: Optional[str] = Query(None), limit: int = Query(20, ge=1, le=50)):
    rows = storage.list_users(q, limit)
    return {"items": [{"id": int(u.id), "name": u.name} for u in rows]}

@router.post("")
def create_user(name: str = Body(..., embed=True)):
    uid = storage.get_or_create_user(name)
    return {"id": uid, "name": name}

@router.get("/by_session")
def user_by_session(session_id: int = Query(...)):
    u = storage.get_user_for_session(int(session_id))
    if not u:
        return {"found": False}
    return {"found": True, "user": {"id": int(u.id), "name": u.name}}
