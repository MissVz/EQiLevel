# scripts/plot_metrics.py
import os, sqlite3, json
from datetime import datetime
import matplotlib.pyplot as plt

DB = os.environ.get("EQ_DB", "eqilevel.db")
OUT = "outputs"
os.makedirs(OUT, exist_ok=True)

def fetch_turns():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("SELECT id, session_id, created_at, reward, emotion, mcp FROM turns ORDER BY id ASC")
    rows = cur.fetchall()
    con.close()
    parsed = []
    for id_, sid, ts, rwd, emo, mcp in rows:
        try:
            emo = json.loads(emo or "{}")
            mcp = json.loads(mcp or "{}")
        except Exception:
            emo, mcp = {}, {}
        parsed.append({
            "id": id_, "session_id": sid,
            "ts": datetime.fromisoformat(ts) if isinstance(ts, str) else ts,
            "reward": rwd or 0.0,
            "emotion": emo.get("label"),
            "tone": mcp.get("tone"),
            "difficulty": mcp.get("difficulty"),
            "pacing": mcp.get("pacing"),
        })
    return parsed

def plot_reward_over_time(data, session=None):
    if session:
        data = [d for d in data if d["session_id"] == session]
    if not data: return
    xs = [d["id"] for d in data]
    ys = [d["reward"] for d in data]
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.title(f"Reward over time ({session or 'all sessions'})")
    plt.xlabel("Turn id"); plt.ylabel("Reward")
    plt.grid(True); plt.tight_layout()
    fn = os.path.join(OUT, f"reward_{session or 'all'}.png")
    plt.savefig(fn)
    print("Saved:", fn)

def plot_action_distribution(data, session=None):
    if session:
        data = [d for d in data if d["session_id"] == session]
    if not data: return
    from collections import Counter
    diff = Counter([d["difficulty"] for d in data if d["difficulty"]])
    tone = Counter([d["tone"] for d in data if d["tone"]])
    pacing = Counter([d["pacing"] for d in data if d["pacing"]])

    plt.figure(figsize=(7,4))
    plt.bar(diff.keys(), diff.values()); plt.title(f"Difficulty distribution ({session or 'all'})")
    plt.tight_layout(); fn1 = os.path.join(OUT, f"dist_difficulty_{session or 'all'}.png"); plt.savefig(fn1); print("Saved:", fn1)

    plt.figure(figsize=(7,4))
    plt.bar(tone.keys(), tone.values()); plt.title(f"Tone distribution ({session or 'all'})")
    plt.tight_layout(); fn2 = os.path.join(OUT, f"dist_tone_{session or 'all'}.png"); plt.savefig(fn2); print("Saved:", fn2)

    plt.figure(figsize=(7,4))
    plt.bar(pacing.keys(), pacing.values()); plt.title(f"Pacing distribution ({session or 'all'})")
    plt.tight_layout(); fn3 = os.path.join(OUT, f"dist_pacing_{session or 'all'}.png"); plt.savefig(fn3); print("Saved:", fn3)

if __name__ == "__main__":
    data = fetch_turns()
    plot_reward_over_time(data)                 # all sessions
    plot_action_distribution(data)              # all sessions
    for sid in sorted({d["session_id"] for d in data}):
        plot_reward_over_time(data, sid)
        plot_action_distribution(data, sid)
