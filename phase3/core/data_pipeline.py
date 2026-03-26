"""Real‑time market data pipeline.

This module introduces a simple simulation of real‑time price streaming for
testing the multi‑exchange infrastructure.  In a production system, the
``MarketDataPipeline`` would connect to WebSocket feeds from exchanges or
data vendors, normalise messages and push them to subscribed consumers.

Classes
-------
SimulatedDataProvider
    Generates synthetic price ticks around a base price using a random walk.

MarketDataPipeline
    Manages multiple data providers and dispatches tick events to
    subscribers.
"""

from __future__ import annotations

import asyncio
import random
from typing import AsyncIterator, Callable, Dict, Any, List, Optional

from .data_provider import AbstractDataProvider


class SimulatedDataProvider(AbstractDataProvider):
    """Produce simulated tick data for a symbol.

    This provider implements ``subscribe_prices`` by emitting price updates
    following a random walk around a specified base price.  It is useful for
    testing the trading loop without relying on external APIs.  Historical
    prices are generated on demand with random fluctuations.
    """

    def __init__(self, base_price: float, volatility: float = 0.002):
        self.base_price = base_price
        self.volatility = volatility

    async def subscribe_prices(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        price = self.base_price
        while True:
            # random walk: price moves by ±volatility percent
            delta = random.uniform(-self.volatility, self.volatility)
            price *= 1 + delta
            yield {
                "symbol": symbol,
                "price": round(price, 2),
                "volume": random.uniform(10, 1000),
                "timestamp": asyncio.get_event_loop().time(),
            }
            await asyncio.sleep(1)  # yield every second

    async def get_historical_prices(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        # generate synthetic historical data
        price = self.base_price
        data: List[Dict[str, Any]] = []
        for _ in range(limit):
            delta = random.uniform(-self.volatility, self.volatility)
            price *= 1 + delta
            data.append({
                "timestamp": asyncio.get_event_loop().time(),
                "open": round(price * (1 - self.volatility / 2), 2),
                "high": round(price * (1 + self.volatility / 2), 2),
                "low": round(price * (1 - self.volatility / 2), 2),
                "close": round(price, 2),
                "volume": random.uniform(10, 1000),
            })
        return data


class MarketDataPipeline:
    """Manage multiple data providers and dispatch tick events.

    Consumers can register callback coroutines to receive price updates.  The
    pipeline runs a background task for each provider and forwards events
    to all subscribers.  In a production deployment, this class would
    maintain backpressure, queue sizes and reconnection policies.
    """

    def __init__(self):
        self.providers: Dict[str, AbstractDataProvider] = {}
        self.subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._tasks: List[asyncio.Task] = []

    def add_provider(self, symbol: str, provider: AbstractDataProvider) -> None:
        self.providers[symbol] = provider

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback to receive tick events."""
        self.subscribers.append(callback)

    async def _run_provider(self, symbol: str, provider: AbstractDataProvider) -> None:
        async for event in provider.subscribe_prices(symbol):
            for cb in self.subscribers:
                # dispatch event; do not await callback to avoid blocking
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(event))
                else:
                    cb(event)

    async def start(self) -> None:
        """Start streaming from all registered providers."""
        # Cancel existing tasks
        await self.stop()
        self._tasks = [asyncio.create_task(self._run_provider(sym, prov)) for sym, prov in self.providers.items()]

    async def stop(self) -> None:
        """Stop all provider tasks."""
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
