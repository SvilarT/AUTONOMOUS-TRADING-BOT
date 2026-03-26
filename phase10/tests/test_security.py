"""Tests for security modules: secrets manager and custody service."""

from __future__ import annotations

import pytest
import asyncio

from phase10.security.secrets_manager import SecretsManager
from phase10.security.custody import MockCustodyService


def test_secrets_manager_set_get() -> None:
    sm = SecretsManager()
    sm.set_secret("API_KEY", "value")
    assert sm.get_secret("API_KEY") == "value"
    # Unknown key returns None
    assert sm.get_secret("NON_EXISTENT") is None


@pytest.mark.asyncio
async def test_mock_custody_deposit_withdraw() -> None:
    cs = MockCustodyService()
    res = await cs.deposit("ETH", 1.0, "addr")
    assert "tx_hash" in res
    assert await cs.get_balance("ETH") == 1.0
    res2 = await cs.withdraw("ETH", 0.5, "dest")
    assert "tx_hash" in res2
    assert await cs.get_balance("ETH") == 0.5
    # Withdrawing more than available should raise
    with pytest.raises(ValueError):
        await cs.withdraw("ETH", 1.0, "dest")
