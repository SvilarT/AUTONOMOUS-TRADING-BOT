from services.phase16_autonomous_gate_service_v2 import Phase16AutonomousGateServiceV2


def valid_config(**overrides):
    config = {
        "mode": "autonomous_live_candidate",
        "autonomous_execution_enabled": False,
        "strategy": "ma_cross_risk_managed_v1",
        "symbols": ["BTC-USD", "ETH-USD"],
        "strategy_operator_approved": True,
        "manual_override_enabled": True,
        "emergency_halt_enabled": True,
        "market_data_max_age_seconds": 30,
        "exchange_connectivity_gate_enabled": True,
        "max_order_notional_usd": 5.0,
        "max_daily_notional_usd": 25.0,
        "max_daily_loss_usd": 10.0,
        "max_drawdown_pct": 2.0,
        "max_open_positions": 1,
        "min_signal_confidence": 0.75,
        "backtest_passed": True,
        "backtest_trades": 30,
        "walk_forward_passed": True,
        "walk_forward_windows": 3,
        "shadow_mode_passed": True,
        "shadow_days_completed": 14,
        "cooldown_after_loss_minutes": 1440,
        "cooldown_after_error_minutes": 60,
        "post_order_reconciliation_required": True,
        "reconciliation_interval_minutes": 15,
        "audit_chain_required": True,
    }
    config.update(overrides)
    return config


def names(result):
    return {item["name"] for item in result["blockers"]}


def test_phase16_policy_is_design_only():
    policy = Phase16AutonomousGateServiceV2.policy()

    assert policy["release_scope"] == "design_only_no_execution"
    assert policy["autonomous_execution_enabled"] is False
    assert policy["required_mode"] == "autonomous_live_candidate"


def test_phase16_valid_design_passes_without_enabling_execution():
    result = Phase16AutonomousGateServiceV2.evaluate_design(valid_config())

    assert result["status"] == "design_gate_satisfied"
    assert result["ready_for_autonomous_shadow_mode_design_review"] is True
    assert result["autonomous_execution_enabled"] is False
    assert result["blockers"] == []


def test_phase16_blocks_bad_identity_inputs():
    result = Phase16AutonomousGateServiceV2.evaluate_design(
        valid_config(mode="other", strategy="unknown", symbols=["DOGE-USD"])
    )

    blockers = names(result)
    assert "candidate_mode_explicit" in blockers
    assert "strategy_is_allowlisted" in blockers
    assert "symbols_are_allowlisted" in blockers


def test_phase16_blocks_missing_safety_controls():
    result = Phase16AutonomousGateServiceV2.evaluate_design(
        valid_config(
            autonomous_execution_enabled=True,
            strategy_operator_approved=False,
            manual_override_enabled=False,
            emergency_halt_enabled=False,
            exchange_connectivity_gate_enabled=False,
        )
    )

    blockers = names(result)
    assert "autonomous_execution_disabled_in_design_phase" in blockers
    assert "strategy_operator_approved" in blockers
    assert "manual_override_and_emergency_halt_enabled" in blockers
    assert "exchange_connectivity_gate_defined" in blockers


def test_phase16_blocks_weak_evidence_and_limits():
    result = Phase16AutonomousGateServiceV2.evaluate_design(
        valid_config(
            max_order_notional_usd=50,
            max_daily_notional_usd=100,
            max_daily_loss_usd=25,
            max_drawdown_pct=10,
            max_open_positions=5,
            min_signal_confidence=0.25,
            backtest_passed=False,
            backtest_trades=5,
            walk_forward_passed=False,
            walk_forward_windows=1,
            shadow_mode_passed=False,
            shadow_days_completed=1,
        )
    )

    blockers = names(result)
    assert "risk_limits_are_tiny_and_explicit" in blockers
    assert "strategy_confidence_threshold_defined" in blockers
    assert "backtest_evidence_sufficient" in blockers
    assert "walk_forward_evidence_sufficient" in blockers
    assert "shadow_mode_required_before_canary" in blockers


def test_phase16_blocks_missing_reconciliation_audit_and_cooldowns():
    result = Phase16AutonomousGateServiceV2.evaluate_design(
        valid_config(
            cooldown_after_loss_minutes=30,
            cooldown_after_error_minutes=5,
            post_order_reconciliation_required=False,
            reconciliation_interval_minutes=60,
            audit_chain_required=False,
        )
    )

    blockers = names(result)
    assert "cooldowns_defined" in blockers
    assert "reconciliation_and_audit_required" in blockers
