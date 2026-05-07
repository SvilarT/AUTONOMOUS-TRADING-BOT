import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "test-secret-for-live-risk-tests-more-than-32-chars")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest

from app_state import db
from services.live_risk_decision_service_v2 import LiveRiskDecisionServiceV2
from services.live_submit_policy_v2 import LiveSubmitPolicyError, LiveSubmitPolicyV2


async def cleanup(user_id: str):
    await db.live_risk_decisions.delete_many({"user_id": user_id})


@pytest.mark.asyncio
async def test_live_risk_decision_persists_allow_and_block():
    user_id = "risk-user-1"
    service = LiveRiskDecisionServiceV2(db)
    try:
        allowed = await service.allow_basic_manual_order(
            user_id=user_id,
            symbol="BTC-USD",
            side="BUY",
            notional_usd=5,
            max_notional_usd=25,
            allowed_symbols=["BTC-USD", "ETH-USD"],
        )
        blocked = await service.allow_basic_manual_order(
            user_id=user_id,
            symbol="DOGE-USD",
            side="BUY",
            notional_usd=50,
            max_notional_usd=25,
            allowed_symbols=["BTC-USD", "ETH-USD"],
        )

        assert allowed["decision"] == "allow"
        assert blocked["decision"] == "block"
        assert any(not check["passed"] for check in blocked["checks"])
        assert await db.live_risk_decisions.count_documents({"user_id": user_id}) == 2
    finally:
        await cleanup(user_id)


def test_live_submit_policy_blocks_blind_retry_for_non_terminal_state():
    with pytest.raises(LiveSubmitPolicyError):
        LiveSubmitPolicyV2.assert_no_blind_retry(
            previous_attempt={"status": "submitted"},
            client_order_id="client-1",
        )


def test_live_submit_policy_blocks_ambiguous_retry():
    with pytest.raises(LiveSubmitPolicyError):
        LiveSubmitPolicyV2.assert_no_blind_retry(
            previous_attempt={"status": "adapter_error", "ambiguous": True},
            client_order_id="client-1",
        )


def test_live_submit_policy_allows_first_attempt():
    LiveSubmitPolicyV2.assert_no_blind_retry(previous_attempt=None, client_order_id="client-1")
