import pytest

from services.coinbase_live_execution_adapter_v2 import CoinbaseLiveExecutionAdapterV2, CoinbaseLiveExecutionError
from services.live_risk_decision_service_v2 import LiveRiskDecisionServiceV2


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(dict(doc))


class FakeDB:
    def __init__(self):
        self.live_risk_decisions = FakeCollection()


def test_coinbase_live_response_normalizes_done_with_fill_as_filled():
    response = CoinbaseLiveExecutionAdapterV2.normalize_order_response(
        {"id": "ex-1", "client_oid": "client-1", "status": "done", "product_id": "BTC-USD", "filled_size": "0.01", "executed_value": "10.50", "fill_fees": "0.05"},
        symbol="BTC-USD",
        side="BUY",
        requested={"client_order_id": "client-1"},
    )

    assert response["success"] is True
    assert response["status"] == "filled"
    assert response["broker_status"] == "done"
    assert response["order_id"] == "ex-1"
    assert response["client_order_id"] == "client-1"
    assert response["live_execution"] is True


def test_coinbase_live_response_normalizes_done_without_fill_as_canceled():
    response = CoinbaseLiveExecutionAdapterV2.normalize_order_response(
        {"id": "ex-2", "status": "done", "filled_size": "0", "executed_value": "0"},
        symbol="BTC-USD",
        side="SELL",
        requested={"client_order_id": "client-2"},
    )

    assert response["success"] is False
    assert response["status"] == "canceled"
    assert response["broker_status"] == "done"


def test_coinbase_live_response_normalizes_open_as_acknowledged():
    response = CoinbaseLiveExecutionAdapterV2.normalize_order_response(
        {"id": "ex-3", "status": "open", "product_id": "ETH-USD"},
        symbol="ETH-USD",
        side="BUY",
        requested={"client_order_id": "client-3"},
    )

    assert response["success"] is True
    assert response["status"] == "acknowledged"
    assert response["broker_status"] == "open"


def test_coinbase_live_response_normalizes_rejected_as_success_false():
    response = CoinbaseLiveExecutionAdapterV2.normalize_order_response(
        {"id": "ex-4", "status": "rejected", "product_id": "BTC-USD"},
        symbol="BTC-USD",
        side="BUY",
        requested={"client_order_id": "client-4"},
    )

    assert response["success"] is False
    assert response["status"] == "rejected"


def test_coinbase_live_kill_switch_remains_final_adapter_guard(monkeypatch):
    monkeypatch.setenv("COINBASE_LIVE_ORDER_KILL_SWITCH", "true")
    with pytest.raises(CoinbaseLiveExecutionError):
        CoinbaseLiveExecutionAdapterV2.assert_live_orders_not_killed()


@pytest.mark.asyncio
async def test_live_risk_decision_blocks_symbol_outside_manual_pilot_allowlist():
    db = FakeDB()
    decision = await LiveRiskDecisionServiceV2(db).allow_basic_manual_order(
        user_id="user-1",
        symbol="DOGE-USD",
        side="BUY",
        notional_usd=5.0,
        max_notional_usd=10.0,
        allowed_symbols=["BTC-USD", "ETH-USD"],
    )

    assert decision["decision"] == "block"
    assert decision["reason"] == "symbol is not allowed for live trading"
    assert len(db.live_risk_decisions.docs) == 1
