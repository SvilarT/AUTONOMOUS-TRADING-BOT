"""Custody and multi‑signature wallet integration.

This module defines abstract interfaces and stub implementations for
custody management.  For assets requiring custody (e.g. BTC, ETH),
multi‑signature wallets or external custodial services such as
Fireblocks or BitGo can be used.  Implementations should provide
secure deposit and withdrawal workflows with multi‑party approvals.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class CustodyService(ABC):
    """Abstract base class for custody providers."""

    @abstractmethod
    async def get_balance(self, asset: str) -> float:
        """Return the on‑chain balance for the given asset."""
        raise NotImplementedError

    @abstractmethod
    async def deposit(self, asset: str, amount: float, address: str) -> Dict[str, Any]:
        """Initiate a deposit into the custody account.

        Returns transaction metadata (e.g. transaction hash).
        """
        raise NotImplementedError

    @abstractmethod
    async def withdraw(self, asset: str, amount: float, to_address: str) -> Dict[str, Any]:
        """Initiate a withdrawal from the custody account.

        Should enforce multi‑sig approval workflows.  Returns transaction
        metadata.
        """
        raise NotImplementedError


class MockCustodyService(CustodyService):
    """A mock custody provider for testing purposes.

    This implementation does not perform real blockchain transactions.
    It simulates balances and returns dummy transaction hashes.  Use
    this class in development and testing environments where access to
    real custody solutions is unavailable.
    """

    def __init__(self) -> None:
        self._balances: dict[str, float] = {}

    async def get_balance(self, asset: str) -> float:
        return self._balances.get(asset, 0.0)

    async def deposit(self, asset: str, amount: float, address: str) -> Dict[str, Any]:
        # Increase balance and return dummy transaction metadata
        self._balances[asset] = self._balances.get(asset, 0.0) + amount
        return {"tx_hash": f"mock_deposit_{asset}_{amount}", "address": address}

    async def withdraw(self, asset: str, amount: float, to_address: str) -> Dict[str, Any]:
        current = self._balances.get(asset, 0.0)
        if amount > current:
            raise ValueError("Insufficient balance for withdrawal")
        self._balances[asset] = current - amount
        return {"tx_hash": f"mock_withdraw_{asset}_{amount}", "to_address": to_address}
