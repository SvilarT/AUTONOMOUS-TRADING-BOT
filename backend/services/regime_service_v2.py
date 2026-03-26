class RegimeServiceV2:
    def classify(self, prices):
        if len(prices) < 30:
            return "unknown"

        sma10 = sum(prices[-10:]) / 10
        sma30 = sum(prices[-30:]) / 30
        high = max(prices[-20:])
        low = min(prices[-20:])

        if sma10 > sma30:
            return "trend_up"
        if sma10 < sma30:
            return "trend_down"
        if (high - low) / max(1e-9, low) < 0.05:
            return "range"
        return "mixed"
