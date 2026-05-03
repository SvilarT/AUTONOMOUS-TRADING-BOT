import base64
import hashlib
import hmac

import pytest

from services.coinbase_readonly_adapter_v2 import CoinbaseReadonlyAdapterV2, CoinbaseReadonlyError
from services.live_readonly_service_v2 import LiveReadonlyServiceV2
from services.trading_mode_v2 import TradingModeService, TradingModeError


class FakeCursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction=1):
        reverse = direction == -1
        self.docs = sorted(self.docs, key=lambda doc: doc.get(key, ""), reverse=reverse)
        return self

    def limit(self, limit):
        self.docs = self.docs[:limit]
        return self

    async def to_list(self, limit):
        return self.docs[:limit]


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def find_one(self, query, projection=None, sort=None):
        matches = [doc for doc in self.docs if all(doc.get(k) == v for k, v in query.items())]
        if sort and matches:
            key, direction = sort[0]
            matches = sorted(matches, key=lambda doc: doc.get(key, ""), reverse=direction == -1)
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

    async def count_documents(self, query):
        return len([doc for doc in self.docs if all(doc.get(k) == v for k, v in query.items())])


class FakeDB:
    def __init__(self):
        self.alerts = FakeCollection()
        self.live_readonly_reports = FakeCollection()
        self.ledger_entries = FakeCollection()
        self.positions_v2 = FakeCollection()
        self.portfolio_state = FakeCollection()
        self.reconciliation_reports = FakeCollection()
        self.trades_v2 = FakeCollection()
        self.risk_metrics = FakeCollection()
        self.bot_configs = FakeCollection()


class FakeReadonlyAdapter:
    credentials_configured = True

    async def snapshot(self, symbols=None):
        return {
            "mode": "live-readonly",
            "orders_allowed": False,
            "live_execution_enabled": False,
            "credentials_configured": True,
            "accounts": [
                {"currency": "BTC", "balance": 1.0, "available": 1.0, "hold": 0.0},
                {"currency": "USD", "balance": 100.0, "available": 100.0, "hold": 0.0},
            ],
            "tickers": {"BTC-USD": {"price": 100.0}},
            "timestamp": "2026-01-01T00:00:00+00:00",
        }

    async def get_orders(self, status="all", limit=100):
        return [{"id": "order-1", "status": status, "product_id": "BTC-USD"}]

    async def get_fills(self, product_id=None, limit=100):
        return [{"order_id": "order-1", "product_id": product_id or "BTC-USD", "size": 1.0}]


class FailingReadonlyAdapter(FakeReadonlyAdapter):
    async def snapshot(self, symbols=None):
        raise CoinbaseReadonlyError("readonly failure")


def test_coinbase_readonly_adapter_credentials_detection_and_signing():
    secret = base64.b64encode(b"secret-bytes").decode("utf-8")
    adapter = CoinbaseReadonlyAdapterV2(api_key="key", api_secret=secret, passphrase="pass")
    timestamp = "1700000000.0"
    signature = adapter._signature(timestamp, "GET", "/accounts")
    expected = base64.b64encode(hmac.new(b"secret-bytes", b"1700000000.0GET/accounts", hashlib.sha256).digest()).decode("utf-8")

    assert adapter.credentials_configured is True
    assert signature == expected


def test_coinbase_readonly_adapter_rejects_order_methods():
    adapter = CoinbaseReadonlyAdapterV2(api_key="key", api_secret="secret", passphrase="pass")

    with pytest.raises(CoinbaseReadonlyError):
        import asyncio
        asyncio.run(adapter.place_market_buy("BTC-USD", 10.0))

    with pytest.raises(CoinbaseReadonlyError):
        import asyncio
        asyncio.run(adapter.place_market_sell("BTC-USD", 0.1))


def test_coinbase_readonly_adapter_requires_credentials_for_private_headers():
    adapter = CoinbaseReadonlyAdapterV2(api_key=None, api_secret=None, passphrase=None)
    assert adapter.credentials_configured is False
    with pytest.raises(CoinbaseReadonlyError):
        adapter._headers("GET", "/accounts")


def test_trading_mode_metadata_for_live_readonly_blocks_orders():
    mode = TradingModeService("live-readonly")
    description = mode.describe()

    assert description["mode"] == "live-readonly"
    assert description["orders_allowed"] is False
    assert description["live_readonly_enabled"] is True
    assert description["live_account_reads_allowed"] is True
    assert description["live_execution_enabled"] is False
    with pytest.raises(TradingModeError):
        mode.assert_can_trade()


@pytest.mark.asyncio
async def test_live_readonly_snapshot_includes_internal_positions_and_ledger_rebuild():
    db = FakeDB()
    await db.positions_v2.insert_one({"user_id": "user-1", "symbol": "BTC-USD", "base_units": 1.0, "notional_usd": 100.0})
    service = LiveReadonlyServiceV2(db, adapter=FakeReadonlyAdapter())

    snapshot = await service.snapshot("user-1", symbols=["BTC-USD"])

    assert snapshot["mode"] == "live-readonly"
    assert snapshot["orders_allowed"] is False
    assert snapshot["internal_positions"][0]["symbol"] == "BTC-USD"
    assert snapshot["ledger_rebuild"]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_live_readonly_reconcile_reports_ok_when_units_match():
    db = FakeDB()
    await db.positions_v2.insert_one({"user_id": "user-1", "symbol": "BTC-USD", "base_units": 1.0, "notional_usd": 100.0})
    service = LiveReadonlyServiceV2(db, adapter=FakeReadonlyAdapter())

    report = await service.compare_exchange_to_internal("user-1", symbols=["BTC-USD"])

    assert report["status"] == "ok"
    assert report["issues"] == []
    assert len(db.live_readonly_reports.docs) == 1
    assert len(db.alerts.docs) == 0


@pytest.mark.asyncio
async def test_live_readonly_reconcile_detects_drift_and_alerts():
    db = FakeDB()
    await db.positions_v2.insert_one({"user_id": "user-1", "symbol": "BTC-USD", "base_units": 0.25, "notional_usd": 25.0})
    service = LiveReadonlyServiceV2(db, adapter=FakeReadonlyAdapter())

    report = await service.compare_exchange_to_internal("user-1", symbols=["BTC-USD"])

    assert report["status"] == "mismatch"
    assert report["issues"][0]["type"] == "exchange_internal_position_drift"
    assert report["issues"][0]["delta_units"] == 0.75
    assert db.alerts.docs[0]["type"] == "live_readonly_drift_detected"


@pytest.mark.asyncio
async def test_live_readonly_snapshot_failure_emits_alert():
    db = FakeDB()
    service = LiveReadonlyServiceV2(db, adapter=FailingReadonlyAdapter())

    with pytest.raises(CoinbaseReadonlyError):
        await service.snapshot("user-1", symbols=["BTC-USD"])

    assert db.alerts.docs[0]["type"] == "live_readonly_snapshot_failed"


@pytest.mark.asyncio
async def test_live_readonly_orders_and_fills_are_readonly_payloads():
    db = FakeDB()
    service = LiveReadonlyServiceV2(db, adapter=FakeReadonlyAdapter())

    orders = await service.recent_orders("user-1", status="done", limit=5)
    fills = await service.recent_fills("user-1", product_id="BTC-USD", limit=5)

    assert orders["orders_allowed"] is False
    assert orders["orders"][0]["status"] == "done"
    assert fills["orders_allowed"] is False
    assert fills["fills"][0]["product_id"] == "BTC-USD"
