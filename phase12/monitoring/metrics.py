"""Prometheus metrics for the trading bot.

This module defines and exposes various Prometheus metrics capturing
trade activity, risk events and service health.  Metrics are
registered on import.  The ``export_metrics`` function returns all
metrics in the Prometheus exposition format, suitable for scraping by
Prometheus or other compatible systems.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest

__all__ = [
    "trade_requests_total",
    "trade_latency_seconds",
    "risk_events_total",
    "service_health",
    "instrument_trade",
    "export_metrics",
]


# Create a dedicated registry so that tests can reset metrics easily.
registry = CollectorRegistry()

# Total number of trade requests processed, labelled by status.
trade_requests_total = Counter(
    "trade_requests_total",
    "Total number of trade requests processed",
    labelnames=["status"],
    registry=registry,
)

# Trade execution latency in seconds.
trade_latency_seconds = Histogram(
    "trade_latency_seconds",
    "Latency distribution for trade processing",
    registry=registry,
)

# Risk events (e.g. kill switch triggers, volatility breaches) counted by event type.
risk_events_total = Counter(
    "risk_events_total",
    "Number of risk events triggered",
    labelnames=["event"],
    registry=registry,
)

# Service health gauge (1 for healthy, 0 for unhealthy).  This can be
# updated by a health check routine.
service_health = Gauge(
    "service_health",
    "Overall health of the trading service (1=healthy, 0=unhealthy)",
    registry=registry,
)
service_health.set(1)


def instrument_trade(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to instrument trade handling functions.

    Wraps a function that processes a trade (e.g. the ``/trade`` API
    endpoint) and records its execution time and success/failure
    outcome.
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = await fn(*args, **kwargs)
            # Success if response indicates success=True
            status = "success"
            if hasattr(result, "success"):
                status = "success" if result.success else "failure"
            trade_requests_total.labels(status=status).inc()
            return result
        except Exception:
            trade_requests_total.labels(status="failure").inc()
            raise
        finally:
            duration = time.perf_counter() - start
            trade_latency_seconds.observe(duration)

    return wrapper


def export_metrics() -> bytes:
    """Return metrics in Prometheus exposition format."""
    return generate_latest(registry)
