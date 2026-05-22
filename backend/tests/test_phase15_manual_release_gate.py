from services.phase15_controlled_manual_live_service_v2 import Phase15ControlledManualLiveServiceV2


def valid_config(**overrides):
    config = {
        "phase13_release_approved": True,
        "phase14_operations_ready": True,
        "mode": "controlled_manual_live",
        "autonomous_live_enabled": False,
        "manual_approval_required": True,
        "signed_approval_required": True,
        "dry_run_required_before_each_order": True,
        "post_order_reconciliation_required": True,
        "pilot_report_required_after_each_order": True,
        "operator_signoff_required_after_each_order": True,
        "kill_switch_closed_when_idle": True,
        "allowed_symbols": ["BTC-USD", "ETH-USD"],
        "max_order_notional_usd": 10.0,
        "max_daily_notional_usd": 50.0,
        "max_orders_per_day": 5,
        "open_live_orders": 0,
        "pending_reconciliation_count": 0,
        "unsigned_completed_report_count": 0,
        "active_halt_count": 0,
    }
    config.update(overrides)
    return config


def blocker_names(result):
    return {item["name"] for item in result["blockers"]}


def test_phase15_policy_is_limited_and_manual_only():
    policy = Phase15ControlledManualLiveServiceV2.policy()

    assert policy["release_scope"] == "limited_repeated_manual_live_only"
    assert policy["autonomous_live_trading"] == "not_allowed"
    assert policy["required_mode"] == "controlled_manual_live"


def test_phase15_valid_config_is_ready():
    result = Phase15ControlledManualLiveServiceV2.evaluate_config(valid_config())

    assert result["ready_for_controlled_manual_live"] is True
    assert result["status"] == "controlled_manual_live_ready"
    assert result["blockers"] == []


def test_phase15_requires_prior_release_and_operations_approval():
    result = Phase15ControlledManualLiveServiceV2.evaluate_config(
        valid_config(phase13_release_approved=False, phase14_operations_ready=False)
    )

    names = blocker_names(result)
    assert "phase13_release_approved" in names
    assert "phase14_operations_ready" in names


def test_phase15_blocks_autonomous_mode_and_missing_human_controls():
    result = Phase15ControlledManualLiveServiceV2.evaluate_config(
        valid_config(
            autonomous_live_enabled=True,
            manual_approval_required=False,
            signed_approval_required=False,
            dry_run_required_before_each_order=False,
        )
    )

    names = blocker_names(result)
    assert "autonomous_live_disabled" in names
    assert "manual_approval_required" in names
    assert "signed_approval_required" in names
    assert "dry_run_required_before_each_order" in names


def test_phase15_blocks_missing_after_order_controls():
    result = Phase15ControlledManualLiveServiceV2.evaluate_config(
        valid_config(
            post_order_reconciliation_required=False,
            pilot_report_required_after_each_order=False,
            operator_signoff_required_after_each_order=False,
        )
    )

    names = blocker_names(result)
    assert "post_order_reconciliation_required" in names
    assert "post_order_report_and_signoff_required" in names


def test_phase15_blocks_bad_limits_and_unresolved_state():
    result = Phase15ControlledManualLiveServiceV2.evaluate_config(
        valid_config(
            allowed_symbols=["BTC-USD", "DOGE-USD"],
            max_order_notional_usd=25,
            max_daily_notional_usd=100,
            max_orders_per_day=10,
            open_live_orders=2,
            pending_reconciliation_count=1,
            unsigned_completed_report_count=1,
            active_halt_count=1,
        )
    )

    names = blocker_names(result)
    assert "symbols_are_allowlisted" in names
    assert "max_order_notional_limited" in names
    assert "max_daily_notional_limited" in names
    assert "order_frequency_limited" in names
    assert "open_live_orders_limited" in names
    assert "no_unresolved_live_state" in names
