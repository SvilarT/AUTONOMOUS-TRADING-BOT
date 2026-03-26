"""Unit tests for the RiskManager.

These tests validate basic calculations performed by the RiskManager,
such as exposure, equity and kill switch detection.  They also verify
that risk profiles scale limits appropriately.
"""

from __future__ import annotations

import pytest

from phase11.core.risk_manager import RiskManager


def test_portfolio_metrics_basic() -> None:
    """RiskManager computes correct equity and exposure with no positions."""
    rm = RiskManager(risk_profile="moderate")
    state = {"cash_balance": 10000.0, "equity_high": 10000.0, "daily_start_equity": 10000.0}
    positions: list[dict[str, float]] = []
    price_map: dict[str, float] = {}
    metrics = rm.portfolio_metrics(state, positions, price_map)
    assert metrics["total_equity"] == pytest.approx(10000.0)
    assert metrics["exposure_pct"] == 0.0


def test_kill_switch_on_daily_loss() -> None:
    """Kill switch triggers when daily loss exceeds threshold for conservative profile."""
    rm = RiskManager(risk_profile="conservative")
    # Construct metrics with daily loss > 0.03 (default max_daily_loss_pct scaled by 0.5 = 0.015)
    metrics = {"daily_loss_pct": 0.02, "drawdown_pct": 0.0, "exposure_pct": 0.0, "volatility": {}}
    result = rm.should_kill_switch(metrics)
    assert result["triggered"] is True
    assert "daily loss" in result["reason"].lower()


def test_can_open_position_limits() -> None:
    """Ensure position sizing limits are enforced."""
    rm = RiskManager(max_position_notional=100.0, max_total_exposure_pct=0.2)
    metrics = {
        "total_equity": 1000.0,
        "exposure_pct": 0.19,
        "volatility": {},
        "daily_loss_pct": 0.0,
        "drawdown_pct": 0.0,
    }
    # Proposed notional of 200 would exceed both position and exposure limits
    allowed = rm.can_open_position(metrics, [], proposed_notional=200.0)
    assert allowed["allowed"] is False
    assert "exposure" in allowed["reason"].lower() or "notional" in allowed["reason"].lower()
