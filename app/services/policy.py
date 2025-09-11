# app/services/policy.py
# Minimal “policy”: apply small nudges based on reward
from app.models import MCP

def update(mcp: MCP, reward: float) -> MCP:
    """
    Return a NEW MCP with small nudges based on reward.
    Note: does not mutate the input object (important for tests and purity).
    """
    new_mcp = MCP(**mcp.model_dump())
    # Nudge pacing and difficulty if reward is poor/good
    if reward < 0:
        # slow down, reduce difficulty
        new_mcp.pacing = "slow"
        new_mcp.difficulty = "down"
        new_mcp.tone = "warm"
        # emphasize concrete help
        new_mcp.next_step = "example"
    elif reward > 0.5:
        # challenge a bit
        new_mcp.pacing = "fast"
        new_mcp.difficulty = "up"
        new_mcp.tone = "encouraging"
        new_mcp.next_step = "quiz"
    return new_mcp
