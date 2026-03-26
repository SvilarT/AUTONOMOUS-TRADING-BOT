"""Mock connector simulating Coinbase exchange behaviour.

This connector simulates Coinbase’s trading environment with slightly higher
fees than Binance.  It inherits from ``AbstractExchangeConnector`` and
implements simple buy/sell operations for testing purposes.
"""

from __future__ import annotations

import random
from typing import Dict, Any, List

from ..core.execution_router import AbstractExchangeConnector


class MockCoinbaseConnector(AbstractExchangeConnector):
    name = "mock_coinbase"
    fee_rate: float = 0.0015  # Higher fee than Binance
    supported_symbols: List[str] | None = None

    def __init__(self, base_prices: Dict[str, float] | None = None):
        self.base_prices = base_prices or {"BTC-USD": 45200.0, "ETH-USD": 2520.0}
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
        fee = notional_usd * self.fee_rate
        base_units = (notional_usd - fee) / filled_price
        self.cash_balance -= notional_usd
        position = next((p for p in self.positions if p["symbol"] == symbol), None)
        if position:
            total_units = position["base_units"] + base_units
            new_avg = ((position["avg_price"] * position["base_units"]) + (filled_price * base_units)) / total_units
            position["base_units"] = total_units
            position["avg_price"] = new_avg
        else:
            self.positions.append({"symbol": symbol, "base_units": base_units, "avg_price": filled_price})
        return {
            "success": True,
            "order_id": f"coin_buy_{random.randint(100000, 999999)}",
            "status": "filled",
            "filled_price": round(filled_price, 8),
            "base_units": round(base_units, 12),
            "notional_usd": round(notional_usd, 8),
            "fee_usd": round(fee, 8),
        }

    async def sell(self, symbol: str, base_units: float, **kwargs) -> Dict[str, Any]:
        base_price = self.base_prices.get(symbol, 1000.0)
        slippage = random.uniform(0.001, 0.003)
        filled_price = base_price * (1 - slippage)
        notional_usd = base_units * filled_price
        fee = notional_usd * self.fee_rate
        self.cash_balance += notional_usd - fee
        position = next((p for p in self.positions if p["symbol"] == symbol), None)
        if position:
            position["base_units"] -= base_units
            if position["base_units"] <= 0:
                self.positions.remove(position)
        return {
            "success": True,
            "order_id": f"coin_sell_{random.randint(100000, 999999)}",
            "status": "filled",
            "filled_price": round(filled_price, 8),
            "base_units": round(base_units, 12),
            "notional_usd": round(notional_usd, 8),
            "fee_usd": round(fee, 8),
        }

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return {"success": True, "order_id": order_id, "status": "canceled"}
