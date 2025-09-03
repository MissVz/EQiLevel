# app/services/emotion.py
import re, unicodedata
from app.models import EmotionSignals, PerformanceSignals

# Allow multiple variants, case insensitive
_CORRECT_RE = re.compile(r"\b(got\s*it|i\s*solved|solved\s*it|worked)\b", re.I)

NEG_WORDS = {"stuck","confused","lost","hard","difficult","messing up","frustrated"}
POS_WORDS = {"great","got it","clear","easy","makes sense","understand"}

def _normalize(text: str) -> str:
    # Fold Unicode characters (like em dashes, curly quotes) into simpler ASCII
    t = unicodedata.normalize("NFKD", text)
    return (
        t.replace("—", "-")   # em dash → hyphen
         .replace("–", "-")   # en dash → hyphen
         .replace("’", "'")   # curly apostrophe → straight
         .replace("“", '"')   # left double quote → straight
         .replace("”", '"')   # right double quote → straight
         .lower().strip()
    )

def classify(text: str) -> EmotionSignals:
    t = _normalize(text)
    if any(w in t for w in NEG_WORDS):
        return EmotionSignals(label="frustrated", sentiment=-0.4)
    if any(w in t for w in POS_WORDS):
        return EmotionSignals(label="engaged", sentiment=0.5)
    # neutral fallback
    return EmotionSignals(label="calm", sentiment=0.0)

def estimate_perf(text: str) -> PerformanceSignals:
    # very rough heuristic: “I got it / I solved it” -> correct
    t1 = _normalize(text)
    perf = PerformanceSignals()
    if _CORRECT_RE.search(t1):
        perf.correct = True
        perf.accuracy_pct = 1.0
        perf.attempts = 1
    return perf
