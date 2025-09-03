# app/services/reward.py
def compute(emotion, perf) -> float:
    base = 0.0
    if perf.correct:
        base += 0.5
    if perf.time_to_solve_sec is not None:
        base += max(0.0, 0.3 - min(perf.time_to_solve_sec, 30)/100.0)
    if emotion.label == "frustrated":
        base -= 0.2
    if emotion.label == "engaged":
        base += 0.2
    return round(max(-1.0, min(1.0, base)), 2)   # force a float
