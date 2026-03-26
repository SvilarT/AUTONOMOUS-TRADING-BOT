from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

from services.trading_service_v2 import TradingServiceV2


class ExecutionServiceV2:
    def __init__(self):
        self.trading_service = TradingServiceV2()

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def build_client_order_id(prefix: str, symbol: str) -> str:
        return f"{prefix.lower()}_{symbol.replace('-', '').lower()}_{uuid.uuid4().hex[:16]}"

    async def buy(
        self,
        symbol: str,
        notional_usd: float,
        signal_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        client_order_id = self.build_client_order_id("buy", symbol)
        result = await self.trading_service.place_market_buy(
            symbol=symbol,
            notional_usd=notional_usd,
            client_order_id=client_order_id,
        )
        result["client_order_id"] = client_order_id
        result["requested_notional_usd"] = round(float(notional_usd), 8)
        result["signal_snapshot"] = signal_snapshot or {}
        result["timestamp"] = self.utc_now()
        return result

    async def sell(
        self,
        symbol: str,
        base_units: float,
        reason: str = "",
    ) -> Dict[str, Any]:
        client_order_id = self.build_client_order_id("sell", symbol)
        result = await self.trading_service.place_market_sell(
            symbol=symbol,
            base_units=base_units,
            client_order_id=client_order_id,
        )
        result["client_order_id"] = client_order_id
        result["requested_base_units"] = round(float(base_units), 12)
        result["reason"] = reason
        result["timestamp"] = self.utc_now()
        return result
