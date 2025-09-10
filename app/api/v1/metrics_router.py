# app/api/v1/metrics_router.py
from typing import Optional, Union
from fastapi import APIRouter, Query
from app.services.metrics import compute_metrics, compute_series

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
                        "filters": {"session_id": "s3", "since_minutes": 60, "window_start_utc": "2025-09-02T20:51:30Z"}
                    }
                }
            },
        }
    },
)
def get_metrics(
    session_id: Optional[str] = Query(
        None,
        example="3",
        description="Filter metrics by session ID (numeric)"
    ),
    since_minutes: Optional[int] = Query(
        None,
        ge=1,
        example=60,
        description="Only include turns from the last N minutes"
    ),
    since_hours: Optional[int] = Query(
        None,
        ge=1,
        example=24,
        description="Only include turns from the last N hours (converted to minutes if since_minutes not provided)"
    ),
):
    # prefer since_minutes; otherwise convert hours â†’ minutes
    if since_minutes is None and since_hours is not None:
        since_minutes = since_hours * 60

    # Coerce session_id to int if numeric; otherwise ignore
    sid: Optional[int] = None
    if isinstance(session_id, str) and session_id.strip().isdigit():
        sid = int(session_id.strip())
    elif isinstance(session_id, int):
        sid = session_id

    return compute_metrics(session_id=sid, since_minutes=since_minutes)

@router.get(
    "/series",
    responses={
        200: {
            "description": "Time series for dashboard charts",
            "content": {"application/json": {"example": {
                "bucket": "minute",
                "since_minutes": 240,
                "window_start_utc": "2025-09-02T20:51:30Z",
                "session_id": "s3",
                "points": [
                    {"ts":"2025-09-02T20:10:00Z","turns":4,"avg_reward":0.23,"frustrated":1},
                    {"ts":"2025-09-02T20:11:00Z","turns":2,"avg_reward":0.17,"frustrated":0},
                ]
            }}}
        }
    }
)
def get_series(
    session_id: Optional[str] = Query(
        None, example="3", description="Filter series by session ID (numeric)"
    ),
    bucket: str = Query(
        "minute", pattern="^(minute|hour)$", description="Time bucket for aggregation"
    ),
    since_minutes: int = Query(
        240, ge=1, example=240, description="Window size in minutes (default 4 hours)"
    ),
):
    sid: Optional[int] = None
    if isinstance(session_id, str) and session_id.strip().isdigit():
        sid = int(session_id.strip())
    elif isinstance(session_id, int):
        sid = session_id
    return compute_series(session_id=sid, since_minutes=since_minutes, bucket=bucket)


