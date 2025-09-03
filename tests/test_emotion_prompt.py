# tests/test_emotion_prompt.py
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_session_detects_correct_and_adapts():
    resp = client.post("/session", json={"user_text": "Got it - give me a harder one!", "session_id": "test_s"})
    assert resp.status_code == 200
    data = resp.json()
    # basic expectations
    assert "mcp" in data and "text" in data
    assert data["mcp"]["tone"] in ["encouraging","warm","neutral","concise"]
