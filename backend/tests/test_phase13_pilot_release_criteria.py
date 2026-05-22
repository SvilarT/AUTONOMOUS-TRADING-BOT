from services.phase13_pilot_release_service_v2 import Phase13PilotReleaseServiceV2


def evidence_for_approved_pilot():
    return {
        "reports": [
            {
                "user_id": "user-1",
                "live_order_id": "order-1",
                "status": "complete",
                "report_hash": "report-hash-1",
            }
        ],
        "signoffs": [
            {
                "user_id": "user-1",
                "live_order_id": "order-1",
                "decision": "approved_for_next_tiny_pilot",
                "signoff_hash": "signoff-hash-1",
            }
        ],
        "requirements": [
            {
                "user_id": "user-1",
                "live_order_id": "order-1",
                "status": "resolved",
            }
        ],
    }


def names(result):
    return {item["name"] for item in result["blockers"]}


def test_phase13_policy_blocks_autonomous_live_trading():
    policy = Phase13PilotReleaseServiceV2.policy()

    assert policy["release_scope"] == "limited_repeated_manual_live_only"
    assert policy["autonomous_live_trading"] == "not_allowed"
    assert policy["max_release_notional_usd"] == 10.0
    assert policy["allowed_symbols"] == ["BTC-USD", "ETH-USD"]


def test_phase13_approved_evidence_allows_limited_manual_release():
    result = Phase13PilotReleaseServiceV2.evaluate_evidence(
        evidence=evidence_for_approved_pilot(),
        requested_max_notional_usd=10.0,
        requested_symbols=["BTC-USD", "ETH-USD"],
    )

    assert result["status"] == "approved_for_limited_manual_live"
    assert result["approved_for_limited_manual_live"] is True
    assert result["blockers"] == []
    assert result["reviewed_orders"] == ["order-1"]


def test_phase13_blocks_when_no_reviewed_pilot_exists():
    result = Phase13PilotReleaseServiceV2.evaluate_evidence(evidence={"reports": [], "signoffs": [], "requirements": []})

    assert result["approved_for_limited_manual_live"] is False
    assert "minimum_reviewed_pilots_met" in names(result)


def test_phase13_blocks_pending_reconciliation():
    evidence = evidence_for_approved_pilot()
    evidence["requirements"][0]["status"] = "pending"

    result = Phase13PilotReleaseServiceV2.evaluate_evidence(evidence=evidence)

    assert "minimum_reviewed_pilots_met" in names(result)
    assert "no_pending_reconciliation" in names(result)


def test_phase13_blocks_unsigned_complete_report():
    evidence = evidence_for_approved_pilot()
    evidence["signoffs"] = []

    result = Phase13PilotReleaseServiceV2.evaluate_evidence(evidence=evidence)

    assert "minimum_reviewed_pilots_met" in names(result)
    assert "no_unsigned_complete_reports" in names(result)


def test_phase13_blocks_hold_reject_or_investigation_signoff():
    evidence = evidence_for_approved_pilot()
    evidence["signoffs"][0]["decision"] = "manual_investigation_required"

    result = Phase13PilotReleaseServiceV2.evaluate_evidence(evidence=evidence)

    assert "minimum_reviewed_pilots_met" in names(result)
    assert "no_blocking_operator_signoff" in names(result)


def test_phase13_blocks_large_release_notional():
    result = Phase13PilotReleaseServiceV2.evaluate_evidence(
        evidence=evidence_for_approved_pilot(),
        requested_max_notional_usd=100.0,
    )

    assert "requested_release_notional_remains_limited" in names(result)


def test_phase13_blocks_non_allowlisted_symbols():
    result = Phase13PilotReleaseServiceV2.evaluate_evidence(
        evidence=evidence_for_approved_pilot(),
        requested_symbols=["BTC-USD", "DOGE-USD"],
    )

    assert "requested_symbols_are_allowlisted" in names(result)
