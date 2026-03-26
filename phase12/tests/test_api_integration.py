"""Integration tests for FastAPI endpoints.

These tests spin up the application using FastAPI's TestClient and
exercise selected endpoints from the marketplace, security and
compliance routers.  They verify that routes are registered and
respond with expected data structures.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# Import the Phase 11 API factory.
# Import the Phase 12 API factory
from phase12.api.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Provide a TestClient that triggers startup/shutdown events."""
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_marketplace_endpoints(client: TestClient) -> None:
    # Register a new strategy
    resp = client.post(
        "/marketplace/strategies",
        json={"name": "Test", "version": "1.0", "author": "Tester"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    # List strategies should return at least one entry
    resp_list = client.get("/marketplace/strategies")
    assert resp_list.status_code == 200
    assert isinstance(resp_list.json(), list)
    assert len(resp_list.json()) >= 1
    # Rate the strategy
    resp_rate = client.post(f"/marketplace/strategies/{data['id']}/rating", json={"rating": 4.5})
    assert resp_rate.status_code == 200
    assert resp_rate.json()["reputation"] > 0


def test_security_endpoints(client: TestClient) -> None:
    # Set and retrieve a secret
    set_resp = client.post("/security/secrets", json={"key": "TEST_SECRET", "value": "secret"})
    assert set_resp.status_code == 200
    get_resp = client.get("/security/secrets/TEST_SECRET")
    assert get_resp.status_code == 200
    assert get_resp.json()["value"] == "secret"
    # Deposit and withdraw
    dep = client.post("/security/deposit", json={"asset": "BTC", "amount": 1.0, "address": "addr"})
    assert dep.status_code == 200
    wd = client.post("/security/withdraw", json={"asset": "BTC", "amount": 0.5, "address": "dest"})
    assert wd.status_code == 200


def test_compliance_endpoints(client: TestClient) -> None:
    # KYC
    kyc_resp = client.post("/compliance/kyc", json={"user_id": "u123", "documents": {"id": "mock"}})
    assert kyc_resp.status_code == 200
    assert kyc_resp.json()["verified"] is True
    # AML monitoring
    aml_resp = client.post("/compliance/aml", json={"user_id": "u123", "transactions": [{"amount": 15000.0, "asset": "BTC", "destination": "dest"}]})
    assert aml_resp.status_code == 200
    assert aml_resp.json()[0]["flagged"] is True
