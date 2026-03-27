"""Risk management engine.

Consolidated from phase12 into canonical runtime for production-first use.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class RiskManager:
    def __init__(
        self,
        max_position_notional: float = 100.0,
        max_total_exposure_pct: float = 0.30,
        max_open_positions: int = 5,
        max_daily_loss_pct: float = 0.03,
        max_drawdown_pct: float = 0.05,
        cooldown_seconds: int = 300,
        vol_lookback: int = 30,
        max_volatility_pct: float = 0.10,
        var_confidence: float = 0.95,
        risk_profile: str = "moderate",
    ):
        profile_scale = {
            "conservative": 0.5,
            "moderate": 1.0,
            "aggressive": 1.5,
        }.get(risk_profile.lower(), 1.0)
        self.max_position_notional = max_position_notional
        self.max_total_exposure_pct = max_total_exposure_pct * profile_scale
        self.max_open_positions = max_open_positions
        self.max_daily_loss_pct = max_daily_loss_pct * profile_scale
        self.max_drawdown_pct = max_drawdown_pct * profile_scale
        self.cooldown_seconds = cooldown_seconds
        self.vol_lookback = vol_lookback
        self.max_volatility_pct = max_volatility_pct
        self.var_confidence = var_confidence
        self.risk_profile = risk_profile.lower()

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def portfolio_metrics(
        self,
        state: Dict[str, Any],
        positions: List[Dict[str, Any]],
        price_map: Dict[str, float],
        price_history_map: Optional[Dict[str, List[float]]] = None,
    ) -> Dict[str, Any]:
        cash = float(state.get("cash_balance", 10000.0))
        equity_high = float(state.get("equity_high", max(cash, 10000.0)))
        daily_start_equity = float(state.get("daily_start_equity", max(cash, 10000.0)))

        market_value = 0.0
        for p in positions:
            px = float(price_map.get(p["symbol"], p.get("avg_price", 0.0)))
            market_value += float(p.get("base_units", 0.0)) * px

        total_equity = cash + market_value
        equity_high = max(equity_high, total_equity)

        daily_loss_pct = max(0.0, (daily_start_equity - total_equity) / daily_start_equity) if daily_start_equity > 0 else 0.0
        drawdown_pct = max(0.0, (equity_high - total_equity) / equity_high) if equity_high > 0 else 0.0
        exposure_pct = market_value / total_equity if total_equity > 0 else 0.0

        volatility: Dict[str, float] = {}
        var: Dict[str, float] = {}
        es: Dict[str, float] = {}
        corr_matrix: Dict[str, Dict[str, float]] = {}

        if price_history_map:
            import math
            z = self._confidence_to_z(self.var_confidence)
            for sym, series in price_history_map.items():
                if len(series) < 2:
                    continue
                recent = series[-self.vol_lookback :]
                returns = [math.log(recent[i] / recent[i - 1]) for i in range(1, len(recent)) if recent[i - 1] > 0]
                if not returns:
                    continue
                mean = sum(returns) / len(returns)
                variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1) if len(returns) > 1 else 0.0
                sigma = math.sqrt(variance)
                annualised_vol = sigma * math.sqrt(365)
                volatility[sym] = annualised_vol
                var[sym] = -(mean + z * sigma)

                sorted_returns = sorted(returns)
                tail_count = max(1, int(len(sorted_returns) * (1 - self.var_confidence)))
                tail_losses = sorted_returns[:tail_count]
                es[sym] = -sum(tail_losses) / len(tail_losses) if tail_losses else 0.0

            syms = list(price_history_map.keys())
            if len(syms) > 1:
                min_len = min(len(price_history_map[s]) for s in syms)
                return_table = {}
                for s in syms:
                    series = price_history_map[s][-min_len:]
                    rts = [math.log(series[i] / series[i - 1]) for i in range(1, len(series)) if series[i - 1] > 0]
                    return_table[s] = rts
                for i, s1 in enumerate(syms):
                    corr_matrix.setdefault(s1, {})
                    for s2 in syms[i:]:
                        corr_matrix.setdefault(s2, {})
                        r1 = return_table[s1]
                        r2 = return_table[s2]
                        n = min(len(r1), len(r2))
                        if n <= 1:
                            corr = 0.0
                        else:
                            m1 = sum(r1[:n]) / n
                            m2 = sum(r2[:n]) / n
                            cov = sum((r1[j] - m1) * (r2[j] - m2) for j in range(n)) / (n - 1)
                            var1 = sum((r1[j] - m1) ** 2 for j in range(n)) / (n - 1)
                            var2 = sum((r2[j] - m2) ** 2 for j in range(n)) / (n - 1)
                            corr = 0.0 if var1 <= 0 or var2 <= 0 else cov / ((var1 ** 0.5) * (var2 ** 0.5))
                        corr_matrix[s1][s2] = corr
                        corr_matrix[s2][s1] = corr

        return {
            "cash_balance": round(cash, 8),
            "market_value": round(market_value, 8),
            "total_equity": round(total_equity, 8),
            "equity_high": round(equity_high, 8),
            "daily_start_equity": round(daily_start_equity, 8),
            "daily_loss_pct": round(daily_loss_pct, 8),
            "drawdown_pct": round(drawdown_pct, 8),
            "exposure_pct": round(exposure_pct, 8),
            "volatility": {k: round(v, 6) for k, v in volatility.items()},
            "var": {k: round(v, 6) for k, v in var.items()},
            "es": {k: round(v, 6) for k, v in es.items()},
            "correlation": {s1: {s2: round(corr_matrix[s1][s2], 4) for s2 in corr_matrix[s1]} for s1 in corr_matrix},
        }

    @staticmethod
    def _confidence_to_z(confidence: float) -> float:
        if confidence <= 0.0 or confidence >= 1.0:
            return 0.0
        import math
        c = [
            0.3374754822726147,
            0.9761690190917186,
            0.1607979714918209,
            0.0276438810333863,
            0.0038405729373609,
            0.0003951896511919,
            0.0000321767881768,
            0.0000002888167364,
            0.0000003960315187,
        ]
        p = 1.0 - confidence
        y = math.sqrt(-2.0 * math.log(p))
        return y + sum(c[i] * y ** (-(2 * i + 1)) for i in range(len(c)))

    def should_kill_switch(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        if metrics["daily_loss_pct"] >= self.max_daily_loss_pct:
            return {"triggered": True, "reason": f"daily loss limit breached ({metrics['daily_loss_pct']:.2%})"}
        if metrics["drawdown_pct"] >= self.max_drawdown_pct:
            return {"triggered": True, "reason": f"drawdown limit breached ({metrics['drawdown_pct']:.2%})"}
        for sym, vol in metrics.get("volatility", {}).items():
            if vol >= self.max_volatility_pct:
                return {"triggered": True, "reason": f"volatility limit breached for {sym} ({vol:.2%})"}
        return {"triggered": False, "reason": "ok"}

    def can_open_position(self, metrics: Dict[str, float], positions: List[Dict[str, Any]], proposed_notional: float, last_trade_at: Optional[str] = None) -> Dict[str, Any]:
        if proposed_notional > self.max_position_notional:
            return {"allowed": False, "reason": "position notional exceeds limit"}
        if len(positions) >= self.max_open_positions:
            return {"allowed": False, "reason": "max open positions reached"}
        if metrics["total_equity"] <= 0:
            return {"allowed": False, "reason": "invalid equity"}

        projected_exposure = metrics["exposure_pct"] + (proposed_notional / metrics["total_equity"])
        if projected_exposure > self.max_total_exposure_pct:
            return {"allowed": False, "reason": "total exposure limit exceeded"}

        if last_trade_at:
            try:
                last_ts = datetime.fromisoformat(last_trade_at.replace("Z", "+00:00"))
                if (self.utc_now() - last_ts).total_seconds() < self.cooldown_seconds:
                    return {"allowed": False, "reason": "trade cooldown active"}
            except Exception:
                pass

        for sym, vol in metrics.get("volatility", {}).items():
            if vol >= self.max_volatility_pct:
                return {"allowed": False, "reason": f"volatility too high for {sym}"}
        return {"allowed": True, "reason": "ok"}
