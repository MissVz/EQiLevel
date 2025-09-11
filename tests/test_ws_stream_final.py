import json
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_ws_voice_finalizes_without_audio():
    with client.websocket_connect('/ws/voice') as ws:
        # server should announce readiness first
        msg = ws.receive_json()
        assert msg.get('type') == 'ready'
        # Send stop without any audio bytes
        ws.send_text(json.dumps({ 'event': 'stop' }))
        final = None
        for _ in range(4):
            m = ws.receive_json()
            if m.get('type') == 'final':
                final = m
                break
        assert final is not None
        assert 'reply' in final and 'text' in final['reply']

