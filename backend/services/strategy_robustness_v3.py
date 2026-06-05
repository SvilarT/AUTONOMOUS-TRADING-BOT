import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from services.strategy_data_guard_v3 import StrategyDataGuardConfigV3, StrategyDataGuardV3


@dataclass(frozen=True)
class RobustnessScenarioV3:
    name: str
    price_shift_bps: float = 0.0
    alternating_noise_bps: float = 0.0
    drop_every_nth_candle: int | None = None


class StrategyRobustnessV3:
    """Build deterministic offline robustness scenarios for research datasets.

    The service mutates copies of historical candle inputs only. It does not
    calculate position sizes, change runtime state, submit orders, or connect to
    exchange adapters.
    """

    DEFAULT_SCENARIOS = (
        RobustnessScenarioV3(name="baseline"),
        RobustnessScenarioV3(name="price_shift_up_10bps", price_shift_bps=10.0),
        RobustnessScenarioV3(name="price_shift_down_10bps", price_shift_bps=-10.0),
        RobustnessScenarioV3(name="alternating_noise_15bps", alternating_noise_bps=15.0),
        RobustnessScenarioV3(name="drop_every_25th_candle", drop_every_nth_candle=25),
    )

    @staticmethod
    def _fingerprint(payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _price(candle: dict[str, Any]) -> float:
        return float(candle.get("close", candle.get("price", 0.0)) or 0.0)

    @classmethod
    def apply_scenario(
        cls,
        candles: list[dict[str, Any]],
        scenario: RobustnessScenarioV3,
    ) -> list[dict[str, Any]]:
        transformed: list[dict[str, Any]] = []
        shift = float(scenario.price_shift_bps) / 10000.0
        noise = float(scenario.alternating_noise_bps) / 10000.0

        for index, candle in enumerate(candles):
            if scenario.drop_every_nth_candle and (index + 1) % scenario.drop_every_nth_candle == 0:
                continue

            price = cls._price(candle)
            alternating = noise if index % 2 == 0 else -noise
            adjusted_price = price * (1.0 + shift + alternating)
            transformed.append({**candle, "close": round(adjusted_price, 8)})
        return transformed

    @classmethod
    def build_report(
        cls,
        candles: list[dict[str, Any]],
        scenarios: tuple[RobustnessScenarioV3, ...] | None = None,
        guard_config: StrategyDataGuardConfigV3 | None = None,
    ) -> dict[str, Any]:
        scenarios = scenarios or cls.DEFAULT_SCENARIOS
        guard_config = guard_config or StrategyDataGuardConfigV3()
        StrategyDataGuardV3.validate(candles, guard_config)

        results = []
        for scenario in scenarios:
            transformed = cls.apply_scenario(candles, scenario)
            try:
                normalized, quality = StrategyDataGuardV3.validate(transformed, guard_config)
                results.append(
                    {
                        "scenario": asdict(scenario),
                        "accepted": True,
                        "candles": len(normalized),
                        "dataset_fingerprint": cls._fingerprint(normalized),
                        "quality": quality,
                    }
                )
            except ValueError as exc:
                results.append(
                    {
                        "scenario": asdict(scenario),
                        "accepted": False,
                        "error": str(exc),
                    }
                )

        report = {
            "schema_version": "strategy_robustness_report_v3.0.0",
            "research_only": True,
            "base_dataset_fingerprint": cls._fingerprint(candles),
            "scenario_count": len(results),
            "accepted_scenarios": sum(1 for result in results if result.get("accepted")),
            "rejected_scenarios": sum(1 for result in results if not result.get("accepted")),
            "results": results,
        }
        return {**report, "report_fingerprint": cls._fingerprint(report)}
