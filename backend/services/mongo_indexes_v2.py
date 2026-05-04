from typing import Any, Dict, List


class MongoIndexServiceV2:
    """Creates operational indexes for core trading collections."""

    def __init__(self, db):
        self.db = db

    async def ensure_indexes(self) -> Dict[str, Any]:
        created: List[str] = []

        async def create(collection, keys, **kwargs):
            name = await collection.create_index(keys, **kwargs)
            created.append(name)

        await create(self.db.market_candles, [("symbol", 1), ("exchange", 1), ("timeframe", 1), ("open_time", 1)], unique=True, name="uniq_market_candle")
        await create(self.db.trades_v2, [("user_id", 1), ("created_at", -1)], name="trades_user_created")
        await create(self.db.trades_v2, [("client_order_id", 1)], sparse=True, name="trades_client_order_id")
        await create(self.db.positions_v2, [("user_id", 1), ("symbol", 1)], unique=True, name="uniq_position_user_symbol")
        await create(self.db.portfolio_state, [("user_id", 1)], unique=True, name="uniq_portfolio_state_user")
        await create(self.db.ledger_entries, [("user_id", 1), ("created_at", -1)], name="ledger_user_created")
        await create(self.db.ledger_entries, [("entry_id", 1)], unique=True, name="uniq_ledger_entry")
        await create(self.db.reconciliation_reports, [("user_id", 1), ("checked_at", -1)], name="reconciliation_user_checked")
        await create(self.db.live_readonly_reports, [("user_id", 1), ("snapshot.timestamp", -1)], name="live_readonly_user_timestamp")
        await create(self.db.live_order_audits, [("user_id", 1), ("created_at", -1)], name="live_audits_user_created")
        await create(self.db.live_order_audits, [("audit_hash", 1)], unique=True, sparse=True, name="uniq_live_audit_hash")
        await create(self.db.live_order_audits, [("user_id", 1), ("previous_hash", 1)], name="live_audits_user_previous_hash")
        await create(self.db.execution_locks, [("key", 1)], unique=True, name="uniq_execution_lock")
        await create(self.db.execution_locks, [("expires_at", 1)], name="execution_lock_expiry")
        await create(self.db.alerts, [("user_id", 1), ("created_at", -1)], name="alerts_user_created")

        return {"status": "ok", "created_or_verified": created}
