
from app.main import app
from fastapi.testclient import TestClient
import pytest

client = TestClient(app)

def test_analyze_api():
    req = {"user_text": "I solved it!", "session_id": "test_s", "correct": True}
    resp = client.post("/analyze", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert "emotion" in data and "performance" in data

def test_echo():
    req = {"user_text": "Hello!", "session_id": "test_echo"}
    resp = client.post("/echo", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["user_text"] == "Hello!"
    assert data["session_id"] == "test_echo"

def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") == "ok"

def test_mcp_build_api():
    ctx = {
        "transcript": "I solved it!",
        "emotion": {"label": "engaged", "sentiment": 0.5},
        "performance": {"correct": True, "attempts": 1},
        "mcp": {
            "emotion": {"label": "engaged", "sentiment": 0.5},
            "performance": {"correct": True, "attempts": 1},
            "learning_style": {"visual": 1.0, "auditory": 0.0, "reading_writing": 0.0, "kinesthetic": 0.0},
            "tone": "neutral",
            "pacing": "medium",
            "difficulty": "hold",
            "style": "visual",
            "next_step": "prompt"
        }
    }
    resp = client.post("/mcp/build", json=ctx)
    assert resp.status_code == 200
    data = resp.json()
    assert "tone" in data and "difficulty" in data

def test_metrics_api():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "turns_total" in data
    assert "avg_reward" in data

def test_policy_step_api():
    ctx = {
        "transcript": "I solved it!",
        "emotion": {"label": "engaged", "sentiment": 0.5},
        "performance": {"correct": True, "attempts": 1},
        "mcp": {
            "emotion": {"label": "engaged", "sentiment": 0.5},
            "performance": {"correct": True, "attempts": 1},
            "learning_style": {"visual": 1.0, "auditory": 0.0, "reading_writing": 0.0, "kinesthetic": 0.0},
            "tone": "neutral",
            "pacing": "medium",
            "difficulty": "hold",
            "style": "visual",
            "next_step": "prompt"
        }
    }
    resp = client.post("/policy/step", json=ctx)
    assert resp.status_code == 200
    data = resp.json()
    assert "tone" in data and "difficulty" in data

def test_session_start():
    resp = client.post("/session/start")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data

def test_transcription_endpoint():
    import os
    import pytest
    sample_audio = os.path.join('samples', 'easy.m4a')
    if not os.path.exists(sample_audio):
        pytest.skip("Sample audio file not found.")
    with open(sample_audio, "rb") as f:
        files = {"file": ("easy.m4a", f, "audio/mp4")}
        resp = client.post("/transcribe", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data and "segments" in data

def test_tutor_reply():
    ctx = {
        "transcript": "What is 2+2?",
        "emotion": {"label": "engaged", "sentiment": 0.5},
        "performance": {"correct": True, "attempts": 1},
        "mcp": {
            "emotion": {"label": "engaged", "sentiment": 0.5},
            "performance": {"correct": True, "attempts": 1},
            "learning_style": {"visual": 1.0, "auditory": 0.0, "reading_writing": 0.0, "kinesthetic": 0.0},
            "tone": "neutral",
            "pacing": "medium",
            "difficulty": "hold",
            "style": "visual",
            "next_step": "prompt"
        }
    }
    resp = client.post("/tutor/reply", json=ctx)
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data and "mcp" in data
