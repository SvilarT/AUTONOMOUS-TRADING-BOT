import pytest

from services.execution_control_v2 import ExecutionControlV2
from services.execution_service_v2 import ExecutionServiceV2
from services.risk_guard_v2 import RiskGuardV2
from services.trading_mode_v2 import TradingModeError, TradingModeService


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def to_list(self, limit):
        return self.docs[:limit]


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def find_one(self, query, projection=None, sort=None):
        matches = [doc for doc in self.docs if all(doc.get(k) == v for k, v in query.items())]
        return dict(matches[0]) if matches else None

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, query, update, upsert=False):
        doc = None
        for existing in self.docs:
            if all(existing.get(k) == v for k, v in query.items()):
                doc = existing
                break
        if doc is None:
            if not upsert:
                return
            doc = dict(query)
            self.docs.append(doc)
        for key, value in update.get("$set", {}).items():
            doc[key] = value
        for key, value in update.get("$inc", {}).items():
            doc[key] = doc.get(key, 0) + value

    async def delete_one(self, query):
        self.docs = [doc for doc in self.docs if not all(doc.get(k) == v for k, v in query.items())]

    def find(self, query, projection=None):
        matches = [dict(doc) for doc in self.docs if all(doc.get(k) == v for k, v in query.items())]
        return FakeCursor(matches)


class FakeDB:
    def __init__(self):
        self.execution_locks = FakeCollection()
        self.trades_v2 = FakeCollection()


def test_risk_guard_enforces_capital_floor_and_position_limits():
    guard = RiskGuardV2(max_position_notional=100, max_total_exposure_pct=0.30, capital_floor_pct=0.97)
    metrics = guard.portfolio_metrics(
        {"cash_balance": 9600.0, "equity_high": 10000.0, "daily_start_equity": 10000.0},
        [],
        {},
    )

    kill = guard.should_kill_switch(metrics)
    assert kill["triggered"] is True
    assert "capital floor" in kill["reason"]

    good_metrics = guard.portfolio_metrics(
        {"cash_balance": 10000.0, "equity_high": 10000.0, "daily_start_equity": 10000.0},
        [],
        {},
    )
    blocked = guard.can_open_position(good_metrics, [], 150.0)
    assert blocked["allowed"] is False
    assert "notional" in blocked["reason"]


def test_trading_modes_are_explicit_and_gate_execution():
    paper = TradingModeService("paper")
    paper.assert_can_trade()
    assert paper.describe()["mode"] == "paper"
    assert paper.describe()["orders_allowed"] is True

    readonly = TradingModeService("live-readonly")
    with pytest.raises(TradingModeError):
        readonly.assert_can_trade()
    assert readonly.describe()["orders_allowed"] is False

    live = TradingModeService("live-trading")
    with pytest.raises(TradingModeError):
        live.assert_can_trade()

    with pytest.raises(TradingModeError):
        TradingModeService("bad-mode")


@pytest.mark.asyncio
async def test_execution_control_locks_and_idempotency():
    db = FakeDB()
    control = ExecutionControlV2(db, lock_ttl_seconds=60)

    first = await control.acquire_lock("user-1", "BTC-USD", "BUY")
    assert first["acquired"] is True

    second = await control.acquire_lock("user-1", "BTC-USD", "BUY")
    assert second["acquired"] is False

    await control.release_lock(first["key"])
    third = await control.acquire_lock("user-1", "BTC-USD", "BUY")
    assert third["acquired"] is True

    key = control.build_idempotency_key("user-1", "BTC-USD", "BUY", {"selected": {"strategy": "test"}})
    assert await control.already_executed(key) is False
    await db.trades_v2.insert_one({"idempotency_key": key, "status": "filled"})
    assert await control.already_executed(key) is True


@pytest.mark.asyncio
async def test_execution_service_uses_stable_client_order_id_for_idempotency_key():
    service = ExecutionServiceV2()
    first = await service.buy("BTC-USD", 10.0, idempotency_key="same-key")
    second = await service.buy("BTC-USD", 10.0, idempotency_key="same-key")
    assert first["client_order_id"] == second["client_order_id"]
    assert first["idempotency_key"] == "same-key"
