class ExecutionOptimizerV2:
    def estimate_costs(self, confidence: float, volatility: float):
        fee_rate = 0.001
        slip_rate = min(0.005, 0.0005 + max(0.0, volatility) * 2.5)
        urgency = min(1.5, max(0.75, confidence / 70.0))
        effective_slippage = slip_rate * urgency

        return {
            "fee_rate": fee_rate,
            "slippage_rate": effective_slippage,
            "total_cost": fee_rate + effective_slippage,
        }

    def shape_notional(self, base_notional: float, confidence: float, volatility: float):
        if base_notional <= 0:
            return 0.0
        costs = self.estimate_costs(confidence, volatility)
        penalty = 1 - min(0.35, costs["total_cost"] * 20)
        return round(max(25.0, base_notional * penalty), 8)
