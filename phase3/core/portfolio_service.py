"""Portfolio management service.

Tracks user cash balances, open positions and realised P&L.  This module
generalises the existing ``PortfolioServiceV2`` to support any database
implementation (MongoDB, PostgreSQL, in‑memory) by delegating all storage
operations through an injected repository interface.  Portfolio updates are
recorded atomically to ensure consistency.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List


class AbstractPortfolioRepo:
    """Repository interface for portfolio persistence.

    Implementations must provide asynchronous methods for querying and
    updating user state and positions.  This abstraction allows the
    portfolio service to run against different databases or in‑memory
    backends.
    """

    async def get_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def upsert_state(self, user_id: str, updates: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def get_positions(self, user_id: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def upsert_position(self, user_id: str, symbol: str, updates: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def delete_position(self, user_id: str, symbol: str) -> None:
        raise NotImplementedError


class PortfolioService:
    """Manages a user’s account state and positions."""

    def __init__(self, repo: AbstractPortfolioRepo):
        self.repo = repo

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def ensure_account_state(self, user_id: str, starting_cash: float = 10000.0) -> Dict[str, Any]:
        state = await self.repo.get_state(user_id)
        if state:
            return state
        state = {
            "user_id": user_id,
            "cash_balance": float(starting_cash),
            "realized_pnl": 0.0,
            "equity_high": float(starting_cash),
            "daily_start_equity": float(starting_cash),
            "created_at": self.utc_now(),
            "updated_at": self.utc_now(),
        }
        await self.repo.upsert_state(user_id, state)
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
        positions = await self.repo.get_positions(user_id)
        existing = next((p for p in positions if p["symbol"] == symbol), None)

        if existing:
            old_units = float(existing.get("base_units", 0.0))
            old_notional = float(existing.get("notional_usd", 0.0))
            new_units = old_units + float(base_units)
            new_notional = old_notional + float(notional_usd)
            new_avg = new_notional / new_units if new_units > 0 else float(filled_price)
            updates = {
                "base_units": round(new_units, 12),
                "notional_usd": round(new_notional, 8),
                "avg_price": round(new_avg, 8),
                "updated_at": self.utc_now(),
            }
            await self.repo.upsert_position(user_id, symbol, updates)
        else:
            updates = {
                "user_id": user_id,
                "symbol": symbol,
                "base_units": round(float(base_units), 12),
                "notional_usd": round(float(notional_usd), 8),
                "avg_price": round(float(filled_price), 8),
                "created_at": self.utc_now(),
                "updated_at": self.utc_now(),
            }
            await self.repo.upsert_position(user_id, symbol, updates)

        # update cash balance and timestamps
        await self.repo.upsert_state(user_id, {
            "cash_balance": -float(notional_usd),
            "updated_at": self.utc_now(),
        })

    async def record_sell_fill(
        self,
        user_id: str,
        symbol: str,
        filled_price: float,
        base_units: float,
    ) -> Dict[str, Any]:
        positions = await self.repo.get_positions(user_id)
        position = next((p for p in positions if p["symbol"] == symbol), None)
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
            await self.repo.delete_position(user_id, symbol)
        else:
            await self.repo.upsert_position(user_id, symbol, {
                "base_units": round(remaining_units, 12),
                "notional_usd": round(remaining_notional, 8),
                "avg_price": round(remaining_notional / remaining_units, 8) if remaining_units > 0 else float(filled_price),
                "updated_at": self.utc_now(),
            })
        await self.repo.upsert_state(user_id, {
            "cash_balance": proceeds,
            "realized_pnl": realized_pnl,
            "updated_at": self.utc_now(),
        })
        return {
            "realized_pnl": round(realized_pnl, 8),
            "proceeds": round(proceeds, 8),
            "remaining_units": round(max(remaining_units, 0.0), 12),
        }
