"""Integration tests for the monitoring API.

These tests ensure that the health and metrics endpoints are registered
and return expected status codes and content.  The metrics endpoint
should expose our custom Prometheus metrics names, even if no trades
have been processed yet.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from phase12.api.main import create_app


def test_health_and_metrics_endpoints() -> None:
    """The monitoring endpoints return healthy status and metric names."""
    with TestClient(create_app()) as client:
        # Health endpoint should return status 1
        resp = client.get("/monitoring/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == 1
        # Metrics endpoint should include our metric names
        resp2 = client.get("/monitoring/metrics")
        assert resp2.status_code == 200
        body = resp2.text
        assert "trade_requests_total" in body
        assert "trade_latency_seconds" in body
        assert "risk_events_total" in body
        assert "service_health" in body