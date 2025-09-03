# tests/test_reward.py
import pytest
from app.models import EmotionSignals, PerformanceSignals
from app.services import reward

def test_reward_positive_for_correct_engaged():
    em = EmotionSignals(label="engaged", sentiment=0.5)
    perf = PerformanceSignals(correct=True, attempts=1)
    r = reward.compute(em, perf)
    assert r > 0.3

def test_reward_penalty_for_frustrated_wrong():
    em = EmotionSignals(label="frustrated", sentiment=-0.4)
    perf = PerformanceSignals(correct=False, attempts=1)
    r = reward.compute(em, perf)
    assert r < 0.0

def test_reward_baseline_neutral():
    em = EmotionSignals(label="calm", sentiment=0.0)
    perf = PerformanceSignals()
    r = reward.compute(em, perf)
    assert -0.1 <= r <= 0.1
