"""Coinbase connector using REST APIs.

This module sketches a production connector for Coinbase Advanced Trade.
It demonstrates how to set up API authentication, create orders and
retrieve account balances.  The final implementation should follow
Coinbase’s official API documentation.
"""

from __future__ import annotations

import aiohttp
import os
import time
import hmac
import hashlib
from typing import Dict, Any, List, Optional

from ..core.execution_router import AbstractExchangeConnector


class CoinbaseConnector(AbstractExchangeConnector):
    name = "coinbase"
    fee_rate: float = 0.0015  # Typical Coinbase taker fee
    supported_symbols: Optional[List[str]] = None

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, passphrase: Optional[str] = None, base_url: str = "https://api.exchange.coinbase.com"):
        self.api_key = api_key or os.getenv("COINBASE_API_KEY")
        self.api_secret = api_secret or os.getenv("COINBASE_API_SECRET")
        self.passphrase = passphrase or os.getenv("COINBASE_PASSPHRASE")
        self.base_url = base_url
        if not all([self.api_key, self.api_secret, self.passphrase]):
            raise ValueError("Coinbase API key, secret and passphrase must be provided")
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """Create HMAC signature for Coinbase API requests."""
        message = f"{timestamp}{method}{request_path}{body}"
        hmac_key = hmac.new(self.api_secret.encode(), message.encode(), hashlib.sha256)
        return hmac_key.hexdigest()

    async def get_balances(self) -> Dict[str, float]:
        endpoint = "/accounts"
        timestamp = str(time.time())
        method = "GET"
        signature = self._sign(timestamp, method, endpoint)
        headers = {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "CB-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }
        session = await self._get_session()
        async with session.get(self.base_url + endpoint, headers=headers) as resp:
            data = await resp.json()
            balances = {}
            for acc in data:
                currency = acc.get("currency")
                balance = float(acc.get("available", 0))
                if balance > 0:
                    balances[currency] = balance
            return balances

    async def get_positions(self) -> List[Dict[str, Any]]:
        # Coinbase uses positions for margin/futures; implement as needed.
        return []

    async def buy(self, symbol: str, notional_usd: float, **kwargs) -> Dict[str, Any]:
        # Implement order creation using POST /orders
        return {"success": False, "reason": "not implemented"}

    async def sell(self, symbol: str, base_units: float, **kwargs) -> Dict[str, Any]:
        # Implement order creation using POST /orders
        return {"success": False, "reason": "not implemented"}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return {"success": False, "reason": "not implemented"}

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
