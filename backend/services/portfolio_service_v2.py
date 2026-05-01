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

        now = self.utc_now()
        state = {
            "user_id": user_id,
            "cash_balance": float(starting_cash),
            "realized_pnl": 0.0,
            "equity_high": float(starting_cash),
            "daily_start_equity": float(starting_cash),
            "updated_at": now,
        }
        await self.db.portfolio_state.insert_one(state)
        return state

    async def record_trade_attempt(self, user_id: str, symbol: str, side: str, order: Dict[str, Any], context: Dict[str, Any] | None = None) -> None:
        now = self.utc_now()
        trade = {
            "user_id": user_id,
            "symbol": symbol,
            "side": side,
            "order_type": "market",
            "status": order.get("status", "unknown"),
            "order_id": order.get("order_id"),
            "client_order_id": order.get("client_order_id"),
            "requested_notional_usd": order.get("requested_notional_usd"),
            "requested_base_units": order.get("requested_base_units"),
            "notional_usd": order.get("notional_usd"),
            "base_units": order.get("base_units"),
            "filled_price": order.get("filled_price"),
            "fee_usd": float(order.get("fee_usd", 0.0) or 0.0),
            "simulation": bool(order.get("simulation", False)),
            "signal_snapshot": order.get("signal_snapshot") or context or {},
            "created_at": now,
            "filled_at": now if order.get("status") == "filled" else None,
        }
        await self.db.trades_v2.insert_one(trade)

        # Mirror minimal fields into the legacy dashboard collection until routes are fully migrated.
        await self.db.trades.insert_one({
            "user_id": user_id,
            "symbol": symbol,
            "side": side,
            "order_type": "market",
            "quantity": float(order.get("base_units", 0.0) or order.get("requested_base_units", 0.0) or 0.0),
            "filled_price": order.get("filled_price"),
            "status": order.get("status", "unknown"),
            "fee_usd": trade["fee_usd"],
            "simulation": trade["simulation"],
            "created_at": now,
            "filled_at": trade["filled_at"],
        })

    async def sync_legacy_position(self, user_id: str, symbol: str) -> None:
        position = await self.db.positions_v2.find_one({"user_id": user_id, "symbol": symbol}, {"_id": 0})
        if not position:
            await self.db.positions.delete_one({"user_id": user_id, "symbol": symbol})
            return

        await self.db.positions.update_one(
            {"user_id": user_id, "symbol": symbol},
            {"$set": {
                "user_id": user_id,
                "symbol": symbol,
                "quantity": float(position.get("base_units", 0.0)),
                "base_units": float(position.get("base_units", 0.0)),
                "notional_usd": float(position.get("notional_usd", 0.0)),
                "avg_price": float(position.get("avg_price", 0.0)),
                "current_price": float(position.get("avg_price", 0.0)),
                "pnl": 0.0,
                "pnl_percent": 0.0,
                "updated_at": self.utc_now(),
                "created_at": position.get("created_at", self.utc_now()),
            }},
            upsert=True,
        )

    async def update_risk_snapshot(self, user_id: str, price_map: Dict[str, float] | None = None) -> Dict[str, Any]:
        state = await self.ensure_account_state(user_id)
        positions = await self.db.positions_v2.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        price_map = price_map or {}

        cash_balance = float(state.get("cash_balance", 0.0))
        positions_value = 0.0
        for position in positions:
            symbol = position.get("symbol")
            mark_price = float(price_map.get(symbol, position.get("avg_price", 0.0)))
            positions_value += float(position.get("base_units", 0.0)) * mark_price

        total_equity = cash_balance + positions_value
        max_equity = max(float(state.get("equity_high", total_equity)), total_equity)
        daily_start_equity = float(state.get("daily_start_equity", max_equity))
        current_drawdown = (max_equity - total_equity) / max_equity if max_equity > 0 else 0.0
        daily_pnl = total_equity - daily_start_equity
        now = self.utc_now()

        snapshot = {
            "user_id": user_id,
            "total_equity": round(total_equity, 8),
            "max_equity": round(max_equity, 8),
            "equity_floor": round(max_equity * 0.97, 8),
            "current_drawdown": round(current_drawdown, 8),
            "daily_pnl": round(daily_pnl, 8),
            "positions_value": round(positions_value, 8),
            "cash_balance": round(cash_balance, 8),
            "timestamp": now,
        }

        await self.db.risk_metrics.insert_one(snapshot.copy())
        await self.db.portfolio_state.update_one(
            {"user_id": user_id},
            {"$set": {"equity_high": max_equity, "updated_at": now}},
            upsert=True,
        )
        return snapshot

    async def record_buy_fill(
        self,
        user_id: str,
        symbol: str,
        filled_price: float,
        base_units: float,
        notional_usd: float,
        fee_usd: float = 0.0,
    ) -> None:
        await self.ensure_account_state(user_id)

        fee_usd = float(fee_usd or 0.0)
        gross_notional = float(notional_usd)
        cost_basis = gross_notional + fee_usd
        existing = await self.db.positions_v2.find_one({"user_id": user_id, "symbol": symbol}, {"_id": 0})

        if existing:
            old_units = float(existing.get("base_units", 0.0))
            old_notional = float(existing.get("notional_usd", 0.0))
            old_fees = float(existing.get("fees_paid_usd", 0.0))
            new_units = old_units + float(base_units)
            new_notional = old_notional + cost_basis
            new_fees = old_fees + fee_usd
            new_avg = new_notional / new_units if new_units > 0 else float(filled_price)

            await self.db.positions_v2.update_one(
                {"user_id": user_id, "symbol": symbol},
                {"$set": {
                    "base_units": round(new_units, 12),
                    "notional_usd": round(new_notional, 8),
                    "avg_price": round(new_avg, 8),
                    "fees_paid_usd": round(new_fees, 8),
                    "updated_at": self.utc_now(),
                }},
            )
        else:
            await self.db.positions_v2.insert_one({
                "user_id": user_id,
                "symbol": symbol,
                "base_units": round(float(base_units), 12),
                "notional_usd": round(cost_basis, 8),
                "avg_price": round(cost_basis / float(base_units), 8) if float(base_units) > 0 else round(float(filled_price), 8),
                "fees_paid_usd": round(fee_usd, 8),
                "created_at": self.utc_now(),
                "updated_at": self.utc_now(),
            })

        await self.db.portfolio_state.update_one(
            {"user_id": user_id},
            {"$inc": {"cash_balance": -cost_basis}, "$set": {"updated_at": self.utc_now()}},
            upsert=True,
        )
        await self.sync_legacy_position(user_id, symbol)

    async def record_sell_fill(
        self,
        user_id: str,
        symbol: str,
        filled_price: float,
        base_units: float,
        fee_usd: float = 0.0,
    ) -> Dict[str, Any]:
        position = await self.db.positions_v2.find_one({"user_id": user_id, "symbol": symbol})
        if not position:
            return {"realized_pnl": 0.0}

        current_units = float(position.get("base_units", 0.0))
        current_notional = float(position.get("notional_usd", 0.0))
        if current_units <= 0:
            return {"realized_pnl": 0.0}

        fee_usd = float(fee_usd or 0.0)
        sell_units = min(float(base_units), current_units)
        cost_basis_per_unit = current_notional / current_units
        sold_cost_basis = sell_units * cost_basis_per_unit
        gross_proceeds = sell_units * float(filled_price)
        net_proceeds = gross_proceeds - fee_usd
        realized_pnl = net_proceeds - sold_cost_basis

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
            {"$inc": {"cash_balance": net_proceeds, "realized_pnl": realized_pnl}, "$set": {"updated_at": self.utc_now()}},
            upsert=True,
        )
        await self.sync_legacy_position(user_id, symbol)

        return {
            "realized_pnl": round(realized_pnl, 8),
            "gross_proceeds": round(gross_proceeds, 8),
            "net_proceeds": round(net_proceeds, 8),
            "fee_usd": round(fee_usd, 8),
            "remaining_units": round(max(remaining_units, 0.0), 12),
        }
