# app/services/metrics.py
from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy import select, func, or_
from app.db.schema import Turn
from app.services.storage import SessionLocal


def _counts_by_emotion(db, session_id):
    from sqlalchemy import case
    def Q(label):  # count where emotion.label == label
        stmt = select(func.count(Turn.id)).where(Turn.emotion["label"].as_string() == label)
        return (stmt.where(Turn.session_id == session_id) if session_id else stmt)
    return {
        "frustrated": db.scalar(Q("frustrated")) or 0,
        "engaged":    db.scalar(Q("engaged")) or 0,
        "calm":       db.scalar(Q("calm")) or 0,
        "bored":      db.scalar(Q("bored")) or 0,
    }

def _action_distribution(db, session_id):
    def S(key, value):
        stmt = select(func.count(Turn.id)).where(Turn.mcp[key].as_string() == value)
        return (stmt.where(Turn.session_id == session_id) if session_id else stmt)
    return {
        "tone":       {t: db.scalar(S("tone", t)) or 0 for t in ["warm","encouraging","neutral","concise"]},
        "pacing":     {p: db.scalar(S("pacing", p)) or 0 for p in ["slow","medium","fast"]},
        "difficulty": {d: db.scalar(S("difficulty", d)) or 0 for d in ["down","hold","up"]},
        "next_step":  {n: db.scalar(S("next_step", n)) or 0 for n in ["example","prompt","explain","quiz","review"]},
    }

def compute_metrics(session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Compute aggregate telemetry for EQiLevel.

    Returns:
      - turns_total
      - avg_reward
      - frustration_adaptation_rate: frustrated turns where pacing='slow' OR difficulty='down'
      - tone_alignment_rate: heuristic tone↔emotion mapping (see below)
      - last_10_reward_avg
    """
    def _with_session_filter(stmt):
        if session_id:
            return stmt.where(Turn.session_id == session_id)
        return stmt

    with SessionLocal() as db:
        # ---- Totals ----
        turns_total = db.scalar(_with_session_filter(select(func.count(Turn.id)))) or 0

        # ---- Average reward ----
        avg_reward = db.scalar(_with_session_filter(select(func.avg(Turn.reward)))) or 0.0

        # ---- Frustration adaptation rate ----
        frustrated_total = db.scalar(
            _with_session_filter(
                select(func.count(Turn.id)).where(
                    Turn.emotion["label"].as_string() == "frustrated"
                )
            )
        ) or 0

        adapted_when_frustrated = db.scalar(
            _with_session_filter(
                select(func.count(Turn.id))
                .where(Turn.emotion["label"].as_string() == "frustrated")
                .where(
                    or_(
                        Turn.mcp["pacing"].as_string() == "slow",
                        Turn.mcp["difficulty"].as_string() == "down",
                    )
                )
            )
        ) or 0

        frustration_adaptation_rate = (
            adapted_when_frustrated / frustrated_total if frustrated_total else 0.0
        )

        # ---- Tone alignment (heuristic proxy) ----
        # Targets:
        #  frustrated -> tone in {"warm","encouraging"}
        #  engaged   -> tone == "encouraging"
        #  calm      -> tone == "neutral"
        #  bored     -> tone == "concise"
        tone_aligned = 0

        tone_aligned += db.scalar(
            _with_session_filter(
                select(func.count(Turn.id))
                .where(Turn.emotion["label"].as_string() == "frustrated")
                .where(Turn.mcp["tone"].as_string().in_(["warm", "encouraging"]))
            )
        ) or 0

        tone_aligned += db.scalar(
            _with_session_filter(
                select(func.count(Turn.id))
                .where(Turn.emotion["label"].as_string() == "engaged")
                .where(Turn.mcp["tone"].as_string() == "encouraging")
            )
        ) or 0

        tone_aligned += db.scalar(
            _with_session_filter(
                select(func.count(Turn.id))
                .where(Turn.emotion["label"].as_string() == "calm")
                .where(Turn.mcp["tone"].as_string() == "neutral")
            )
        ) or 0

        tone_aligned += db.scalar(
            _with_session_filter(
                select(func.count(Turn.id))
                .where(Turn.emotion["label"].as_string() == "bored")
                .where(Turn.mcp["tone"].as_string() == "concise")
            )
        ) or 0

        tone_labeled_total = db.scalar(
            _with_session_filter(
                select(func.count(Turn.id)).where(
                    Turn.emotion["label"].as_string().in_(
                        ["frustrated", "engaged", "calm", "bored"]
                    )
                )
            )
        ) or 0

        tone_alignment_rate = tone_aligned / tone_labeled_total if tone_labeled_total else 0.0

        # ---- Last 10 reward moving average ----
        last_10_reward_avg = db.scalar(
            _with_session_filter(
                select(func.avg(Turn.reward)).order_by(Turn.id.desc()).limit(10)
            )
        ) or 0.0

        return {
            "turns_total": turns_total,
            "avg_reward": round(float(avg_reward), 4),
            "frustration_adaptation_rate": round(float(frustration_adaptation_rate), 4),
            "tone_alignment_rate": round(float(tone_alignment_rate), 4),
            "last_10_reward_avg": round(float(last_10_reward_avg), 4),
            "filters": {"session_id": session_id} if session_id else {},
            "by_emotion": _counts_by_emotion(db, session_id),
            "action_distribution": _action_distribution(db, session_id),
        }