from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.schemas.admin import AdminTurn
from app.services.storage import fetch_turns
from app.services.security import require_admin
from app.db.schema import Turn

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

def _map_turn(t: Turn) -> AdminTurn:
    return AdminTurn(
        id=t.id,
        ts=t.created_at,
        session_id=t.session_id or "unknown",
        user_text=t.user_text or "",
        reply_text=t.reply_text or "",
        reward=t.reward,
        emotion=t.emotion or {},
        performance=t.performance or {},
        mcp=t.mcp or {},
    )

@router.get("/turns", response_model=List[AdminTurn])
def get_admin_turns(
    session_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    since_minutes: Optional[int] = Query(None, ge=1),
    order: str = Query("desc", pattern="^(?i)(asc|desc)$"),
    _=Depends(require_admin),
):
    rows = fetch_turns(session_id, limit, offset, since_minutes, order)
    return [_map_turn(r) for r in rows]
