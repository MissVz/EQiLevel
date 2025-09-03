# app/services/reward.py
def compute(emotion, perf) -> float:
    base = 0.05  # small positive baseline so 'neutral' turns aren't punished

    # correctness / performance
    if getattr(perf, "correct", None) is True:
        base += 0.5
    elif getattr(perf, "correct", None) is False:
        base -= 0.1

    if getattr(perf, "time_to_solve_sec", None) is not None:
        base += max(0.0, 0.25 - min(perf.time_to_solve_sec, 30)/120.0)  # smaller effect

    # emotion shaping (lighter penalties/bonuses)
    if emotion.label == "frustrated":
        base -= 0.1
    elif emotion.label == "engaged":
        base += 0.15
    elif emotion.label == "bored":
        base -= 0.05

    return round(max(-1.0, min(1.0, base)), 3)
