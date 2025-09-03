# tests/test_emotion.py
import pytest
from app.services import emotion

def test_estimate_perf_detects_got_it():
    perf = emotion.estimate_perf("Got it—give me a harder one!")
    assert perf.correct is True
    assert perf.accuracy_pct == 1.0

def test_estimate_perf_detects_solved_it():
    perf = emotion.estimate_perf("I solved it!")
    assert perf.correct is True

def test_estimate_perf_detects_worked_it_out():
    perf = emotion.estimate_perf("I worked it out.")
    assert perf.correct is True

def test_estimate_perf_neutral_when_no_keywords():
    perf = emotion.estimate_perf("I still feel confused.")
    assert perf.correct is None
