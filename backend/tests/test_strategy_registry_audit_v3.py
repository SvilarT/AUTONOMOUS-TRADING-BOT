from datetime import datetime, timedelta, timezone

import pytest

from services.strategy_audit_v3 import StrategyAuditConfigV3, StrategyAuditV3
from services.strategy_registry_v3 import StrategyDefinitionV3, StrategyRegistryV3


def make_candles(count: int = 80, start_price: float = 100.0, drift: float = 0.01):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    price = start_price
    for index in range(count):
        close_time = start + timedelta(hours=index + 1)
        price *= 1 + drift
        candles.append(
            {
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "close_time": close_time.isoformat(),
                "close": round(price, 8),
            }
        )
    return candles


def test_registry_contains_default_research_definition():
    registry = StrategyRegistryV3()

    definition = registry.get("multi_factor_baseline", "v3.0.0")

    assert definition.research_only is True
    assert "HOLD" in definition.supported_actions
    assert len(definition.fingerprint()) == 64


def test_registry_rejects_mutation_of_existing_identity():
    registry = StrategyRegistryV3()

    with pytest.raises(ValueError):
        registry.register(
            StrategyDefinitionV3(
                name="multi_factor_baseline",
                version="v3.0.0",
                feature_schema_version="different-schema",
                implementation="different.implementation",
            )
        )


def test_registry_rejects_definition_without_hold():
    registry = StrategyRegistryV3()

    with pytest.raises(ValueError):
        registry.register(
            StrategyDefinitionV3(
                name="invalid",
                version="v1",
                feature_schema_version="v1",
                implementation="invalid",
                supported_actions=("BUY", "SELL"),
            )
        )


def test_audit_is_deterministic_for_same_dataset_and_config():
    service = StrategyAuditV3()
    candles = make_candles()

    first = service.audit(candles)
    second = service.audit(candles)

    assert first["research_only"] is True
    assert first["dataset"]["fingerprint"] == second["dataset"]["fingerprint"]
    assert first["evidence_fingerprint"] == second["evidence_fingerprint"]
    assert first["summary"]["snapshots"] == len(candles) - StrategyAuditConfigV3().warmup_periods + 1
    assert first["snapshots"]


def test_audit_rejects_unsorted_candles():
    candles = make_candles()
    candles[5], candles[6] = candles[6], candles[5]

    with pytest.raises(ValueError):
        StrategyAuditV3().audit(candles)


def test_audit_rejects_non_positive_prices():
    candles = make_candles()
    candles[10]["close"] = 0.0

    with pytest.raises(ValueError):
        StrategyAuditV3().audit(candles)


def test_audit_rejects_short_warmup():
    with pytest.raises(ValueError):
        StrategyAuditV3().audit(make_candles(), StrategyAuditConfigV3(warmup_periods=5))
