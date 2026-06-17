from datetime import UTC, datetime, timedelta

from services.audit_market_data_freshness_guard_v2 import AuditMarketDataFreshnessGuardV2


def test_audit_market_data_guard_blocks_stale_ticker():
    guard = AuditMarketDataFreshnessGuardV2(max_ticker_age_seconds=10)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    result = guard.check_ticker({"price": 100, "timestamp": now - timedelta(seconds=11)}, now=now)

    assert result["fresh"] is False
    assert result["reason"] == "stale_ticker"


def test_audit_market_data_guard_blocks_candle_gap():
    guard = AuditMarketDataFreshnessGuardV2(max_candle_gap_seconds=60, min_candles=3)
    now = datetime(2026, 1, 1, 0, 5, tzinfo=UTC)

    result = guard.check_candles(
        [
            {"timestamp": now - timedelta(seconds=180), "price": 100},
            {"timestamp": now - timedelta(seconds=120), "price": 101},
            {"timestamp": now, "price": 102},
        ],
        now=now,
    )

    assert result["fresh"] is False
    assert result["reason"] == "candle_gap_detected"


def test_audit_market_data_guard_allows_fresh_ticker():
    guard = AuditMarketDataFreshnessGuardV2(max_ticker_age_seconds=10)
    now = datetime(2026, 1, 1, tzinfo=UTC)

    result = guard.check_ticker({"price": 100, "timestamp": now}, now=now)

    assert result["fresh"] is True
