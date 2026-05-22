from services.phase18_autonomous_canary_service_v2 import Phase18AutonomousCanaryServiceV2


def valid_config(**overrides):
    config = {
        "phase16_design_gate_satisfied": True,
        "phase17_shadow_review_passed": True,
        "mode": "autonomous_canary_candidate",
        "strategy": "ma_cross_risk_managed_v1",
        "symbols": ["BTC-USD"],
        "operator_canary_approval": True,
        "max_order_notional_usd": 2.0,
        "max_daily_notional_usd": 2.0,
        "max_daily_loss_usd": 2.0,
        "max_orders_per_day": 1,
        "open_orders": 0,
        "global_kill_switch_available": True,
        "auto_halt_after_any_anomaly": True,
        "post_order_reconciliation_required": True,
        "operator_alert_required": True,
        "canary_report_required": True,
        "canary_signoff_required": True,
        "scale_up_blocked_until_review": True,
        "pending_reconciliation_count": 0,
        "unresolved_canary_report_count": 0,
        "active_halt_count": 0,
    }
    config.update(overrides)
    return config


def valid_summary(**overrides):
    summary = {
        "attempted_orders": 1,
        "filled_orders": 1,
        "anomaly_count": 0,
        "reconciliation_issue_count": 0,
        "operator_alert_count": 1,
        "operator_signoff_recorded": True,
        "realized_loss_usd": 0.25,
        "scale_up_still_blocked": True,
    }
    summary.update(overrides)
    return summary


def names(result):
    return {item["name"] for item in result["blockers"]}


def test_phase18_policy_is_single_tiny_canary_candidate_only():
    policy = Phase18AutonomousCanaryServiceV2.policy()

    assert policy["release_scope"] == "single_tiny_autonomous_canary_candidate"
    assert policy["live_order_submission_by_this_service"] == "not_allowed"
    assert policy["allowed_symbols"] == ["BTC-USD"]
    assert policy["max_orders_per_day"] == 1


def test_phase18_valid_candidate_passes_review_gate_without_submission():
    result = Phase18AutonomousCanaryServiceV2.evaluate_candidate(valid_config())

    assert result["status"] == "canary_candidate_ready"
    assert result["ready_for_single_tiny_autonomous_canary_review"] is True
    assert result["live_order_submission_by_this_service"] is False
    assert result["blockers"] == []


def test_phase18_requires_phase16_phase17_and_explicit_mode():
    result = Phase18AutonomousCanaryServiceV2.evaluate_candidate(
        valid_config(
            phase16_design_gate_satisfied=False,
            phase17_shadow_review_passed=False,
            mode="shadow",
        )
    )

    blockers = names(result)
    assert "phase16_design_gate_satisfied" in blockers
    assert "phase17_shadow_review_passed" in blockers
    assert "canary_mode_explicit" in blockers


def test_phase18_blocks_bad_strategy_symbol_and_missing_operator_approval():
    result = Phase18AutonomousCanaryServiceV2.evaluate_candidate(
        valid_config(strategy="unknown", symbols=["BTC-USD", "ETH-USD"], operator_canary_approval=False)
    )

    blockers = names(result)
    assert "strategy_is_single_and_allowlisted" in blockers
    assert "symbol_is_single_and_allowlisted" in blockers
    assert "operator_canary_approval_present" in blockers


def test_phase18_blocks_bad_limits_and_open_orders():
    result = Phase18AutonomousCanaryServiceV2.evaluate_candidate(
        valid_config(
            max_order_notional_usd=5,
            max_daily_notional_usd=10,
            max_daily_loss_usd=5,
            max_orders_per_day=2,
            open_orders=2,
        )
    )

    blockers = names(result)
    assert "tiny_notional_caps_enforced" in blockers
    assert "one_order_limit_enforced" in blockers


def test_phase18_blocks_missing_halt_post_order_and_unresolved_state_controls():
    result = Phase18AutonomousCanaryServiceV2.evaluate_candidate(
        valid_config(
            global_kill_switch_available=False,
            auto_halt_after_any_anomaly=False,
            post_order_reconciliation_required=False,
            operator_alert_required=False,
            canary_report_required=False,
            canary_signoff_required=False,
            scale_up_blocked_until_review=False,
            pending_reconciliation_count=1,
            unresolved_canary_report_count=1,
            active_halt_count=1,
        )
    )

    blockers = names(result)
    assert "halt_controls_enabled" in blockers
    assert "post_order_controls_required" in blockers
    assert "scale_up_blocked_until_review" in blockers
    assert "no_unresolved_state" in blockers


def test_phase18_valid_post_canary_summary_passes_but_keeps_scale_blocked():
    result = Phase18AutonomousCanaryServiceV2.evaluate_post_canary_review(valid_summary())

    assert result["status"] == "canary_review_passed"
    assert result["ready_for_production_release_review"] is True
    assert result["blockers"] == []


def test_phase18_post_canary_review_blocks_anomalies_and_scale_up():
    result = Phase18AutonomousCanaryServiceV2.evaluate_post_canary_review(
        valid_summary(
            attempted_orders=2,
            filled_orders=2,
            anomaly_count=1,
            reconciliation_issue_count=1,
            operator_alert_count=0,
            operator_signoff_recorded=False,
            realized_loss_usd=5.0,
            scale_up_still_blocked=False,
        )
    )

    blockers = names(result)
    assert "single_canary_attempt_only" in blockers
    assert "no_anomalies_or_reconciliation_issues" in blockers
    assert "operator_alert_and_signoff_recorded" in blockers
    assert "loss_within_tiny_limit" in blockers
    assert "scale_up_still_blocked" in blockers
