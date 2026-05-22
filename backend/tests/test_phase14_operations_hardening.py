from services.phase14_operations_hardening_service_v2 import Phase14OperationsHardeningServiceV2


def complete_config(**overrides):
    config = {
        "runbooks": sorted(Phase14OperationsHardeningServiceV2.REQUIRED_RUNBOOKS),
        "monitors": sorted(Phase14OperationsHardeningServiceV2.REQUIRED_MONITORS),
        "alert_channels": sorted(Phase14OperationsHardeningServiceV2.REQUIRED_ALERT_CHANNELS),
        "database_backup_enabled": True,
        "database_restore_drill_recorded": True,
        "log_redaction_enabled": True,
        "error_tracking_configured": True,
        "rate_limiting_enabled": True,
        "production_cors_explicit": True,
        "pending_reconciliation_count": 0,
        "unsigned_completed_report_count": 0,
        "active_halt_count": 0,
        "stale_worker_count": 0,
        "incident_commander": "operator-1",
    }
    config.update(overrides)
    return config


def names(result):
    return {item["name"] for item in result["blockers"]}


def warning_names(result):
    return {item["name"] for item in result["warnings"]}


def test_phase14_policy_keeps_autonomous_live_disallowed():
    policy = Phase14OperationsHardeningServiceV2.policy()

    assert policy["release_scope"] == "operations_ready_for_controlled_manual_live"
    assert policy["autonomous_live_trading"] == "not_allowed"
    assert "deployment_runbook" in policy["required_runbooks"]
    assert "unresolved_reconciliation" in policy["required_monitors"]


def test_phase14_complete_config_is_operations_ready():
    result = Phase14OperationsHardeningServiceV2.evaluate_config(complete_config())

    assert result["status"] == "operations_ready"
    assert result["ready_for_controlled_manual_live"] is True
    assert result["blockers"] == []


def test_phase14_missing_runbooks_block_readiness():
    result = Phase14OperationsHardeningServiceV2.evaluate_config(complete_config(runbooks=[]))

    assert result["ready_for_controlled_manual_live"] is False
    assert "deployment_runbooks_complete" in names(result)


def test_phase14_missing_monitoring_blocks_readiness():
    result = Phase14OperationsHardeningServiceV2.evaluate_config(complete_config(monitors=[]))

    assert "monitoring_coverage_complete" in names(result)


def test_phase14_missing_alert_channels_block_readiness():
    result = Phase14OperationsHardeningServiceV2.evaluate_config(complete_config(alert_channels=[]))

    assert "critical_alert_channels_configured" in names(result)


def test_phase14_backup_restore_and_log_controls_are_required():
    result = Phase14OperationsHardeningServiceV2.evaluate_config(
        complete_config(
            database_backup_enabled=False,
            database_restore_drill_recorded=False,
            log_redaction_enabled=False,
        )
    )

    blockers = names(result)
    assert "database_backup_enabled" in blockers
    assert "database_restore_drill_recorded" in blockers
    assert "log_redaction_enabled" in blockers


def test_phase14_unresolved_live_state_blocks_readiness():
    result = Phase14OperationsHardeningServiceV2.evaluate_config(
        complete_config(
            pending_reconciliation_count=1,
            unsigned_completed_report_count=1,
            active_halt_count=1,
        )
    )

    assert "no_unresolved_live_state" in names(result)


def test_phase14_stale_workers_block_readiness():
    result = Phase14OperationsHardeningServiceV2.evaluate_config(complete_config(stale_worker_count=1))

    assert "workers_not_stale" in names(result)


def test_phase14_error_tracking_and_incident_owner_are_warnings():
    result = Phase14OperationsHardeningServiceV2.evaluate_config(
        complete_config(error_tracking_configured=False, incident_commander="")
    )

    assert result["ready_for_controlled_manual_live"] is True
    assert "error_tracking_configured" in warning_names(result)
    assert "incident_commander_assigned" in warning_names(result)
