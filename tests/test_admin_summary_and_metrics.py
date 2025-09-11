from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_health_full_has_ffmpeg_and_db_keys():
    resp = client.get('/api/v1/health/full')
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert 'components' in data
    comps = data['components']
    assert 'openai_key' in comps
    assert 'database' in comps
    assert 'ffmpeg' in comps

def test_metrics_endpoints_available():
    resp1 = client.get('/api/v1/metrics')
    assert resp1.status_code in (200, 503)
    snap = resp1.json()
    assert isinstance(snap, dict)
    resp2 = client.get('/api/v1/metrics/series')
    assert resp2.status_code in (200, 503)
    series = resp2.json()
    assert isinstance(series, dict)
    assert 'points' in series

def test_admin_summary_endpoint_available():
    resp = client.get('/api/v1/admin/summary')
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert 'sessions' in data
    assert 'filters' in data
