from statistics import pstdev


class RegimeServiceV2:
    """Classify simple market regimes for strategy routing.

    This remains deterministic and explainable. It does not attempt to predict
    regime transitions; it labels recent price behavior using trend spread,
    realized volatility, and range width.
    """

    def classify(self, prices):
        if len(prices) < 30:
            return "unknown"

        recent_10 = prices[-10:]
        recent_20 = prices[-20:]
        recent_30 = prices[-30:]
        sma10 = sum(recent_10) / 10
        sma30 = sum(recent_30) / 30
        trend_spread = (sma10 - sma30) / max(abs(sma30), 1e-9)
        high = max(recent_20)
        low = min(recent_20)
        range_width = (high - low) / max(abs(low), 1e-9)
        returns = [
            (current - previous) / previous
            for previous, current in zip(recent_20, recent_20[1:])
            if previous
        ]
        volatility = pstdev(returns) if len(returns) > 1 else 0.0

        if volatility >= 0.035:
            return "high_volatility"
        if abs(trend_spread) <= 0.004 and range_width <= 0.05:
            return "range"
        if trend_spread >= 0.008:
            return "trend_up"
        if trend_spread <= -0.008:
            return "trend_down"
        return "mixed"
