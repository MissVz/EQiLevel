# app/services/metrics.py
from __future__ import annotations
from app.db.schema import Turn
from app.services.storage import SessionLocal
from datetime import datetime, timedelta
from sqlalchemy import select, func, or_, case, String
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

def compute_metrics(session_id: Optional[int] = None,
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

    # Helper: apply session/time filters
    cutoff_dt = None
    if since_minutes and since_minutes > 0:
        cutoff_dt = datetime.utcnow() - timedelta(minutes=since_minutes)

    def _with_filters(stmt):
        if session_id:
            stmt = stmt.where(Turn.session_id == session_id)
        if cutoff_dt is not None:
            stmt = stmt.where(Turn.created_at >= cutoff_dt)
        return stmt

    # Helper: Postgres JSONB text extractor (portable across SA/pg versions)
    def J(col, key: str):
        # col ->> 'key'
        return col.op('->>')(key)

    with SessionLocal() as db:
        # ---- Totals ----
        turns_total = db.scalar(_with_filters(select(func.count(Turn.id)))) or 0

        # ---- Average reward ---- (of all filtered turns)
        avg_reward = db.scalar(_with_filters(select(func.avg(Turn.reward)))) or 0.0

        # ---- Frustration adaptation rate ----
        # denominator: # frustrated turns
        frustrated_total = db.scalar(
            _with_filters(
                select(func.count(Turn.id)).where(J(Turn.emotion, 'label') == 'frustrated')
            )
        ) or 0

        # numerator: among frustrated, how many adapted (pacing slow OR difficulty down)
        adapted_frustrated = db.scalar(
            _with_filters(
                select(func.count(Turn.id))
                .where(J(Turn.emotion, 'label') == 'frustrated')
                .where(
                    or_(
                        J(Turn.mcp, 'pacing') == 'slow',
                        J(Turn.mcp, 'difficulty') == 'down'
                    )
                )
            )
        ) or 0

        frustration_adaptation_rate = (adapted_frustrated / frustrated_total) if frustrated_total else 0.0

        # ---- Tone alignment (heuristic proxy) ----
        # frustrated -> warm/encouraging
        frustrated_aligned = db.scalar(
            _with_filters(
                select(func.count(Turn.id))
                .where(J(Turn.emotion, 'label') == 'frustrated')
                .where(J(Turn.mcp, 'tone').in_(['warm', 'encouraging']))
            )
        ) or 0

        # engaged -> encouraging
        engaged_aligned = db.scalar(
            _with_filters(
                select(func.count(Turn.id))
                .where(J(Turn.emotion, 'label') == 'engaged')
                .where(J(Turn.mcp, 'tone') == 'encouraging')
            )
        ) or 0

        # calm -> neutral
        calm_aligned = db.scalar(
            _with_filters(
                select(func.count(Turn.id))
                .where(J(Turn.emotion, 'label') == 'calm')
                .where(J(Turn.mcp, 'tone') == 'neutral')
            )
        ) or 0

        # bored -> concise
        bored_aligned = db.scalar(
            _with_filters(
                select(func.count(Turn.id))
                .where(J(Turn.emotion, 'label') == 'bored')
                .where(J(Turn.mcp, 'tone') == 'concise')
            )
        ) or 0

        tone_aligned = frustrated_aligned + engaged_aligned + calm_aligned + bored_aligned

        tone_labeled_total = db.scalar(
            _with_filters(
                select(func.count(Turn.id)).where(
                    J(Turn.emotion, 'label').in_(['frustrated', 'engaged', 'calm', 'bored'])
                )
            )
        ) or 0

        tone_alignment_rate = (tone_aligned / tone_labeled_total) if tone_labeled_total else 0.0

        # ---- Last 10 reward Moving Average (subquery pattern for PG) ----
        subq = _with_filters(
            select(Turn.reward).order_by(Turn.id.desc()).limit(10)
        ).subquery()
        last_10_reward_avg = db.scalar(select(func.avg(subq.c.reward))) or 0.0

        # ---- Emotion counts ----
        def count_emotion(lbl: str) -> int:
            return db.scalar(
                _with_filters(select(func.count(Turn.id)).where(J(Turn.emotion, 'label') == lbl))
            ) or 0

        by_emotion = {
            "frustrated": count_emotion("frustrated"),
            "engaged":    count_emotion("engaged"),
            "calm":       count_emotion("calm"),
            "bored":      count_emotion("bored"),
        }

        # ---- Action distribution ----
        def count_mcp(field: str, value: str) -> int:
            return db.scalar(
                _with_filters(select(func.count(Turn.id)).where(J(Turn.mcp, field) == value))
            ) or 0

        action_distribution = {
            "tone":       {t: count_mcp("tone", t) for t in ["warm","encouraging","neutral","concise"]},
            "pacing":     {p: count_mcp("pacing", p) for p in ["slow","medium","fast"]},
            "difficulty": {d: count_mcp("difficulty", d) for d in ["down","hold","up"]},
            "next_step":  {n: count_mcp("next_step", n) for n in ["example","prompt","explain","quiz","review"]},
        }

        filters = {}
        if session_id is not None:
            filters["session_id"] = session_id
        if since_minutes:
            filters["since_minutes"] = since_minutes
            filters["window_start_utc"] = (datetime.utcnow() - timedelta(minutes=since_minutes)).isoformat() + "Z"

        return {
            "turns_total": turns_total,
            "avg_reward": float(round(avg_reward, 4)),
            "frustration_adaptation_rate": float(round(frustration_adaptation_rate, 4)),
            "tone_alignment_rate": float(round(tone_alignment_rate, 4)),
            "last_10_reward_avg": float(round(last_10_reward_avg, 4)),
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
