# app/services/emotion.py
from app.models import EmotionSignals, PerformanceSignals

NEG_WORDS = {"stuck","confused","lost","hard","difficult","messing up","frustrated"}
POS_WORDS = {"great","got it","clear","easy","makes sense","understand"}

def classify(text: str) -> EmotionSignals:
    t = text.lower()
    if any(w in t for w in NEG_WORDS):
        return EmotionSignals(label="frustrated", sentiment=-0.4)
    if any(w in t for w in POS_WORDS):
        return EmotionSignals(label="engaged", sentiment=0.5)
    # neutral fallback
    return EmotionSignals(label="calm", sentiment=0.0)

def estimate_perf(text: str) -> PerformanceSignals:
    # very rough heuristic: “I got it / I solved it” -> correct
    tl = text.lower()
    perf = PerformanceSignals()
    if "got it" in tl or "i solved" in tl or "worked" in tl:
        perf.correct = True
        perf.accuracy_pct = 1.0
        perf.attempts = 1
    return perf
