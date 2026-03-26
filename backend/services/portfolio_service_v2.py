from datetime import datetime, timezone
from typing import Dict, Any


class PortfolioServiceV2:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def ensure_account_state(self, user_id: str, starting_cash: float = 10000.0) -> Dict[str, Any]:
        state = await self.db.portfolio_state.find_one({"user_id": user_id}, {"_id": 0})
        if state:
            return state

        state = {
            "user_id": user_id,
            "cash_balance": float(starting_cash),
            "realized_pnl": 0.0,
            "updated_at": self.utc_now(),
        }
        await self.db.portfolio_state.insert_one(state)
        return state

    async def record_buy_fill(
        self,
        user_id: str,
        symbol: str,
        filled_price: float,
        base_units: float,
        notional_usd: float,
    ) -> None:
        await self.ensure_account_state(user_id)

        existing = await self.db.positions_v2.find_one({"user_id": user_id, "symbol": symbol}, {"_id": 0})

        if existing:
            old_units = float(existing.get("base_units", 0.0))
            old_notional = float(existing.get("notional_usd", 0.0))
            new_units = old_units + float(base_units)
            new_notional = old_notional + float(notional_usd)
            new_avg = new_notional / new_units if new_units > 0 else float(filled_price)

            await self.db.positions_v2.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {
                    "base_units": round(new_units, 12),
                    "notional_usd": round(new_notional, 8),
                    "avg_price": round(new_avg, 8),
                    "updated_at": self.utc_now(),
                }},
            )
        else:
            await self.db.positions_v2.insert_one({
                "user_id": user_id,
                "symbol": symbol,
                "base_units": round(float(base_units), 12),
                "notional_usd": round(float(notional_usd), 8),
                "avg_price": round(float(filled_price), 8),
                "created_at": self.utc_now(),
                "updated_at": self.utc_now(),
            })

        await self.db.portfolio_state.update_one(
            {"user_id": user_id},
            {"$inc": {"cash_balance": -float(notional_usd)}, "$set": {"updated_at": self.utc_now()}},
            upsert=True,
        )

    async def record_sell_fill(
        self,
        user_id: str,
        symbol: str,
        filled_price: float,
        base_units: float,
    ) -> Dict[str, Any]:
        position = await self.db.positions_v2.find_one({"user_id": user_id, "symbol": symbol})
        if not position:
            return {"realized_pnl": 0.0}

        current_units = float(position.get("base_units", 0.0))
        current_notional = float(position.get("notional_usd", 0.0))
        if current_units <= 0:
            return {"realized_pnl": 0.0}

        sell_units = min(float(base_units), current_units)
        cost_basis_per_unit = current_notional / current_units
        sold_cost_basis = sell_units * cost_basis_per_unit
        proceeds = sell_units * float(filled_price)
        realized_pnl = proceeds - sold_cost_basis

        remaining_units = current_units - sell_units
        remaining_notional = max(0.0, current_notional - sold_cost_basis)

        if remaining_units <= 1e-12:
            await self.db.positions_v2.delete_one({"user_id": user_id, "symbol": symbol})
        else:
            await self.db.positions_v2.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {
                    "base_units": round(remaining_units, 12),
                    "notional_usd": round(remaining_notional, 8),
                    "avg_price": round(remaining_notional / remaining_units, 8),
                    "updated_at": self.utc_now(),
                }},
            )

        await self.db.portfolio_state.update_one(
            {"user_id": user_id},
            {"$inc": {"cash_balance": proceeds, "realized_pnl": realized_pnl}, "$set": {"updated_at": self.utc_now()}},
            upsert=True,
        )

        return {
            "realized_pnl": round(realized_pnl, 8),
            "proceeds": round(proceeds, 8),
            "remaining_units": round(max(remaining_units, 0.0), 12),
            }
