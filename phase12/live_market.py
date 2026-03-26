"""Live market dashboard and trade notification utilities.

This module defines a simple publish/subscribe mechanism for broadcasting
trade events to connected WebSocket clients.  A ``TradeNotifier``
maintains a list of active WebSocket connections and provides methods
to register, unregister and broadcast JSON messages.  A global
``trade_notifier`` instance is created at import time so that the
notifier can be shared across the API routes and the trade execution
logic.  In a production system you would likely replace this with a
more robust message bus (e.g. Redis Pub/Sub, Kafka) to support
horizontal scaling and durable event delivery.
"""

from __future__ import annotations

from typing import List, Dict, Any

from fastapi import WebSocket


class TradeNotifier:
    """Manage active WebSocket connections and broadcast trade events."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection from the list of active clients."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a JSON‐serialisable message to all active clients."""
        disconnected: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                # Mark for removal on error (client might have disconnected)
                disconnected.append(connection)
        for ws in disconnected:
            self.disconnect(ws)


# Singleton notifier used by API routes and trading logic.
trade_notifier = TradeNotifier()
