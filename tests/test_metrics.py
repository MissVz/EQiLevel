# tests/test_metrics.py
from app.services.metrics import compute_metrics

def test_compute_metrics_runs_smoke():
    data = compute_metrics()
    assert "turns_total" in data
    assert "avg_reward" in data