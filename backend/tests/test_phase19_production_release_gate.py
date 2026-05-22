from services.phase19_production_live_release_service_v2 import Phase19ProductionLiveReleaseServiceV2


def valid_config(**overrides):
    config = {
        "phase15_controlled_manual_live_ready": True,
        "phase17_shadow_review_passed": True,
        "phase18_canary_review_passed": True,
        "phase14_operations_ready": True,
        "release_modes": sorted(Phase19ProductionLiveReleaseServiceV2.REQUIRED_RELEASE_MODES),
        "runbooks": sorted(Phase19ProductionLiveReleaseServiceV2.REQUIRED_RUNBOOKS),
        "monitors": sorted(Phase19ProductionLiveReleaseServiceV2.REQUIRED_MONITORS),
        "alerts": sorted(Phase19ProductionLiveReleaseServiceV2.REQUIRED_ALERTS),
        "ci_green": True,
        "dependency_audit_green": True,
        "security_scan_green": True,
        "backup_restore_validated": True,
        "rollback_validated": True,
        "incident_response_ready": True,
        "incident_commander": "operator-1",
        "max_order_notional_usd": 10.0,
        "max_daily_notional_usd": 50.0,
        "max_daily_loss_usd": 10.0,
        "max_drawdown_pct": 2.0,
        "max_open_orders": 1,
        "global_kill_switch_ready": True,
        "automatic_halt_ready": True,
        "manual_override_ready": True,
        "post_order_reconciliation_required": True,
        "post_order_report_required": True,
        "post_order_signoff_required": True,
        "pending_reconciliation_count": 0,
        "unsigned_report_count": 0,
        "active_halt_count": 0,
        "stale_worker_count": 0,
        "open_order_count": 0,
        "production_release_approval_recorded": True,
        "release_approver": "operator-1",
    }
    config.update(overrides)
    return config


def names(result):
    return {item["name"] for item in result["blockers"]}


def test_phase19_policy_is_final_gate_without_submission():
    policy = Phase19ProductionLiveReleaseServiceV2.policy()

    assert policy["release_scope"] == "controlled_production_live_release_decision"
    assert policy["live_order_submission_by_this_service"] == "not_allowed"
    assert "production_live" in policy["required_release_modes"]
    assert "production_live_release_runbook" in policy["required_runbooks"]


def test_phase19_valid_config_is_release_ready_without_submission():
    result = Phase19ProductionLiveReleaseServiceV2.evaluate_release(valid_config())

    assert result["status"] == "production_release_ready"
    assert result["ready_for_production_live_release"] is True
    assert result["live_order_submission_by_this_service"] is False
    assert result["blockers"] == []


def test_phase19_blocks_missing_phase_prerequisites():
    result = Phase19ProductionLiveReleaseServiceV2.evaluate_release(
        valid_config(
            phase15_controlled_manual_live_ready=False,
            phase17_shadow_review_passed=False,
            phase18_canary_review_passed=False,
            phase14_operations_ready=False,
        )
    )

    assert "phase_prerequisites_complete" in names(result)


def test_phase19_blocks_missing_modes_runbooks_monitors_and_alerts():
    result = Phase19ProductionLiveReleaseServiceV2.evaluate_release(
        valid_config(release_modes=[], runbooks=[], monitors=[], alerts=[])
    )

    blockers = names(result)
    assert "release_modes_are_separately_gated" in blockers
    assert "runbooks_complete" in blockers
    assert "monitoring_complete" in blockers
    assert "alerting_complete" in blockers


def test_phase19_blocks_ci_backup_rollback_and_incident_failures():
    result = Phase19ProductionLiveReleaseServiceV2.evaluate_release(
        valid_config(
            ci_green=False,
            dependency_audit_green=False,
            security_scan_green=False,
            backup_restore_validated=False,
            rollback_validated=False,
            incident_response_ready=False,
            incident_commander="",
        )
    )

    blockers = names(result)
    assert "ci_and_supply_chain_checks_green" in blockers
    assert "backup_restore_and_rollback_validated" in blockers
    assert "incident_response_ready" in blockers


def test_phase19_blocks_risk_halt_and_post_order_control_failures():
    result = Phase19ProductionLiveReleaseServiceV2.evaluate_release(
        valid_config(
            max_order_notional_usd=25,
            max_daily_notional_usd=100,
            max_daily_loss_usd=25,
            max_drawdown_pct=10,
            max_open_orders=5,
            global_kill_switch_ready=False,
            automatic_halt_ready=False,
            manual_override_ready=False,
            post_order_reconciliation_required=False,
            post_order_report_required=False,
            post_order_signoff_required=False,
        )
    )

    blockers = names(result)
    assert "risk_limits_locked" in blockers
    assert "kill_switch_and_halt_controls_ready" in blockers
    assert "post_order_controls_locked" in blockers


def test_phase19_blocks_unresolved_live_state_and_missing_approval():
    result = Phase19ProductionLiveReleaseServiceV2.evaluate_release(
        valid_config(
            pending_reconciliation_count=1,
            unsigned_report_count=1,
            active_halt_count=1,
            stale_worker_count=1,
            open_order_count=2,
            production_release_approval_recorded=False,
            release_approver="",
        )
    )

    blockers = names(result)
    assert "no_unresolved_live_state" in blockers
    assert "production_release_approval_recorded" in blockers
