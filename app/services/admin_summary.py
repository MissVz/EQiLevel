# app/services/admin_summary.py
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func, and_, tuple_
from app.db.schema import Turn
from app.services.storage import SessionLocal

def admin_summary(since_minutes: Optional[int] = None) -> Dict[str, Any]:
    """
    Returns a compact dashboard by session:
      - session_id
      - turns_total (all time)
      - last_turn_utc, last_emotion, last_reward, last_difficulty, last_tone
      - turns_in_window (if since_minutes provided)
      - avg_reward_window (if since_minutes provided)
    """
    cutoff_dt = None
    if since_minutes and since_minutes > 0:
        cutoff_dt = datetime.utcnow() - timedelta(minutes=since_minutes)

    with SessionLocal() as db:
        # 1) Total turns per session
        totals = dict(
            db.execute(
                select(Turn.session_id, func.count(Turn.id))
                .group_by(Turn.session_id)
            ).all()
        )

        if not totals:
            return {
                "sessions": [],
                "filters": {"since_minutes": since_minutes, "window_start_utc": cutoff_dt.isoformat() + "Z" if cutoff_dt else None},
            }

        # 2) Latest id per session (to inspect last turn fields fast)
        last_ids = dict(
            db.execute(
                select(Turn.session_id, func.max(Turn.id))
                .group_by(Turn.session_id)
            ).all()
        )
        last_rows = {}
        if last_ids:
            rows = db.execute(
                select(Turn).where(
                    tuple_(Turn.session_id, Turn.id).in_(
                        [(sid, lid) for sid, lid in last_ids.items()]
                    )
                )
            ).scalars().all()
            for r in rows:
                last_rows[r.session_id] = r

        # 3) Window stats (optional)
        window_counts = {}
        window_avgs = {}
        if cutoff_dt:
            window_counts = dict(
                db.execute(
                    select(Turn.session_id, func.count(Turn.id))
                    .where(Turn.created_at >= cutoff_dt)
                    .group_by(Turn.session_id)
                ).all()
            )
            window_avgs = dict(
                db.execute(
                    select(Turn.session_id, func.avg(Turn.reward))
                    .where(Turn.created_at >= cutoff_dt)
                    .group_by(Turn.session_id)
                ).all()
            )

        # 4) Build summary list
        summary: List[Dict[str, Any]] = []
        for sid, total in totals.items():
            last = last_rows.get(sid)
            summary.append({
                "session_id": sid,
                "turns_total": int(total),
                "last_turn_utc": (last.created_at.isoformat() + "Z") if last and last.created_at else None,
                "last_emotion": (last.emotion or {}).get("label") if last and last.emotion else None,
                "last_reward": float(last.reward) if (last and last.reward is not None) else None,
                "last_difficulty": (last.mcp or {}).get("difficulty") if last and last.mcp else None,
                "last_tone": (last.mcp or {}).get("tone") if last and last.mcp else None,
                "turns_in_window": int(window_counts.get(sid, 0)) if cutoff_dt else None,
                "avg_reward_window": (round(float(window_avgs.get(sid, 0.0)), 4) if cutoff_dt else None),
            })

        # Sort by latest turn desc
        summary.sort(key=lambda x: (x["last_turn_utc"] or ""), reverse=True)

        return {
            "sessions": summary,
            "filters": {
                "since_minutes": since_minutes,
                "window_start_utc": cutoff_dt.isoformat() + "Z" if cutoff_dt else None
            },
        }
