# tests/test_emotion_prompt.py
# Unit tests for emotion_prompt module
# Purpose: Validate emotion_prompt module’s functionality, parsing, and logging
# Assignment: AI687 HOS04B – Emotion Prompting Unit Tests

import sys
import os
from pathlib import Path

# Ensure project root is in sys.path so `src` package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import pytest
from datetime import datetime
from src.nlp.emotion_prompt import (
    load_transcript,
    build_prompt,
    analyze_emotion,
    save_output
)

# Sample transcript dict for testing 'easy' audio scenario
# Uses the project’s easy.m4a to simulate clear, positive feedback
SAMPLE = {
    "audio_file": "easy.m4a",
    "text": "I love this lesson, it's super clear and easy!"
}


def test_load_transcript(tmp_path):
    """
    GIVEN a valid transcript JSON file
    WHEN load_transcript() reads it
    THEN the returned dict matches the original data
    """
    p = tmp_path / "transcript.json"
    p.write_text(json.dumps(SAMPLE), encoding="utf-8")
    data = load_transcript(str(p))
    assert data == SAMPLE


def test_build_prompt_contains_transcript():
    """
    Ensure the prompt built by build_prompt() includes the transcript text
    and the instruction to respond with raw JSON only.
    """
    prompt = build_prompt(SAMPLE["text"])
    assert SAMPLE["text"] in prompt
    assert "Respond with raw JSON only" in prompt


def test_analyze_emotion_mock(monkeypatch):
    """
    Simulate a GPT-4o API response and verify analyze_emotion() correctly
    parses the JSON and returns the expected emotion_analysis structure.
    """
    class DummyChoice:
        message = {"content": '{"emotion":"happy","confidence":0.99,"explanation":"Test explanation"}'}
    class DummyClient:
        chat = type("C", (), {"completions": type("C2", (), {
            "create": staticmethod(lambda **kwargs: type("R", (), {"choices":[DummyChoice]})())
        })})
    monkeypatch.setattr("src.nlp.emotion_prompt.client", DummyClient())
    result = analyze_emotion(SAMPLE)
    emo = result["emotion_analysis"]
    assert emo["emotion"] == "happy"
    assert pytest.approx(emo["confidence"], 0.01) == 0.99
    assert "Test explanation" in emo["explanation"]


def test_save_output(tmp_path, capsys):
    """
    GIVEN a valid emotion analysis dict
    WHEN save_output() writes it to disk
    THEN the file exists, content matches, and a summary is printed
    """
    out_file = tmp_path / "out.json"
    data = {
        "timestamp": datetime.now().isoformat(),
        "input_file": "easy.m4a",
        "transcript": "test text",
        "emotion_analysis": {
            "emotion": "test",
            "confidence": 1.0,
            "explanation": "ok"
        }
    }
    # Act
    save_output(data, str(out_file))

    # Assert: file was created and content matches
    assert out_file.exists()
    saved = json.loads(out_file.read_text(encoding="utf-8"))
    assert saved == data

    # Capture console output summary
    captured = capsys.readouterr().out
    assert "Summary → Emotion: test" in captured

# -------------------------------------------------------------
# OpenAI Acknowledgement:
# This test suite was developed with assistance from OpenAI’s ChatGPT (2025) [Large Language Model].
