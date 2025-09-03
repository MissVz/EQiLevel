from typing import List, Optional
from fastapi import APIRouter, Depends, Query

from app.schemas.admin import AdminTurn
from app.services.admin_summary import admin_summary
from app.services.storage import fetch_turns
from app.services.security import require_admin
from app.db.schema import Turn
from fastapi import Query
from typing import Optional

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
def get_turns(
    session_id: Optional[str] = Query(None),
    since_minutes: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order: str = Query("desc", pattern="^(?i)(asc|desc)$"),
    _=Depends(require_admin),
):
    rows = fetch_turns(
        session_id=session_id,
        limit=limit,
        offset=offset,
        since_minutes=since_minutes,
        order=order,
    )
    return [_map_turn(r) for r in rows]

@router.get(
    "/summary",
    responses={
        200: {
            "description": "Admin summary: per-session totals and last turn snapshot.",
            "content": {
                "application/json": {
                    "example": {
                        "sessions": [
                            {
                                "session_id": "s3",
                                "turns_total": 2,
                                "last_turn_utc": "2025-09-03T19:23:29Z",
                                "last_emotion": "frustrated",
                                "last_reward": 0.45,
                                "last_difficulty": "down",
                                "last_tone": "warm",
                                "turns_in_window": 2,
                                "avg_reward_window": 0.35
                            },
                            {
                                "session_id": "s1",
                                "turns_total": 10,
                                "last_turn_utc": "2025-09-03T05:41:00Z",
                                "last_emotion": "calm",
                                "last_reward": 0.05,
                                "last_difficulty": "hold",
                                "last_tone": "neutral",
                                "turns_in_window": 0,
                                "avg_reward_window": 0.0
                            }
                        ],
                        "filters": {
                            "since_hours": 24,
                            "window_start_utc": "2025-09-02T20:51:30Z"
                        }
                    }
                }
            },
        }
    },
)
def get_summary(
    since_minutes: Optional[int] = Query(None, ge=1, description="Window size in minutes"),
    since_hours: Optional[int] = Query(None, ge=1, description="Window size in hours"),
    _=Depends(require_admin),
):
    if since_minutes is None and since_hours:
        since_minutes = since_hours * 60
    return admin_summary(since_minutes=since_minutes)