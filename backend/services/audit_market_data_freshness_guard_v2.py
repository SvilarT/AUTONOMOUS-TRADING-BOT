from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


class AuditMarketDataFreshnessGuardV2:
    """Deterministic guard for stale or invalid market data.

    Trading decisions should not be made from missing, stale, gap-corrupted, or
    invalid market data.
    """

    def __init__(self, *, max_ticker_age_seconds: int = 30, max_candle_gap_seconds: int = 120, min_candles: int = 30):
        self.max_ticker_age_seconds = max_ticker_age_seconds
        self.max_candle_gap_seconds = max_candle_gap_seconds
        self.min_candles = min_candles

    @staticmethod
    def parse_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=UTC)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=UTC)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                return None
        return None

    def check_ticker(self, ticker: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(UTC)
        timestamp = self.parse_timestamp(ticker.get("timestamp") or ticker.get("time") or ticker.get("created_at"))
        if timestamp is None:
            return {"fresh": False, "reason": "missing_or_invalid_ticker_timestamp"}

        age = now - timestamp
        if age > timedelta(seconds=self.max_ticker_age_seconds):
            return {
                "fresh": False,
                "reason": "stale_ticker",
                "age_seconds": age.total_seconds(),
                "max_age_seconds": self.max_ticker_age_seconds,
            }

        try:
            if float(ticker.get("price")) <= 0:
                return {"fresh": False, "reason": "invalid_ticker_price"}
        except (TypeError, ValueError):
            return {"fresh": False, "reason": "invalid_ticker_price"}

        return {"fresh": True, "reason": "ticker_fresh", "age_seconds": age.total_seconds()}

    def check_candles(self, candles: list[dict[str, Any]], *, now: datetime | None = None) -> dict[str, Any]:
        now = now or datetime.now(UTC)
        if len(candles) < self.min_candles:
            return {
                "fresh": False,
                "reason": "insufficient_candles",
                "count": len(candles),
                "min_candles": self.min_candles,
            }

        timestamps: list[datetime] = []
        for candle in candles:
            timestamp = self.parse_timestamp(candle.get("timestamp") or candle.get("time") or candle.get("created_at"))
            if timestamp is None:
                return {"fresh": False, "reason": "missing_or_invalid_candle_timestamp"}
            timestamps.append(timestamp)

        timestamps.sort()
        latest_age = now - timestamps[-1]
        if latest_age > timedelta(seconds=self.max_candle_gap_seconds):
            return {
                "fresh": False,
                "reason": "stale_latest_candle",
                "age_seconds": latest_age.total_seconds(),
                "max_age_seconds": self.max_candle_gap_seconds,
            }

        for earlier, later in zip(timestamps, timestamps[1:], strict=False):
            gap_seconds = (later - earlier).total_seconds()
            if gap_seconds > self.max_candle_gap_seconds:
                return {
                    "fresh": False,
                    "reason": "candle_gap_detected",
                    "gap_seconds": gap_seconds,
                    "max_gap_seconds": self.max_candle_gap_seconds,
                }

        return {"fresh": True, "reason": "candles_fresh", "latest_age_seconds": latest_age.total_seconds()}
