# app/services/mcp.py
from app.models import EmotionSignals, PerformanceSignals, LearningStyle, MCP

def _choose_tone(emotion: EmotionSignals) -> str:
    if emotion.label == "frustrated": return "warm"
    if emotion.label == "engaged":    return "encouraging"
    return "neutral"

def _choose_pacing(emotion: EmotionSignals) -> str:
    if emotion.label == "frustrated": return "slow"
    if emotion.label == "engaged":    return "fast"
    return "medium"

def _choose_difficulty(emotion: EmotionSignals, perf: PerformanceSignals) -> str:
    if emotion.label == "frustrated": return "down"
    if perf.correct:                  return "up"
    return "hold"

def _choose_style(ls: LearningStyle) -> str:
    # pick the max learning style; if all zero -> mixed
    styles = {
        "visual": ls.visual,
        "auditory": ls.auditory,
        "reading_writing": ls.reading_writing,
        "kinesthetic": ls.kinesthetic,
    }
    best = max(styles, key=styles.get) if any(v>0 for v in styles.values()) else "mixed"
    return best

def _next_step(emotion: EmotionSignals, perf: PerformanceSignals) -> str:
    if emotion.label == "frustrated": return "example"
    if perf.correct:                  return "quiz"
    return "explain"

def build(emotion: EmotionSignals, perf: PerformanceSignals, transcript: str) -> MCP:
    # default learning style (can be set elsewhere)
    ls = LearningStyle()
    return MCP(
        emotion=emotion,
        performance=perf,
        learning_style=ls,
        tone=_choose_tone(emotion),
        pacing=_choose_pacing(emotion),
        difficulty=_choose_difficulty(emotion, perf),
        style=_choose_style(ls),
        next_step=_next_step(emotion, perf),
    )
