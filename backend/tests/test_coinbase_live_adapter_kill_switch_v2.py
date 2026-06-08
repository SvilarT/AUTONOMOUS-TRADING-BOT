import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "test-secret-for-adapter-more-than-thirty-two-characters")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("RUNTIME_ROLE", "api")
os.environ.setdefault("API_EMBED_BOT_MANAGER", "false")

import pytest

from services.coinbase_live_execution_adapter_v2 import CoinbaseLiveExecutionAdapterV2, CoinbaseLiveExecutionError


def test_adapter_kill_switch_defaults_to_enabled(monkeypatch):
    monkeypatch.delenv("COINBASE_LIVE_ORDER_KILL_SWITCH", raising=False)
    assert CoinbaseLiveExecutionAdapterV2.live_order_kill_switch_enabled() is True
    with pytest.raises(CoinbaseLiveExecutionError, match="blocked"):
        CoinbaseLiveExecutionAdapterV2.assert_live_orders_not_killed()
