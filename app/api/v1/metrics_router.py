# app/api/v1/metrics_router.py
from typing import Optional
from fastapi import APIRouter, Query
from app.services.metrics import compute_metrics

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get(
    "",
    responses={
        200: {
            "description": "Metrics snapshot",
            "content": {
                "application/json": {
                    "example": {
                        "turns_total": 12,
                        "avg_reward": 0.21,
                        "frustration_adaptation_rate": 0.78,
                        "tone_alignment_rate": 0.81,
                        "last_10_reward_avg": 0.25,
                        "by_emotion": {"frustrated": 5, "engaged": 4, "calm": 3, "bored": 0},
                        "action_distribution": {
                            "tone": {"warm": 5, "encouraging": 4, "neutral": 3, "concise": 0},
                            "pacing": {"slow": 5, "medium": 3, "fast": 4},
                            "difficulty": {"down": 5, "hold": 5, "up": 2},
                            "next_step": {"example": 5, "explain": 3, "quiz": 4, "prompt": 0, "review": 0}
                        },
                        "filters": {"session_id": "s3", "since_hours": 24, "window_start_utc": "2025-09-02T20:51:30Z"}
                    }
                }
            },
        }
    },
)
def get_metrics(
    session_id: Optional[str] = Query(None),
    since_minutes: Optional[int] = Query(None, ge=1, description="Only include turns within last N minutes"),
    since_hours:   Optional[int] = Query(None,  ge=1, description="Only include turns in last N hours"),
):
    # prefer since_minutes; otherwise convert hours → minutes
    if since_minutes is None and since_hours is not None:
        since_minutes = since_hours * 60

    # Pass through to metrics service
    return compute_metrics(session_id=session_id, since_minutes=since_minutes)
