"""Execution connectors and routing logic.

Consolidated from phase12 into canonical runtime.
"""

from __future__ import annotations

import abc
from typing import Dict, Any, List, Optional


class AbstractExchangeConnector(abc.ABC):
    name: str = "abstract"
    fee_rate: float = 0.001
    supported_symbols: Optional[List[str]] = None

    @abc.abstractmethod
    async def get_balances(self) -> Dict[str, float]:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def buy(self, symbol: str, notional_usd: float, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def sell(self, symbol: str, base_units: float, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError

    @abc.abstractmethod
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        raise NotImplementedError


class ExecutionRouter:
    def __init__(self, connectors: Optional[List[AbstractExchangeConnector]] = None):
        self.connectors: List[AbstractExchangeConnector] = connectors or []

    def add_connector(self, connector: AbstractExchangeConnector) -> None:
        self.connectors.append(connector)

    async def select_connector(self, symbol: str) -> Optional[AbstractExchangeConnector]:
        candidates: List[AbstractExchangeConnector] = []
        for connector in self.connectors:
            supp = connector.supported_symbols
            if supp is None or symbol in supp:
                candidates.append(connector)
        if not candidates:
            return None
        candidates.sort(key=lambda c: getattr(c, "fee_rate", 1.0))
        return candidates[0]

    async def buy(self, symbol: str, notional_usd: float, **kwargs) -> Dict[str, Any]:
        connector = await self.select_connector(symbol)
        if not connector:
            return {"success": False, "reason": "no connector available"}
        return await connector.buy(symbol, notional_usd, **kwargs)

    async def sell(self, symbol: str, base_units: float, **kwargs) -> Dict[str, Any]:
        connector = await self.select_connector(symbol)
        if not connector:
            return {"success": False, "reason": "no connector available"}
        return await connector.sell(symbol, base_units, **kwargs)
