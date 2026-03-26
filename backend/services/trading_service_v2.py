import random
from datetime import datetime, timezone
from typing import Dict, Any


class TradingServiceV2:
    async def place_market_buy(self, symbol: str, notional_usd: float, client_order_id: str | None = None) -> Dict[str, Any]:
        base_prices = {"BTC-USD": 45000.0, "ETH-USD": 2500.0}
        base_price = base_prices.get(symbol, 1000.0)
        slippage = random.uniform(0.001, 0.003)
        filled_price = base_price * (1 + slippage)
        fee_usd = round(float(notional_usd) * 0.001, 8)
        base_units = float(notional_usd) / filled_price if filled_price else 0.0
        return {
            "success": True,
            "order_id": client_order_id or f"sim_buy_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            "status": "filled",
            "filled_price": round(filled_price, 8),
            "base_units": round(base_units, 12),
            "notional_usd": round(float(notional_usd), 8),
            "fee_usd": fee_usd,
            "simulation": True,
        }

    async def place_market_sell(self, symbol: str, base_units: float, client_order_id: str | None = None) -> Dict[str, Any]:
        base_prices = {"BTC-USD": 45000.0, "ETH-USD": 2500.0}
        base_price = base_prices.get(symbol, 1000.0)
        slippage = random.uniform(0.001, 0.003)
        filled_price = base_price * (1 - slippage)
        notional_usd = float(base_units) * filled_price
        fee_usd = round(notional_usd * 0.001, 8)
        return {
            "success": True,
            "order_id": client_order_id or f"sim_sell_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            "status": "filled",
            "filled_price": round(filled_price, 8),
            "base_units": round(float(base_units), 12),
            "notional_usd": round(notional_usd, 8),
            "fee_usd": fee_usd,
            "simulation": True,
        }
