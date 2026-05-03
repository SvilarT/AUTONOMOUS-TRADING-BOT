import base64
import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiohttp


class CoinbaseReadonlyError(RuntimeError):
    pass


class CoinbaseReadonlyAdapterV2:
    """Coinbase Exchange readonly adapter.

    This adapter intentionally exposes only account/market-data reads. It has no
    order-placement methods and should be used only for live-readonly mode.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        passphrase: Optional[str] = None,
        base_url: Optional[str] = None,
        session_factory=None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("COINBASE_EXCHANGE_API_KEY")
        self.api_secret = api_secret if api_secret is not None else os.getenv("COINBASE_EXCHANGE_API_SECRET")
        self.passphrase = passphrase if passphrase is not None else os.getenv("COINBASE_EXCHANGE_PASSPHRASE")
        self.base_url = (base_url or os.getenv("COINBASE_EXCHANGE_URL", "https://api.exchange.coinbase.com")).rstrip("/")
        self.session_factory = session_factory or aiohttp.ClientSession

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @property
    def credentials_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self.passphrase)

    def assert_credentials(self) -> None:
        if not self.credentials_configured:
            raise CoinbaseReadonlyError(
                "Coinbase readonly credentials are not configured. Set COINBASE_EXCHANGE_API_KEY, "
                "COINBASE_EXCHANGE_API_SECRET, and COINBASE_EXCHANGE_PASSPHRASE with readonly permissions."
            )

    def _signature(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        self.assert_credentials()
        message = f"{timestamp}{method.upper()}{request_path}{body}"
        try:
            secret = base64.b64decode(str(self.api_secret))
        except Exception:
            secret = str(self.api_secret).encode("utf-8")
        digest = hmac.new(secret, message.encode("utf-8"), hashlib.sha256).digest()
        return base64.b64encode(digest).decode("utf-8")

    def _headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        timestamp = str(time.time())
        return {
            "CB-ACCESS-KEY": str(self.api_key),
            "CB-ACCESS-SIGN": self._signature(timestamp, method, request_path, body),
            "CB-ACCESS-TIMESTAMP": timestamp,
            "CB-ACCESS-PASSPHRASE": str(self.passphrase),
            "Content-Type": "application/json",
        }

    async def _get_public(self, request_path: str) -> Any:
        async with self.session_factory() as session:
            async with session.get(f"{self.base_url}{request_path}") as response:
                if response.status != 200:
                    raise CoinbaseReadonlyError(f"Coinbase public GET {request_path} returned HTTP {response.status}")
                return await response.json()

    async def _get_private(self, request_path: str) -> Any:
        self.assert_credentials()
        async with self.session_factory() as session:
            async with session.get(f"{self.base_url}{request_path}", headers=self._headers("GET", request_path)) as response:
                if response.status != 200:
                    raise CoinbaseReadonlyError(f"Coinbase readonly GET {request_path} returned HTTP {response.status}")
                return await response.json()

    async def get_product_ticker(self, symbol: str) -> Dict[str, Any]:
        data = await self._get_public(f"/products/{symbol}/ticker")
        return {
            "symbol": symbol,
            "price": float(data.get("price", 0.0) or 0.0),
            "volume": float(data.get("volume", 0.0) or 0.0),
            "bid": float(data.get("bid", 0.0) or 0.0),
            "ask": float(data.get("ask", 0.0) or 0.0),
            "source": "coinbase_exchange",
            "simulation": False,
            "timestamp": self.utc_now(),
        }

    async def get_accounts(self) -> List[Dict[str, Any]]:
        raw = await self._get_private("/accounts")
        accounts = []
        for account in raw:
            balance = float(account.get("balance", 0.0) or 0.0)
            available = float(account.get("available", 0.0) or 0.0)
            hold = float(account.get("hold", 0.0) or 0.0)
            if balance == 0 and available == 0 and hold == 0:
                continue
            accounts.append(
                {
                    "id": account.get("id"),
                    "currency": account.get("currency"),
                    "balance": balance,
                    "available": available,
                    "hold": hold,
                    "profile_id": account.get("profile_id"),
                }
            )
        return accounts

    async def get_orders(self, status: str = "all", limit: int = 100) -> List[Dict[str, Any]]:
        raw = await self._get_private(f"/orders?status={status}")
        normalized = []
        for order in raw[:limit]:
            normalized.append(
                {
                    "id": order.get("id"),
                    "product_id": order.get("product_id"),
                    "side": order.get("side"),
                    "type": order.get("type"),
                    "status": order.get("status"),
                    "price": float(order.get("price", 0.0) or 0.0),
                    "size": float(order.get("size", 0.0) or 0.0),
                    "filled_size": float(order.get("filled_size", 0.0) or 0.0),
                    "executed_value": float(order.get("executed_value", 0.0) or 0.0),
                    "fill_fees": float(order.get("fill_fees", 0.0) or 0.0),
                    "created_at": order.get("created_at"),
                }
            )
        return normalized

    async def get_fills(self, product_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        path = "/fills"
        if product_id:
            path += f"?product_id={product_id}"
        raw = await self._get_private(path)
        normalized = []
        for fill in raw[:limit]:
            normalized.append(
                {
                    "trade_id": fill.get("trade_id"),
                    "order_id": fill.get("order_id"),
                    "product_id": fill.get("product_id"),
                    "side": fill.get("side"),
                    "price": float(fill.get("price", 0.0) or 0.0),
                    "size": float(fill.get("size", 0.0) or 0.0),
                    "fee": float(fill.get("fee", 0.0) or 0.0),
                    "liquidity": fill.get("liquidity"),
                    "created_at": fill.get("created_at"),
                }
            )
        return normalized

    async def snapshot(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        symbols = symbols or ["BTC-USD", "ETH-USD"]
        tickers = {}
        for symbol in symbols:
            tickers[symbol] = await self.get_product_ticker(symbol)
        accounts = await self.get_accounts()
        return {
            "mode": "live-readonly",
            "orders_allowed": False,
            "live_execution_enabled": False,
            "credentials_configured": self.credentials_configured,
            "accounts": accounts,
            "tickers": tickers,
            "timestamp": self.utc_now(),
        }

    async def place_market_buy(self, *args, **kwargs):
        raise CoinbaseReadonlyError("CoinbaseReadonlyAdapterV2 does not place orders")

    async def place_market_sell(self, *args, **kwargs):
        raise CoinbaseReadonlyError("CoinbaseReadonlyAdapterV2 does not place orders")
