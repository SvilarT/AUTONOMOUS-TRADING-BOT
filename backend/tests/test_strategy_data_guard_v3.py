from datetime import datetime, timedelta, timezone

import pytest

from services.strategy_data_guard_v3 import StrategyDataGuardConfigV3, StrategyDataGuardV3


def make_candles(count: int = 12, interval_seconds: int = 3600):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    candles = []
    price = 100.0
    for index in range(count):
        timestamp = start + timedelta(seconds=interval_seconds * index)
        price *= 1.001
        candles.append(
            {
                "symbol": "BTC-USD",
                "timeframe": "1h",
                "close_time": timestamp.isoformat(),
                "close": round(price, 8),
            }
        )
    return candles


def test_guard_accepts_ordered_point_in_time_safe_dataset():
    normalized, report = StrategyDataGuardV3.validate(make_candles())

    assert len(normalized) == 12
    assert report["point_in_time_safe"] is True
    assert report["expected_interval_seconds"] == 3600
    assert report["gaps_exceeding_tolerance"] == 0
    assert report["future_columns_detected"] == []


def test_guard_rejects_duplicate_timestamp():
    candles = make_candles()
    candles[5]["close_time"] = candles[4]["close_time"]

    with pytest.raises(ValueError, match="duplicate candle timestamp"):
        StrategyDataGuardV3.validate(candles)


def test_guard_rejects_descending_timestamp():
    candles = make_candles()
    candles[5]["close_time"] = candles[3]["close_time"]

    with pytest.raises(ValueError, match="ascending timestamp"):
        StrategyDataGuardV3.validate(candles)


def test_guard_rejects_large_gap():
    candles = make_candles()
    candles[8]["close_time"] = (datetime.fromisoformat(candles[7]["close_time"]) + timedelta(hours=10)).isoformat()
    for index in range(9, len(candles)):
        candles[index]["close_time"] = (
            datetime.fromisoformat(candles[index - 1]["close_time"]) + timedelta(hours=1)
        ).isoformat()

    with pytest.raises(ValueError, match="gaps above configured tolerance"):
        StrategyDataGuardV3.validate(candles, StrategyDataGuardConfigV3(expected_interval_seconds=3600))


def test_guard_rejects_future_looking_columns():
    candles = make_candles()
    candles[0]["future_return"] = 0.05

    with pytest.raises(ValueError, match="future-looking columns"):
        StrategyDataGuardV3.validate(candles)


def test_guard_rejects_non_positive_price():
    candles = make_candles()
    candles[3]["close"] = 0.0

    with pytest.raises(ValueError, match="invalid candle price"):
        StrategyDataGuardV3.validate(candles)
