from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid


class PortfolioServiceV2:
    """Ledger-based portfolio/accounting primitives."""

    def __init__(self, db):
        self.db = db

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def ensure_account_state(self, user_id: str, starting_cash: float = 10000.0):
        state = await self.db.portfolio_state.find_one({"user_id": user_id}, {"_id": 0})
        if state:
            return state

        state = {
            "user_id": user_id,
            "cash_balance": starting_cash,
            "realized_pnl": 0.0,
            "updated_at": self.utc_now(),
        }
        await self.db.portfolio_state.insert_one(state)
        return state

    async def record_buy_fill(self, user_id: str, symbol: str, filled_price: float, base_units: float, notional_usd: float):
        await self.ensure_account_state(user_id)

        await self.db.positions_v2.update_one(
            {"user_id": user_id, "symbol": symbol},
            {
                "$inc": {
                    "base_units": base_units,
                    "notional_usd": notional_usd
                },
                "$set": {
                    "avg_price": filled_price,
                    "updated_at": self.utc_now()
                }
            },
            upsert=True
        )

        await self.db.portfolio_state.update_one(
            {"user_id": user_id},
            {"$inc": {"cash_balance": -notional_usd}}
        )

    async def record_sell_fill(self, user_id: str, symbol: str, filled_price: float, base_units: float):
        position = await self.db.positions_v2.find_one({"user_id": user_id, "symbol": symbol})
        if not position:
            return

        proceeds = base_units * filled_price

        await self.db.positions_v2.update_one(
            {"user_id": user_id, "symbol": symbol},
            {"$inc": {"base_units": -base_units}}
        )

        await self.db.portfolio_state.update_one(
            {"user_id": user_id},
            {"$inc": {"cash_balance": proceeds}}
        )
