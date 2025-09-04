# app/services/metrics.py
from __future__ import annotations
from app.db.schema import Turn
from app.services.storage import SessionLocal
from datetime import datetime, timedelta
from sqlalchemy import select, func, or_, case
from typing import Optional, Dict, Any, List

def _counts_by_emotion(db, session_id, cutoff_dt):
    def _with_filters(stmt):
        if session_id:
            stmt = stmt.where(Turn.session_id == session_id)
        if cutoff_dt is not None:
            stmt = stmt.where(Turn.created_at >= cutoff_dt)
        return stmt

    def Q(label):  # count where emotion.label == label
        stmt = select(func.count(Turn.id)).where(Turn.emotion["label"].as_string() == label)
        return db.scalar(_with_filters(stmt)) or 0

    return {
        "frustrated": Q("frustrated"),
        "engaged":    Q("engaged"),
        "calm":       Q("calm"),
        "bored":      Q("bored"),
    }

def _action_distribution(db, session_id, cutoff_dt):
    def _with_filters(stmt):
        if session_id:
            stmt = stmt.where(Turn.session_id == session_id)
        if cutoff_dt is not None:
            stmt = stmt.where(Turn.created_at >= cutoff_dt)
        return stmt

    def S(key, value):
        stmt = select(func.count(Turn.id)).where(Turn.mcp[key].as_string() == value)
        return db.scalar(_with_filters(stmt)) or 0

    return {
        "tone":       {t: S("tone", t) for t in ["warm","encouraging","neutral","concise"]},
        "pacing":     {p: S("pacing", p) for p in ["slow","medium","fast"]},
        "difficulty": {d: S("difficulty", d) for d in ["down","hold","up"]},
        "next_step":  {n: S("next_step", n) for n in ["example","prompt","explain","quiz","review"]},
    }

def _series_basic(db, session_id: Optional[str], cutoff_dt: Optional[datetime], bucket: str = "minute") -> List[Dict[str, Any]]:
    """
    Time-bucketed series of core metrics:
      - turns
      - avg_reward
      - frustrated
    Buckets: 'minute' or 'hour'
    """
    assert bucket in ("minute", "hour")
    bucket_fn = func.date_trunc(bucket, Turn.created_at).label("ts")

    def _with_filters(stmt):
        if session_id:
            stmt = stmt.where(Turn.session_id == session_id)
        if cutoff_dt is not None:
            stmt = stmt.where(Turn.created_at >= cutoff_dt)
        return stmt

    # base aggregates
    base_stmt = (
        select(
            bucket_fn,
            func.count(Turn.id).label("turns"),
            func.avg(Turn.reward).label("avg_reward"),
            func.sum(
                case(
                    (
                        Turn.emotion["label"].as_string() == "frustrated",
                        1
                    ),
                    else_=0
                )
            ).label("frustrated")
        )
        .group_by(bucket_fn)
        .order_by(bucket_fn.asc())
    )

    rows = db.execute(_with_filters(base_stmt)).all()
    series = []
    for ts, turns, avg_reward, frustrated in rows:
        series.append({
            "ts": ts.isoformat() + "Z",
            "turns": int(turns or 0),
            "avg_reward": float(avg_reward or 0.0),
            "frustrated": int(frustrated or 0),
        })
    return series

