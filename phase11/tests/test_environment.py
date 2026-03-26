"""Tests for environment and feature flag endpoints.

These tests ensure that the ``/environment`` and ``/features``
endpoints return values consistent with the configuration file.  The
default configuration defines ``mode: paper`` and a couple of disabled
feature flags.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from phase11.api.main import create_app


def test_environment_endpoint() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/environment")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "paper"


def test_features_endpoint() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/features")
        assert resp.status_code == 200
        flags = resp.json().get("flags")
        # The default config sets both flags to false
        assert isinstance(flags, dict)
        assert flags.get("beta_ml_strategy") is False
        assert flags.get("advanced_risk_dashboard") is False