from typing import Optional, List, Dict
from fastapi import APIRouter, Query

from app.services import objectives as objsvc
from app.services import storage
from datetime import datetime

router = APIRouter(prefix="/api/v1/objectives", tags=["objectives"])

@router.get("")
def list_objectives(unit: Optional[str] = Query(None), q: Optional[str] = Query(None)):
    rows = objsvc.list_objectives(unit=unit, q=q)
    return {"count": len(rows), "items": rows}

@router.get("/{code}")
def get_objective(code: str):
    o = objsvc.find_by_code(code)
    if not o:
        return {"found": False}
    return {"found": True, "item": o}


@router.get("/progress")
def objective_progress(
    session_id: Optional[int] = Query(None, description="Session ID to summarize"),
    user_id: Optional[int] = Query(None, description="User ID to summarize across sessions"),
    since_minutes: Optional[int] = Query(None, ge=1, description="Optional recency window"),
):
    rows = []
    if user_id is not None and (session_id is None):
        # Aggregate across all sessions for this user
        sess_ids = storage.sessions_for_user(int(user_id))
        for sid in sess_ids:
            rows.extend(storage.fetch_turns(session_id=str(sid), since_minutes=since_minutes, limit=200, offset=0, order="desc"))
    elif session_id is not None:
        rows = storage.fetch_turns(session_id=str(session_id), since_minutes=since_minutes, limit=200, offset=0, order="desc")
    else:
        return {"items": [], "error": "Provide session_id or user_id"}
    # group by objective_code captured in performance JSON
    groups: Dict[str, Dict] = {}
    for t in rows:
        perf = t.performance or {}
        oc = (perf.get("objective_code") or perf.get("objective") or "").strip()
        if not oc:
            continue
        g = groups.setdefault(oc, {"objective_code": oc, "attempts": 0, "correct": 0, "sum_reward": 0.0, "last_ts": None})
        g["attempts"] += 1
        # correctness from perf, fallback to reward > 0
        try:
            if perf.get("correct") is True:
                g["correct"] += 1
            elif perf.get("correct") is None:
                if float(t.reward or 0.0) > 0.0:
                    g["correct"] += 1
        except Exception:
            pass
        try:
            g["sum_reward"] += float(t.reward or 0.0)
        except Exception:
            pass
        ts = t.created_at
        if ts is not None:
            if g["last_ts"] is None or ts > g["last_ts"]:
                g["last_ts"] = ts

    items: List[Dict] = []
    for oc, g in groups.items():
        obj = objsvc.find_by_code(oc) or {}
        attempts = g["attempts"]
        correct = g["correct"]
        acc = (correct / attempts) if attempts > 0 else 0.0
        avg_reward = (g["sum_reward"] / attempts) if attempts > 0 else 0.0
        mt = None
        try:
            mt = float(obj.get("mastery_threshold")) if obj.get("mastery_threshold") else None
        except Exception:
            mt = None
        mastered = (acc >= mt) if (mt is not None and attempts >= 3) else False
        items.append({
            "objective_code": oc,
            "description": obj.get("description"),
            "attempts": attempts,
            "correct": correct,
            "accuracy": round(acc, 3),
            "avg_reward": round(avg_reward, 3),
            "mastery_threshold": mt,
            "mastered": mastered,
            "last_turn_utc": (g["last_ts"].isoformat() + "Z") if g["last_ts"] else None,
        })

    # sort by recent then code
    items.sort(key=lambda x: (x["last_turn_utc"] or "", x["objective_code"]), reverse=True)
    out = {"items": items}
    if session_id is not None:
        out["session_id"] = session_id
    if user_id is not None:
        out["user_id"] = user_id
    return out
