# AI687 Capstone – Utility Script (SEED01): Seed EQīLevel Turns
# Topic: Metrics + Emotion-Aware Seeding (Robotics-dance remix 🤖🕺)
# ---------------------------------------------------------------
# Seeds a session with randomized turns so the metrics dashboard lights up.
# - If --session is omitted, a new session row is created (committed).
# - Posts turns to /api/v1/turn/log with varied emotions, pacing, difficulty, and rewards.
# - Prints a summary and the session id used.
#
# Usage examples:
#   python scripts/seed_turns.py --session 6 --n 20
#   python scripts/seed_turns.py --host http://127.0.0.1:8000 --n 12
#
# Error handling included. Have fun, test safely.

import argparse
import json
import random
import sys
import time
from typing import Dict, Any, List, Tuple

import requests

# Optional: create a session directly via DB if not provided
def create_session_via_db() -> int:
    try:
        from sqlalchemy import text
        from app.services.storage import engine
    except Exception as e:
        raise RuntimeError(
            "Could not import SQLAlchemy engine from app.services.storage. "
            "Run inside the project venv where EQīLevel is available."
        ) from e

    try:
        with engine.begin() as c:
            sid = c.execute(text("INSERT INTO sessions DEFAULT VALUES RETURNING id")).scalar()
        if not isinstance(sid, int):
            raise RuntimeError(f"Unexpected session id type: {sid!r}")
        return sid
    except Exception as e:
        raise RuntimeError(f"Failed to create session via DB: {e}") from e


def post_turn(host: str, payload: Dict[str, Any], reward: float) -> Dict[str, Any]:
    url = f"{host.rstrip('/')}/api/v1/turn/log?reward={reward}"
    headers = {"Content-Type": "application/json"}
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    r.raise_for_status()
    return r.json()


def sample_turn(session_id: int) -> Tuple[Dict[str, Any], float]:
    # Emotions, mapped to preferred tutoring adjustments
    cases = [
        ("engaged",    {"tone": "encouraging", "pacing": "medium", "difficulty": "hold", "next_step": "quiz"},  (0.08, 0.16)),
        ("frustrated", {"tone": "warm",        "pacing": "slow",   "difficulty": "down", "next_step": "example"}, (0.02, 0.08)),
        ("calm",       {"tone": "neutral",     "pacing": "medium", "difficulty": "hold", "next_step": "prompt"},  (0.06, 0.12)),
        ("bored",      {"tone": "concise",     "pacing": "fast",   "difficulty": "up",   "next_step": "quiz"},    (0.04, 0.10)),
    ]
    label, mcp, (rmin, rmax) = random.choice(cases)

    # Small narrative variety for user/reply text
    user_templates = {
        "engaged":    ["This was easy", "That clicked!", "Got it—more please"],
        "frustrated": ["I'm stuck", "This is confusing", "I can't get this one"],
        "calm":       ["Okay, I get it", "That makes sense", "I'm following"],
        "bored":      ["This is too easy", "Can we speed up?", "Give me a challenge"],
    }
    reply_templates = {
        "engaged":    ["Great pace—let's keep it going.", "Awesome—ready for a quick quiz."],
        "frustrated": ["No stress—let's try a simpler example together.", "We’ll slow down and unpack it step-by-step."],
        "calm":       ["Nice—here's the next step when you're ready.", "Good—want to try a guided prompt next?"],
        "bored":      ["Let's pick up the pace and try a tougher problem.", "Boosting difficulty—ready for a challenge?"],
    }

    user_text = random.choice(user_templates[label])
    reply_text = random.choice(reply_templates[label])

    performance = {"correct": label in ("engaged", "calm", "bored")}

    reward = round(random.uniform(rmin, rmax), 2)

    payload = {
        "session_id": session_id,
        "user_text": user_text,
        "reply_text": reply_text,
        "emotion": {"label": label},
        "performance": performance,
        "mcp": mcp,
    }
    return payload, reward


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:8000", help="FastAPI base URL")
    parser.add_argument("--session", type=int, help="Existing session id. If omitted, a new session will be created via DB")
    parser.add_argument("--n", type=int, default=12, help="Number of turns to seed")
    parser.add_argument("--sleep", type=float, default=0.1, help="Pause between posts (seconds)")
    args = parser.parse_args()

    try:
        if args.session is None:
            session_id = create_session_via_db()
            print(f"[seed] Created session: {session_id}")
        else:
            session_id = args.session
            print(f"[seed] Using existing session: {session_id}")

        successes: List[int] = []
        for i in range(args.n):
            payload, reward = sample_turn(session_id)
            try:
                resp = post_turn(args.host, payload, reward)
                ok = bool(resp.get("ok", False))
                turn_id = resp.get("turn_id")
                if ok and isinstance(turn_id, int):
                    successes.append(turn_id)
                    print(f"[seed] {i+1:02d}/{args.n} ok turn_id={turn_id} reward={reward} emotion={payload['emotion']['label']}")
                else:
                    print(f"[seed] {i+1:02d}/{args.n} FAILED (unexpected response): {resp}")
            except requests.RequestException as re:
                print(f"[seed] {i+1:02d}/{args.n} HTTP error: {re}")
            except Exception as e:
                print(f"[seed] {i+1:02d}/{args.n} Error: {e}")
            time.sleep(args.sleep)

        print("\n[summary]")
        print(f"  session_id: {session_id}")
        print(f"  turns_posted: {len(successes)}/{args.n}")
        if successes:
            print(f"  last_turn_id: {successes[-1]}")
        print("\nNext:")
        print(f"  - Open {args.host.rstrip('/')}/api/v1/metrics/dashboard")
        print(f"  - Or check: {args.host.rstrip('/')}/api/v1/metrics?since_minutes=60")

    except Exception as e:
        print(f"[fatal] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# REFERENCE: OpenAI. (2025). ChatGPT’s assistance with seeding EQīLevel metrics [Large language model]. https://openai.com/chatgpt
