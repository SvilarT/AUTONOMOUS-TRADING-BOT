from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class StrategyDataGuardConfigV3:
    expected_interval_seconds: int | None = None
    max_gap_multiplier: float = 3.0
    reject_duplicate_timestamps: bool = True
    reject_future_feature_columns: bool = True


class StrategyDataGuardV3:
    """Fail-closed validation for research candle datasets.

    The guard rejects malformed ordering, duplicate timestamps, non-positive
    prices, suspicious future-looking columns, and interval gaps that exceed the
    configured tolerance. It is intentionally offline and research-only.
    """

    FORBIDDEN_FUTURE_KEYS = {
        "future_price",
        "future_return",
        "next_close",
        "next_price",
        "next_return",
        "label",
        "target",
        "forward_return",
    }

    @staticmethod
    def _price(candle: dict[str, Any]) -> float:
        return float(candle.get("close", candle.get("price", 0.0)) or 0.0)

    @staticmethod
    def _timestamp(candle: dict[str, Any], index: int) -> str:
        return str(candle.get("close_time") or candle.get("timestamp") or candle.get("open_time") or index)

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"invalid candle timestamp: {value!r}") from exc

    @classmethod
    def validate(
        cls,
        candles: list[dict[str, Any]],
        config: StrategyDataGuardConfigV3 | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        config = config or StrategyDataGuardConfigV3()
        if not candles:
            raise ValueError("historical candles are required")

        normalized: list[dict[str, Any]] = []
        timestamps: list[datetime] = []
        gap_seconds: list[float] = []
        observed_keys: set[str] = set()
        previous_timestamp: datetime | None = None

        for index, candle in enumerate(candles):
            observed_keys.update(str(key) for key in candle)
            price = cls._price(candle)
            raw_timestamp = cls._timestamp(candle, index)
            timestamp = cls._parse_timestamp(raw_timestamp)

            if price <= 0:
                raise ValueError(f"invalid candle price at index={index}")
            if previous_timestamp is not None:
                if timestamp < previous_timestamp:
                    raise ValueError("candles must be ordered by ascending timestamp")
                if timestamp == previous_timestamp and config.reject_duplicate_timestamps:
                    raise ValueError("duplicate candle timestamp detected")
                gap_seconds.append((timestamp - previous_timestamp).total_seconds())

            normalized.append({**candle, "close": price, "timestamp": raw_timestamp})
            timestamps.append(timestamp)
            previous_timestamp = timestamp

        forbidden = sorted(cls.FORBIDDEN_FUTURE_KEYS.intersection(observed_keys))
        if forbidden and config.reject_future_feature_columns:
            raise ValueError(f"future-looking columns are not allowed in strategy inputs: {', '.join(forbidden)}")

        expected_interval = config.expected_interval_seconds
        if expected_interval is None:
            positive_gaps = sorted(gap for gap in gap_seconds if gap > 0)
            if positive_gaps:
                expected_interval = int(positive_gaps[len(positive_gaps) // 2])

        max_gap_seconds = None
        gaps_exceeding_tolerance = 0
        if expected_interval and expected_interval > 0:
            max_gap_seconds = float(expected_interval) * float(config.max_gap_multiplier)
            gaps_exceeding_tolerance = sum(1 for gap in gap_seconds if gap > max_gap_seconds)
            if gaps_exceeding_tolerance:
                raise ValueError("dataset contains candle gaps above configured tolerance")

        report = {
            "schema_version": "strategy_data_guard_report_v3.0.0",
            "config": asdict(config),
            "candles": len(normalized),
            "first_timestamp": cls._timestamp(normalized[0], 0),
            "last_timestamp": cls._timestamp(normalized[-1], len(normalized) - 1),
            "observed_columns": sorted(observed_keys),
            "expected_interval_seconds": expected_interval,
            "max_gap_seconds": max_gap_seconds,
            "gaps_checked": len(gap_seconds),
            "gaps_exceeding_tolerance": gaps_exceeding_tolerance,
            "future_columns_detected": forbidden,
            "point_in_time_safe": True,
        }
        return normalized, report
