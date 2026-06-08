import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import websockets

logger = logging.getLogger(__name__)


class WebSocketMarketData:
    """Real-time market data via WebSocket."""

    def __init__(self):
        self.ws_url = "wss://ws-feed.exchange.coinbase.com"
        self.connections = {}
        self.subscribers: dict[str, list[Callable[[dict[str, Any]], Awaitable[None]]]] = {}
        self.running = False
        self.price_cache: dict[str, dict[str, Any]] = {}

    async def start(self, symbols: list[str]):
        """Start WebSocket connections for given symbols."""
        self.running = True
        logger.info("Starting WebSocket for symbols: %s", symbols)

        for symbol in symbols:
            asyncio.create_task(self._connect_symbol(symbol))

    async def _connect_symbol(self, symbol: str):
        """Maintain WebSocket connection for a symbol."""
        while self.running:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    subscribe_message = {
                        "type": "subscribe",
                        "product_ids": [symbol],
                        "channels": ["ticker"],
                    }
                    await websocket.send(json.dumps(subscribe_message))
                    logger.info("Subscribed to %s ticker", symbol)

                    self.connections[symbol] = websocket

                    async for message in websocket:
                        if not self.running:
                            break

                        try:
                            data = json.loads(message)
                            await self._handle_message(symbol, data)
                        except json.JSONDecodeError:
                            logger.exception("Failed to parse message: %s", message)
                        except Exception:
                            logger.exception("Error handling message")

            except websockets.exceptions.WebSocketException:
                logger.exception("WebSocket error for %s", symbol)
                await asyncio.sleep(5)
            except Exception:
                logger.exception("Unexpected error for %s", symbol)
                await asyncio.sleep(5)

    async def _handle_message(self, symbol: str, data: dict[str, Any]):
        """Process incoming WebSocket message."""
        if data.get("type") == "ticker":
            price_update = {
                "symbol": symbol,
                "price": float(data.get("price", 0)),
                "volume_24h": float(data.get("volume_24h", 0)),
                "best_bid": float(data.get("best_bid", 0)),
                "best_ask": float(data.get("best_ask", 0)),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            self.price_cache[symbol] = price_update

            if symbol in self.subscribers:
                for callback in self.subscribers[symbol]:
                    try:
                        await callback(price_update)
                    except Exception:
                        logger.exception("Error in subscriber callback")

    def subscribe(self, symbol: str, callback: Callable[[dict[str, Any]], Awaitable[None]]):
        """Subscribe to price updates for a symbol."""
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
        logger.info("Added subscriber for %s", symbol)

    def get_latest_price(self, symbol: str) -> dict[str, Any]:
        """Get latest cached price for a symbol."""
        return self.price_cache.get(symbol, {})

    async def stop(self):
        """Stop all WebSocket connections."""
        self.running = False

        for symbol, ws in self.connections.items():
            try:
                await ws.close()
                logger.info("Closed WebSocket for %s", symbol)
            except Exception:
                logger.exception("Failed to close WebSocket for %s", symbol)

        self.connections.clear()
        logger.info("WebSocket service stopped")
