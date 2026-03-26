"""Integration tests for the notifications API.

These tests verify that the notification endpoints accept requests and
return a successful status.  They exercise trade confirmations, risk
alerts and system status broadcasts.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from phase11.api.main import create_app


def test_notification_endpoints() -> None:
    """Notification endpoints should return a sent status for valid requests."""
    with TestClient(create_app()) as client:
        # Trade confirmation
        resp = client.post(
            "/notifications/trade-confirmation",
            json={"user_id": "u123", "details": {"symbol": "BTC", "filled_price": 100.0}},
        )
        assert resp.status_code == 200
        assert resp.json().get("status") == "sent"
        # Risk alert
        resp2 = client.post(
            "/notifications/risk-alert",
            json={"user_id": "u123", "message": "Margin limit exceeded"},
        )
        assert resp2.status_code == 200
        assert resp2.json().get("status") == "sent"
        # System status broadcast
        resp3 = client.post(
            "/notifications/system-status",
            json={"message": "System maintenance scheduled"},
        )
        assert resp3.status_code == 200
        assert resp3.json().get("status") == "sent"