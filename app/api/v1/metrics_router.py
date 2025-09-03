# app/api/v1/metrics_router.py
from typing import Optional
from fastapi import APIRouter, Query
from app.services.metrics import compute_metrics

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("")
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
