from services.audit_live_risk_policy_v2 import AuditLiveRiskPolicyV2


def test_audit_live_risk_policy_blocks_capital_floor_and_daily_loss():
    policy = AuditLiveRiskPolicyV2(
        capital_floor_usd=50,
        max_order_notional_usd=25,
        max_daily_loss_pct=0.02,
    )

    decision = policy.evaluate(
        equity_usd=1000,
        cash_usd=60,
        daily_pnl_usd=-25,
        open_positions=[],
        symbol="BTC-USD",
        order_notional_usd=20,
        trades_today=0,
    )

    assert decision["allowed"] is False
    assert "capital_floor_would_be_breached" in decision["reasons"]
    assert "max_daily_loss_exceeded" in decision["reasons"]


def test_audit_live_risk_policy_allows_conservative_order():
    policy = AuditLiveRiskPolicyV2(max_order_notional_usd=25)

    decision = policy.evaluate(
        equity_usd=1000,
        cash_usd=500,
        daily_pnl_usd=0,
        open_positions=[],
        symbol="BTC-USD",
        order_notional_usd=20,
        trades_today=0,
    )

    assert decision["allowed"] is True
    assert decision["reasons"] == []
