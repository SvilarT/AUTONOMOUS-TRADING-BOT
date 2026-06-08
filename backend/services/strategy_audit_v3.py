import hashlib
import json
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any

from services.regime_service_v2 import RegimeServiceV2
from services.strategy_registry_v3 import StrategyRegistryV3
from services.strategy_service_v2 import StrategyServiceV2


@dataclass(frozen=True)
class StrategyAuditConfigV3:
    strategy_name: str = "multi_factor_baseline"
    strategy_version: str = "v3.0.0"
    symbol: str = "BTC-USD"
    timeframe: str = "1h"
    warmup_periods: int = 30


class StrategyAuditV3:
    """Deterministic offline strategy audit harness.

    This service is intentionally research-only. It validates historical candle
    ordering, extracts point-in-time feature snapshots, labels recent regimes,
    records advisory signal snapshots, and emits reproducible fingerprints. It
    does not change positions, size orders, activate runtime state, or submit
    broker requests.
    """

    def __init__(self, registry: StrategyRegistryV3 | None = None) -> None:
        self.registry = registry or StrategyRegistryV3()

    @staticmethod
    def _price(candle: dict[str, Any]) -> float:
        return float(candle.get("close", candle.get("price", 0.0)) or 0.0)

    @staticmethod
    def _timestamp(candle: dict[str, Any], index: int) -> str:
        return str(candle.get("close_time") or candle.get("timestamp") or candle.get("open_time") or index)

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def validate_candles(cls, candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candles:
            raise ValueError("historical candles are required")

        normalized = []
        previous_timestamp = None
        for index, candle in enumerate(candles):
            price = cls._price(candle)
            timestamp = cls._timestamp(candle, index)
            if price <= 0:
                raise ValueError(f"invalid candle price at index={index}")
            if previous_timestamp is not None and timestamp <= previous_timestamp:
                raise ValueError("candles must be strictly ordered by ascending timestamp")
            normalized.append({**candle, "close": price, "timestamp": timestamp})
            previous_timestamp = timestamp
        return normalized

    @staticmethod
    def _count_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in rows:
            value = str(row.get(key, "unknown"))
            counts[value] = counts.get(value, 0) + 1
        return counts

    def audit(self, candles: list[dict[str, Any]], config: StrategyAuditConfigV3 | None = None) -> dict[str, Any]:
        config = config or StrategyAuditConfigV3()
        definition = self.registry.get(config.strategy_name, config.strategy_version)
        normalized = self.validate_candles(candles)
        if config.warmup_periods < StrategyServiceV2.MIN_HISTORY:
            raise ValueError(f"warmup_periods must be at least {StrategyServiceV2.MIN_HISTORY}")
        if len(normalized) < config.warmup_periods:
            raise ValueError("not enough candles for configured warmup period")

        strategy = StrategyServiceV2()
        regime_service = RegimeServiceV2()
        prices: list[float] = []
        snapshots: list[dict[str, Any]] = []

        for index, candle in enumerate(normalized):
            prices.append(self._price(candle))
            if len(prices) < config.warmup_periods:
                continue

            signal = strategy.generate_signal(prices, has_position=False)
            snapshots.append(
                {
                    "index": index,
                    "timestamp": self._timestamp(candle, index),
                    "price": round(prices[-1], 8),
                    "regime": regime_service.classify(prices),
                    "advisory_action": signal.get("action", "HOLD"),
                    "score": signal.get("score", 0.0),
                    "confidence": signal.get("confidence", 0.0),
                    "reasons": signal.get("reasons", []),
                    "features": signal.get("features", {}),
                }
            )

        confidence_values = [float(snapshot.get("confidence", 0.0) or 0.0) for snapshot in snapshots]
        evidence = {
            "schema_version": "strategy_audit_evidence_v3.0.0",
            "research_only": True,
            "strategy": {
                **definition.canonical_payload(),
                "fingerprint": definition.fingerprint(),
            },
            "config": asdict(config),
            "dataset": {
                "candles": len(normalized),
                "first_timestamp": self._timestamp(normalized[0], 0),
                "last_timestamp": self._timestamp(normalized[-1], len(normalized) - 1),
                "fingerprint": self._fingerprint(normalized),
            },
            "summary": {
                "snapshots": len(snapshots),
                "advisory_action_counts": self._count_by_key(snapshots, "advisory_action"),
                "regime_counts": self._count_by_key(snapshots, "regime"),
                "average_confidence": round(mean(confidence_values), 8) if confidence_values else 0.0,
            },
            "snapshots": snapshots,
        }
        return {**evidence, "evidence_fingerprint": self._fingerprint(evidence)}
