"""Example exchange connector that simulates trades.

This connector is intended for testing and offline development.  It
implements the ``AbstractExchangeConnector`` interface but does not
communicate with any real exchange.  It returns deterministic prices and
fills for demonstration purposes.
"""

from __future__ import annotations

import random
from typing import Dict, Any, List

from ..core.execution_router import AbstractExchangeConnector


class MockConnector(AbstractExchangeConnector):
    name = "mock"

    def __init__(self, base_prices: Dict[str, float] | None = None):
        # Use provided base prices or defaults for BTC and ETH
        self.base_prices = base_prices or {"BTC-USD": 45000.0, "ETH-USD": 2500.0}
        self.positions: List[Dict[str, Any]] = []
        self.cash_balance: float = 10000.0

    async def get_balances(self) -> Dict[str, float]:
        return {"USD": self.cash_balance}

    async def get_positions(self) -> List[Dict[str, Any]]:
        return self.positions

    async def buy(self, symbol: str, notional_usd: float, **kwargs) -> Dict[str, Any]:
        base_price = self.base_prices.get(symbol, 1000.0)
        slippage = random.uniform(0.001, 0.003)
        filled_price = base_price * (1 + slippage)
        base_units = notional_usd / filled_price
        self.cash_balance -= notional_usd
        # update position in internal list
        position = next((p for p in self.positions if p["symbol"] == symbol), None)
        if position:
            position["base_units"] += base_units
            position["avg_price"] = ((position["avg_price"] * position["base_units"]) + (filled_price * base_units)) / (position["base_units"] + base_units)
        else:
            self.positions.append({"symbol": symbol, "base_units": base_units, "avg_price": filled_price})
        return {
            "success": True,
            "order_id": f"mock_buy_{random.randint(100000, 999999)}",
            "status": "filled",
            "filled_price": round(filled_price, 8),
            "base_units": round(base_units, 12),
            "notional_usd": round(notional_usd, 8),
        }

    async def sell(self, symbol: str, base_units: float, **kwargs) -> Dict[str, Any]:
        base_price = self.base_prices.get(symbol, 1000.0)
        slippage = random.uniform(0.001, 0.003)
        filled_price = base_price * (1 - slippage)
        notional_usd = base_units * filled_price
        self.cash_balance += notional_usd
        # update position
        position = next((p for p in self.positions if p["symbol"] == symbol), None)
        if position:
            position["base_units"] -= base_units
            if position["base_units"] <= 0:
                self.positions.remove(position)
        return {
            "success": True,
            "order_id": f"mock_sell_{random.randint(100000, 999999)}",
            "status": "filled",
            "filled_price": round(filled_price, 8),
            "base_units": round(base_units, 12),
            "notional_usd": round(notional_usd, 8),
        }

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return {"success": True, "order_id": order_id, "status": "canceled"}
