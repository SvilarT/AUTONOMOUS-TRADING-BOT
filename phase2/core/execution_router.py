"""Execution connectors and routing logic.

This module defines abstract exchange connectors and a router that directs
orders to the most appropriate exchange based on fees, liquidity and
availability.  It provides a foundation for multi‑exchange trading.

Use these interfaces to implement specific connectors (e.g. Binance,
CoinbasePro).  The router can later incorporate smart order routing
strategies and fallbacks.
"""

from __future__ import annotations

import abc
from typing import Dict, Any, List, Optional


class AbstractExchangeConnector(abc.ABC):
    """Abstract base class for exchange connectors.

    Methods return dictionaries mimicking a simplified order response with
    fields such as ``success``, ``order_id``, ``status`` and pricing
    details.  Implementations should translate these to and from the
    underlying exchange API formats.
    """

    name: str = "abstract"

    @abc.abstractmethod
    async def get_balances(self) -> Dict[str, float]:
        """Retrieve account balances across all currencies."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Retrieve currently open positions."""
        raise NotImplementedError

    @abc.abstractmethod
    async def buy(self, symbol: str, notional_usd: float, **kwargs) -> Dict[str, Any]:
        """Place a market or limit buy order.

        Parameters
        ----------
        symbol: str
            The trading pair, e.g. ``"BTC-USD"``.
        notional_usd: float
            Amount of USD (or quote currency) to allocate.
        kwargs: Any
            Additional order parameters (e.g. limit price).
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def sell(self, symbol: str, base_units: float, **kwargs) -> Dict[str, Any]:
        """Place a market or limit sell order."""
        raise NotImplementedError

    @abc.abstractmethod
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order."""
        raise NotImplementedError


class ExecutionRouter:
    """Routes orders to the best exchange connector.

    The router maintains a list of available connectors and selects one
    according to simple heuristics such as supported symbols, fee rates and
    service health.  In the future, the router could perform advanced
    liquidity analysis and price improvement calculations.
    """

    def __init__(self, connectors: Optional[List[AbstractExchangeConnector]] = None):
        self.connectors: List[AbstractExchangeConnector] = connectors or []

    def add_connector(self, connector: AbstractExchangeConnector) -> None:
        """Register a new exchange connector."""
        self.connectors.append(connector)

    async def select_connector(self, symbol: str) -> Optional[AbstractExchangeConnector]:
        """Select an exchange connector that supports the given symbol.

        Returns
        -------
        Optional[AbstractExchangeConnector]
            The chosen connector or ``None`` if none support the symbol.
        """
        for connector in self.connectors:
            # In a real implementation, connectors would advertise supported symbols.
            # Here we assume all connectors support all symbols.
            return connector
        return None

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