def compute_metrics(session_id: Optional[str] = None,
                    since_minutes: Optional[int] = None) -> Dict[str, Any]:
    """
    Compute aggregate telemetry for EQiLevel.

    Returns (snapshot):
      - turns_total
      - avg_reward
      - frustration_adaptation_rate
      - tone_alignment_rate
      - last_10_reward_avg
      - by_emotion
      - action_distribution
      - filters {session_id?, since_minutes?, window_start_utc?}
    """
    cutoff_dt = None
    if since_minutes and since_minutes > 0:
        cutoff_dt = datetime.utcnow() - timedelta(minutes=since_minutes)

    def _with_filters(stmt):
        if session_id:
            stmt = stmt.where(Turn.session_id == session_id)
        if cutoff_dt is not None:
            stmt = stmt.where(Turn.created_at >= cutoff_dt)
        return stmt

    with SessionLocal() as db:
        # ---- Totals ----
        turns_total = db.scalar(_with_filters(select(func.count(Turn.id)))) or 0

        # ---- Average reward ----
        avg_reward = db.scalar(_with_filters(select(func.avg(Turn.reward)))) or 0.0

        # ---- Frustration adaptation rate ----
        frustrated_total = db.scalar(_with_filters(
            select(func.count(Turn.id)).where(Turn.emotion["label"].as_string()=="frustrated")
        )) or 0
        adapted_frustrated = db.scalar(_with_filters(
            select(func.count(Turn.id))
            .where(Turn.emotion["label"].as_string()=="frustrated")
            .where(or_(Turn.mcp["pacing"].as_string()=="slow",
                       Turn.mcp["difficulty"].as_string()=="down"))
        )) or 0
        frustration_adaptation_rate = (adapted_frustrated / frustrated_total) if frustrated_total else 0.0

        # ---- Tone alignment (heuristic proxy) ----
        tone_aligned = 0
        tone_aligned += db.scalar(_with_filters(
            select(func.count(Turn.id))
            .where(Turn.emotion["label"].as_string()=="frustrated")
            .where(Turn.mcp["tone"].as_string().in_(["warm","encouraging"]))
        )) or 0
        tone_aligned += db.scalar(_with_filters(
            select(func.count(Turn.id))
            .where(Turn.emotion["label"].as_string()=="engaged")
            .where(Turn.mcp["tone"].as_string()=="encouraging")
        )) or 0
        tone_aligned += db.scalar(_with_filters(
            select(func.count(Turn.id))
            .where(Turn.emotion["label"].as_string()=="calm")
            .where(Turn.mcp["tone"].as_string()=="neutral")
        )) or 0
        tone_aligned += db.scalar(_with_filters(
            select(func.count(Turn.id))
            .where(Turn.emotion["label"].as_string()=="bored")
            .where(Turn.mcp["tone"].as_string()=="concise")
        )) or 0
        tone_labeled_total = db.scalar(_with_filters(
            select(func.count(Turn.id)).where(
                Turn.emotion["label"].as_string().in_(["frustrated","engaged","calm","bored"])
            )
        )) or 0
        tone_alignment_rate = (tone_aligned / tone_labeled_total) if tone_labeled_total else 0.0

        # ---- Last 10 reward Moving Average (MA) ----
        last_10_reward_avg = db.scalar(_with_filters(
            select(func.avg(Turn.reward)).order_by(Turn.id.desc()).limit(10)
        )) or 0.0

        # ---- Breakdowns ----
        by_emotion = _counts_by_emotion(db, session_id, cutoff_dt)
        action_distribution = _action_distribution(db, session_id, cutoff_dt)

        filters = {}
        if session_id: filters["session_id"] = session_id
        if since_minutes:
            filters["since_minutes"] = since_minutes
            filters["window_start_utc"] = (datetime.utcnow() - timedelta(minutes=since_minutes)).isoformat() + "Z"

        return {
            "turns_total": turns_total,
            "avg_reward": round(float(avg_reward), 4),
            "frustration_adaptation_rate": round(float(frustration_adaptation_rate), 4),
            "tone_alignment_rate": round(float(tone_alignment_rate), 4),
            "last_10_reward_avg": round(float(last_10_reward_avg), 4),
            "by_emotion": by_emotion,
            "action_distribution": action_distribution,
            "filters": filters,
        }

def compute_series(session_id: Optional[str] = None,
                   since_minutes: Optional[int] = 240,
                   bucket: str = "minute") -> Dict[str, Any]:
    """
    Public service: time-bucketed series for dashboards.
    """
    cutoff_dt = None
    if since_minutes and since_minutes > 0:
        cutoff_dt = datetime.utcnow() - timedelta(minutes=since_minutes)

    with SessionLocal() as db:
        series = _series_basic(db, session_id=session_id, cutoff_dt=cutoff_dt, bucket=bucket)

    return {
        "bucket": bucket,
        "since_minutes": since_minutes,
        "window_start_utc": (datetime.utcnow() - timedelta(minutes=since_minutes)).isoformat() + "Z" if since_minutes else None,
        "session_id": session_id,
        "points": series,
    }
