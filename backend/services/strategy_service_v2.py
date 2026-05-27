from statistics import mean, pstdev
from typing import Any


class StrategyServiceV2:
    """Base deterministic strategy signal service used by the strategy ensemble.

    The service intentionally stays dependency-light and transparent. It converts
    recent prices into a compact feature set and a conservative directional
    signal that downstream ensemble strategies can reuse. The goal is not to
    claim alpha by itself; it is to provide a stable runtime contract for the
    autonomous paper bot path.
    """

    MIN_HISTORY = 30

    @staticmethod
    def _returns(prices: list[float]) -> list[float]:
        returns = []
        for previous, current in zip(prices, prices[1:], strict=False):
            if previous:
                returns.append((current - previous) / previous)
        return returns

    @staticmethod
    def _zscore(value: float, window: list[float]) -> float:
        if not window:
            return 0.0
        avg = mean(window)
        std = pstdev(window)
        if std <= 0:
            return 0.0
        return (value - avg) / std

    @staticmethod
    def _safe_pct_change(current: float, previous: float) -> float:
        return (current - previous) / previous if previous else 0.0

    def features(self, prices: list[float]) -> dict[str, Any]:
        clean_prices = [float(price) for price in prices if float(price) > 0]
        if len(clean_prices) < self.MIN_HISTORY:
            return {
                "history": len(clean_prices),
                "sufficient_history": False,
            }

        last = clean_prices[-1]
        sma10 = mean(clean_prices[-10:])
        sma20 = mean(clean_prices[-20:])
        sma30 = mean(clean_prices[-30:])
        returns = self._returns(clean_prices)
        vol20 = pstdev(returns[-20:]) if len(returns) >= 20 else 0.0
        momentum_10 = self._safe_pct_change(last, clean_prices[-10])
        momentum_30 = self._safe_pct_change(last, clean_prices[-30])
        zscore_20 = self._zscore(last, clean_prices[-20:])
        high20 = max(clean_prices[-20:])
        low20 = min(clean_prices[-20:])
        trend_spread = (sma10 - sma30) / sma30 if sma30 else 0.0
        range_position = 0.5
        if high20 > low20:
            range_position = (last - low20) / (high20 - low20)

        return {
            "history": len(clean_prices),
            "sufficient_history": True,
            "last": round(last, 8),
            "sma10": round(sma10, 8),
            "sma20": round(sma20, 8),
            "sma30": round(sma30, 8),
            "momentum_10": round(momentum_10, 8),
            "momentum_30": round(momentum_30, 8),
            "zscore_20": round(zscore_20, 8),
            "vol20": round(vol20, 8),
            "high20": round(high20, 8),
            "low20": round(low20, 8),
            "range_position": round(range_position, 8),
            "trend_spread": round(trend_spread, 8),
        }

    def generate_signal(
        self,
        prices: list[float],
        has_position: bool,
    ) -> dict[str, Any]:
        features = self.features(prices)
        if not features.get("sufficient_history"):
            return {
                "action": "HOLD",
                "confidence": 50.0,
                "score": 0.0,
                "features": features,
                "high_volatility": False,
                "reasons": ["insufficient history"],
            }

        score = 0.0
        reasons: list[str] = []

        trend_spread = float(features.get("trend_spread", 0.0))
        momentum_10 = float(features.get("momentum_10", 0.0))
        zscore_20 = float(features.get("zscore_20", 0.0))
        vol20 = float(features.get("vol20", 0.0))

        if trend_spread > 0:
            score += min(1.5, trend_spread * 120.0)
            reasons.append("positive moving-average spread")
        elif trend_spread < 0:
            score += max(-1.5, trend_spread * 120.0)
            reasons.append("negative moving-average spread")

        if momentum_10 > 0:
            score += min(0.75, momentum_10 * 25.0)
            reasons.append("positive short-term momentum")
        elif momentum_10 < 0:
            score += max(-0.75, momentum_10 * 25.0)
            reasons.append("negative short-term momentum")

        if zscore_20 <= -1.5:
            score += 0.75
            reasons.append("short-term oversold")
        elif zscore_20 >= 1.5:
            score -= 0.75
            reasons.append("short-term overbought")

        high_volatility = vol20 > 0.02
        if high_volatility:
            score *= 0.75
            reasons.append("volatility haircut applied")

        action = "HOLD"
        if score >= 1.25:
            action = "BUY"
        elif score <= -1.25:
            action = "SELL"

        if has_position and action == "BUY":
            action = "HOLD"
            reasons.append("already positioned")
        if not has_position and action == "SELL":
            action = "HOLD"
            reasons.append("no position to sell")

        confidence = min(95.0, 50.0 + abs(score) * 14.0)

        return {
            "action": action,
            "confidence": round(confidence, 4),
            "score": round(score, 4),
            "features": features,
            "high_volatility": high_volatility,
            "reasons": reasons or ["no actionable edge"],
        }
