from services.phase11_dry_run_rehearsal_service_v2 import Phase11DryRunRehearsalServiceV2


def valid_readiness():
    return {"ready": True, "status": "ready", "blockers": []}


def valid_dry_run_order():
    return {
        "success": True,
        "status": "dry_run",
        "live_order_id": "live-dry-run-1",
        "gate": {"allowed": True, "dry_run": True},
        "risk_decision": {"decision": "allow"},
        "audit": {"audit_hash": "audit-hash-1"},
        "reconciliation_requirement": {"required": False, "status": "not_required"},
        "order": {"status": "dry_run", "live_execution": False},
    }


def valid_report():
    return {"status": "complete", "report_hash": "report-hash-1"}


def valid_expansion_status():
    return {"allowed_to_repeat_pilot": True, "blockers": []}


def test_phase11_plan_contains_required_rehearsal_steps():
    plan = Phase11DryRunRehearsalServiceV2.plan()
    names = {step["name"] for step in plan["steps"]}

    assert plan["live_order_submission"] == "disabled_by_design"
    assert "secret_hardening_check" in names
    assert "live_readonly_reconciliation" in names
    assert "exact_manual_order_dry_run" in names
    assert "operator_signoff" in names


def test_phase11_valid_artifacts_pass_rehearsal_validation():
    result = Phase11DryRunRehearsalServiceV2.validate_artifacts(
        readiness=valid_readiness(),
        dry_run_order=valid_dry_run_order(),
        report=valid_report(),
        expansion_status=valid_expansion_status(),
    )

    assert result["status"] == "passed"
    assert result["ready_for_tiny_manual_live_pilot"] is True
    assert result["blockers"] == []


def test_phase11_blocks_missing_dry_run_metadata():
    order = valid_dry_run_order()
    order.pop("risk_decision")

    result = Phase11DryRunRehearsalServiceV2.validate_artifacts(
        readiness=valid_readiness(),
        dry_run_order=order,
        report=valid_report(),
        expansion_status=valid_expansion_status(),
    )

    assert result["status"] == "failed"
    names = {blocker["name"] for blocker in result["blockers"]}
    assert "dry_run_contains_required_metadata" in names
    assert "dry_run_risk_allows_order" in names


def test_phase11_blocks_any_live_execution_signal():
    order = valid_dry_run_order()
    order["order"]["live_execution"] = True

    result = Phase11DryRunRehearsalServiceV2.validate_artifacts(
        readiness=valid_readiness(),
        dry_run_order=order,
        report=valid_report(),
        expansion_status=valid_expansion_status(),
    )

    names = {blocker["name"] for blocker in result["blockers"]}
    assert "dry_run_does_not_report_live_execution" in names


def test_phase11_blocks_readiness_blockers():
    result = Phase11DryRunRehearsalServiceV2.validate_artifacts(
        readiness={"ready": False, "status": "not_ready", "blockers": [{"name": "example"}]},
        dry_run_order=valid_dry_run_order(),
        report=valid_report(),
        expansion_status=valid_expansion_status(),
    )

    names = {blocker["name"] for blocker in result["blockers"]}
    assert "pilot_readiness_ready" in names
    assert "pilot_readiness_has_no_blockers" in names


def test_phase11_blocks_uncleared_expansion_status():
    result = Phase11DryRunRehearsalServiceV2.validate_artifacts(
        readiness=valid_readiness(),
        dry_run_order=valid_dry_run_order(),
        report=valid_report(),
        expansion_status={"allowed_to_repeat_pilot": False, "blockers": [{"name": "unsigned"}]},
    )

    names = {blocker["name"] for blocker in result["blockers"]}
    assert "expansion_status_clear_after_signoff" in names
