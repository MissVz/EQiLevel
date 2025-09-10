# tests/test_policy.py
import pytest
from app.models import MCP, EmotionSignals, PerformanceSignals, LearningStyle
from app.services import policy

def test_policy_update_changes_mcp():
    mcp = MCP(
        emotion=EmotionSignals(label="engaged", sentiment=0.5),
        performance=PerformanceSignals(correct=True, attempts=1),
        learning_style=LearningStyle(visual=1.0),
        tone="neutral",
        pacing="medium",
        difficulty="hold",
        style="visual",
        next_step="prompt"
    )
    reward = 1.0
    new_mcp = policy.update(mcp, reward)
    assert isinstance(new_mcp, MCP)
    # Should adapt at least one field
    assert (
        new_mcp.difficulty != mcp.difficulty or
        new_mcp.pacing != mcp.pacing or
        new_mcp.tone != mcp.tone
    )
