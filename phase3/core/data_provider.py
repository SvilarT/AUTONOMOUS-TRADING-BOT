"""Data provider interfaces and concrete implementations.

This module defines abstract classes for real‑time and historical data
ingestion.  Providers implement asynchronous methods for subscribing to
price streams and retrieving historical candles.  Concrete implementations
should wrap exchange APIs or data vendors.  For example, a `CoinbaseProvider`
would consume the Coinbase WebSocket feed and REST API, while a
`BinanceProvider` would interface with Binance’s API.

Classes
-------
AbstractDataProvider
    Defines the contract for data providers.  All providers must implement
    subscription to live data and retrieval of historical price series.

WebSocketDataProvider
    A base class for providers that use WebSockets.  It handles connection
    management and reconnection logic.

HistoricalDataProvider
    A base class for providers that fetch historical OHLCV data via REST.

"""

from __future__ import annotations

import abc
import asyncio
import logging
from typing import AsyncIterator, Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AbstractDataProvider(abc.ABC):
    """Abstract base class for all data providers.

    Concrete subclasses must implement methods to subscribe to live price
    updates and retrieve historical data.  Providers should normalise data
    into a common format with keys: `symbol`, `price`, `bid`, `ask`,
    `timestamp`, and optional `volume`.
    """

    @abc.abstractmethod
    async def subscribe_prices(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Subscribe to a live stream of price updates.

        Parameters
        ----------
        symbol: str
            The trading symbol (e.g. ``"BTC-USD"``).

        Yields
        ------
        Dict[str, Any]
            Normalised price data.  Implementations must not block.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_historical_prices(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch historical price data.

        Parameters
        ----------
        symbol: str
            The trading symbol to fetch.
        start: Optional[str]
            ISO8601 start time (exclusive).  Defaults to provider’s earliest
            supported timestamp.
        end: Optional[str]
            ISO8601 end time (inclusive).  Defaults to now.
        limit: int
            Maximum number of observations to return.

        Returns
        -------
        List[Dict[str, Any]]
            List of OHLCV records.  Each record should contain keys ``open``,
            ``high``, ``low``, ``close``, ``volume``, and ``timestamp``.
        """
        raise NotImplementedError


class WebSocketDataProvider(AbstractDataProvider):
    """Base class for WebSocket providers.

    This class handles connection establishment, reconnection with backoff
    and basic message parsing.  Subclasses must implement the
    ``_connect`` and ``_listen`` methods to connect to specific endpoints.
    """

    def __init__(self):
        self._ws = None
        self._connected = asyncio.Event()
        self._stop = False

    async def subscribe_prices(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Yield price updates from a WebSocket.

        This method ensures a connection is established before listening for
        messages.  It automatically reconnects on error.
        """
        while not self._stop:
            try:
                await self._connect(symbol)
                self._connected.set()
                async for msg in self._listen(symbol):
                    yield msg
            except Exception as exc:
                logger.warning("WebSocket error: %s", exc)
                await asyncio.sleep(2)
                continue

    async def get_historical_prices(self, symbol: str, start: Optional[str] = None, end: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        raise NotImplementedError("WebSocket providers do not implement historical fetch by default")

    async def _connect(self, symbol: str) -> None:
        """Establish a WebSocket connection.

        Subclasses must implement logic to open the WebSocket and perform
        any subscription handshake for the given symbol.
        """
        raise NotImplementedError

    async def _listen(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        """Listen for incoming WebSocket messages.

        Subclasses must implement message parsing and yield normalised
        updates.
        """
        raise NotImplementedError


class HistoricalDataProvider(AbstractDataProvider):
    """Base class for REST‑based historical data providers."""

    async def subscribe_prices(self, symbol: str) -> AsyncIterator[Dict[str, Any]]:
        raise NotImplementedError("Historical providers do not support live subscription")

    @abc.abstractmethod
    async def _fetch(self, symbol: str, start: Optional[str], end: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Internal method to fetch data from the remote API."""
        raise NotImplementedError

    async def get_historical_prices(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        return await self._fetch(symbol, start, end, limit)
