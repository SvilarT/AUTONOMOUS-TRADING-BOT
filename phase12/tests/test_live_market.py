"""Tests for live market dashboard and WebSocket trade streaming.

These tests verify that the live dashboard page is served correctly
and that trade events are broadcast over the WebSocket endpoint.  The
first test checks that the HTML contains the expected title.  The
second test uses FastAPI's TestClient to open a WebSocket connection,
submit a trade via the REST API and assert that a corresponding
message is received.  For simplicity the test sends a small BUY
order to avoid triggering risk limits.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from phase12.api.main import create_app


def test_live_dashboard_page_served() -> None:
    app = create_app()
    with TestClient(app) as client:
        resp = client.get("/live")
        assert resp.status_code == 200
        # Check for the title in the response body
        assert "Live Market Trades" in resp.text


def test_trade_event_broadcast() -> None:
    app = create_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws/trades") as websocket:
            # Submit a small BUY trade that should succeed under default risk limits
            resp = client.post(
                "/users/test_user/trade",
                json={"symbol": "BTC-USD", "action": "BUY", "notional": 10.0},
            )
            assert resp.status_code == 200
            data = websocket.receive_json()
            assert data["symbol"] == "BTC-USD"
            assert data["action"] == "BUY"
            # Notional may differ depending on execution; ensure it's numeric
            assert isinstance(data["notional"], (int, float))