"""Example strategy plugin implementing a simple moving average crossover.

This strategy computes short and long simple moving averages (e.g. 10 and
30 periods) on closing prices.  When the short average crosses above the
long average, it emits a ``BUY`` signal; when it crosses below, it emits
a ``SELL`` signal.  Otherwise, it returns ``HOLD``.
"""

from __future__ import annotations

from typing import List, Dict, Any

from ..core.strategy_engine import AbstractStrategy


class SimpleMovingAverageStrategy(AbstractStrategy):
    name = "sma_crossover"

    def __init__(self, short_period: int = 10, long_period: int = 30):
        if short_period >= long_period:
            raise ValueError("short_period must be less than long_period")
        self.short_period = short_period
        self.long_period = long_period

    def generate_signals(self, prices: List[float], has_position: bool) -> List[Dict[str, Any]]:
        if len(prices) < self.long_period + 1:
            return [{
                "action": "HOLD",
                "confidence": 50.0,
                "score": 0.0,
                "reasons": ["insufficient data"],
            }]
        short_ma_prev = sum(prices[-self.short_period-1:-1]) / self.short_period
        long_ma_prev = sum(prices[-self.long_period-1:-1]) / self.long_period
        short_ma_curr = sum(prices[-self.short_period:]) / self.short_period
        long_ma_curr = sum(prices[-self.long_period:]) / self.long_period

        action = "HOLD"
        score = 0.0
        reasons: List[str] = []
        if short_ma_prev <= long_ma_prev and short_ma_curr > long_ma_curr:
            action = "BUY" if not has_position else "HOLD"
            score = 2.5
            reasons.append("bullish crossover")
        elif short_ma_prev >= long_ma_prev and short_ma_curr < long_ma_curr:
            action = "SELL" if has_position else "HOLD"
            score = -2.5
            reasons.append("bearish crossover")
        return [{
            "action": action,
            "confidence": min(95.0, 50.0 + abs(score) * 12.0),
            "score": score,
            "reasons": reasons if reasons else ["no crossover"],
        }]
