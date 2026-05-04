from typing import Any, Dict, Optional

from services.paper_execution_adapter_v2 import PaperExecutionAdapterV2


class TradingServiceV2:
    """Trading service facade.

    V2 remains simulation/paper only. It delegates to a paper execution adapter
    that models order lifecycle, market-reference pricing, costs, slippage,
    precision, minimum sizes, rejections, and partial fills.
    """

    def __init__(self, adapter: Optional[PaperExecutionAdapterV2] = None):
        self.adapter = adapter or PaperExecutionAdapterV2()

    async def place_market_buy(
        self,
        symbol: str,
        notional_usd: float,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.adapter.place_market_buy(symbol=symbol, notional_usd=notional_usd, client_order_id=client_order_id)

    async def place_market_sell(
        self,
        symbol: str,
        base_units: float,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return await self.adapter.place_market_sell(symbol=symbol, base_units=base_units, client_order_id=client_order_id)
