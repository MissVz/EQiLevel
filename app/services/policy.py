# app/services/policy.py
# Minimal “policy”: apply small nudges based on reward
from app.models import MCP

def update(mcp: MCP, reward: float) -> MCP:
    # Nudge pacing and difficulty if reward is poor/good
    if reward < 0:
        # slow down, reduce difficulty
        mcp.pacing = "slow"
        mcp.difficulty = "down"
        mcp.tone = "warm"
        # emphasize concrete help
        mcp.next_step = "example"
    elif reward > 0.5:
        # challenge a bit
        mcp.pacing = "fast" if mcp.pacing != "fast" else "fast"
        mcp.difficulty = "up"
        mcp.tone = "encouraging"
        mcp.next_step = "quiz"
    return mcp
