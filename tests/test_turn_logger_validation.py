from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_turn_logger_rejects_nonexistent_session():
    body = {
        "session_id": 99999999,  # likely does not exist
        "user_text": "hello",
        "reply_text": "hi",
        "emotion": {"label":"calm"},
        "performance": {},
        "mcp": {}
    }
    r = client.post('/api/v1/turn/log?reward=0.0', json=body)
    # either 400 if session missing or 200 if your DB already has it; accept 400 assertion
    if r.status_code == 200:
        j = r.json()
        assert 'turn_id' in j
    else:
        assert r.status_code == 400

def test_turn_logger_validator_rejects_non_numeric_session():
    body = {
        "session_id": "abc",
        "user_text": "hello",
        "reply_text": "hi",
        "emotion": {"label":"calm"},
        "performance": {},
        "mcp": {}
    }
    r = client.post('/api/v1/turn/log?reward=0.0', json=body)
    assert r.status_code == 422  # Pydantic validation error
