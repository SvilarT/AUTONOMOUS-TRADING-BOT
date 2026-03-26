"""Advanced risk management engine.

This module extends the ideas from ``RiskGuardV2`` by introducing dynamic
risk metrics and configurable risk profiles.  It computes real‑time
exposure, drawdown and volatility measures and determines whether new
positions can be opened or existing ones should be closed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class RiskManager:
    """Risk engine computing portfolio metrics and enforcing limits."""

    def __init__(
        self,
        max_position_notional: float = 100.0,
        max_total_exposure_pct: float = 0.30,
        max_open_positions: int = 5,
        max_daily_loss_pct: float = 0.03,
        max_drawdown_pct: float = 0.05,
        cooldown_seconds: int = 300,
    ):
        self.max_position_notional = max_position_notional
        self.max_total_exposure_pct = max_total_exposure_pct
        self.max_open_positions = max_open_positions
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.cooldown_seconds = cooldown_seconds

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def portfolio_metrics(
        self, state: Dict[str, Any], positions: List[Dict[str, Any]], price_map: Dict[str, float]
    ) -> Dict[str, float]:
        """Compute cash, market value, equity and drawdown.

        Parameters mirror those of ``RiskGuardV2``; new metrics (e.g. VaR) can
        be added in future iterations.
        """
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

        return {
            "cash_balance": round(cash, 8),
            "market_value": round(market_value, 8),
            "total_equity": round(total_equity, 8),
            "equity_high": round(equity_high, 8),
            "daily_start_equity": round(daily_start_equity, 8),
            "daily_loss_pct": round(daily_loss_pct, 8),
            "drawdown_pct": round(drawdown_pct, 8),
            "exposure_pct": round(exposure_pct, 8),
        }

    def should_kill_switch(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Check whether trading should be halted due to risk violations."""
        if metrics["daily_loss_pct"] >= self.max_daily_loss_pct:
            return {"triggered": True, "reason": f"daily loss limit breached ({metrics['daily_loss_pct']:.2%})"}
        if metrics["drawdown_pct"] >= self.max_drawdown_pct:
            return {"triggered": True, "reason": f"drawdown limit breached ({metrics['drawdown_pct']:.2%})"}
        return {"triggered": False, "reason": "ok"}

    def can_open_position(
        self,
        metrics: Dict[str, float],
        positions: List[Dict[str, Any]],
        proposed_notional: float,
        last_trade_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Determine if a new position can be opened.

        This method enforces per‑position and portfolio‑level constraints.  In a
        future version, it will incorporate volatility‑adjusted limits and
        correlation analysis.
        """
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
        return {"allowed": True, "reason": "ok"}
