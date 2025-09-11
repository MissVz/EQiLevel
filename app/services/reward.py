# app/services/reward.py
import re

ONE_QUESTION_STEPS = {"quiz", "prompt"}

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


def _count_questions(text: str) -> int:
    if not text:
        return 0
    # fast path: count literal question marks
    return text.count("?")


def shape_with_reply(base_reward: float, mcp, reply_text: str) -> float:
    """Adjust reward based on the tutor's reply quality with respect to
    the one-question policy.

    Heuristics:
      - When next_step ∈ {quiz, prompt}:
          exactly one question mark → +0.1
          zero question marks       → −0.25
          multiple question marks   → −0.15 per extra question (cap −0.4)
      - Otherwise (explain/example/review): presence of question marks → −0.1 (avoid new questions).
      - Long question penalty: if the final question (up to '?') exceeds ~160 chars → −0.1
    """
    r = float(base_reward)
    text = reply_text or ""
    nq = _count_questions(text)
    step = getattr(mcp, "next_step", None)
    try:
        if step in ONE_QUESTION_STEPS:
            if nq == 1:
                r += 0.10
            elif nq == 0:
                r -= 0.25
            else:
                r -= min(0.4, 0.15 * (nq - 1))
        else:
            if nq > 0:
                r -= 0.10

        # Long-question shaping
        if nq >= 1:
            idx = text.rfind("?")
            if idx != -1:
                # naive length of last sentence before '?'
                start = max(0, text.rfind(".\n", 0, idx), text.rfind(". ", 0, idx), text.rfind("\n", 0, idx))
                qlen = idx - start
                if qlen > 160:
                    r -= 0.10
    except Exception:
        pass

    return round(max(-1.0, min(1.0, r)), 3)
