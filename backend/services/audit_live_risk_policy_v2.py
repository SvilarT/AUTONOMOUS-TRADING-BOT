from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditLiveRiskPolicyV2:
    """Conservative live-trading risk policy.

    This policy is intended as a final safety check before any live order can be
    submitted. It should be used in addition to existing risk services.
    """

    capital_floor_usd: float = 50.0
    max_order_notional_usd: float = 25.0
    max_daily_loss_pct: float = 0.02
    max_total_exposure_pct: float = 0.25
    max_symbol_exposure_pct: float = 0.10
    max_open_positions: int = 3
    max_trades_per_day: int = 10

    @classmethod
    def from_config(cls, config: dict[str, Any] | None) -> "AuditLiveRiskPolicyV2":
        data = config or {}
        return cls(
            capital_floor_usd=float(data.get("capital_floor_usd", cls.capital_floor_usd)),
            max_order_notional_usd=float(data.get("max_order_notional_usd", cls.max_order_notional_usd)),
            max_daily_loss_pct=float(data.get("max_daily_loss_pct", cls.max_daily_loss_pct)),
            max_total_exposure_pct=float(data.get("max_total_exposure_pct", cls.max_total_exposure_pct)),
            max_symbol_exposure_pct=float(data.get("max_symbol_exposure_pct", cls.max_symbol_exposure_pct)),
            max_open_positions=int(data.get("max_open_positions", cls.max_open_positions)),
            max_trades_per_day=int(data.get("max_trades_per_day", cls.max_trades_per_day)),
        )

    def evaluate(
        self,
        *,
        equity_usd: float,
        cash_usd: float,
        daily_pnl_usd: float,
        open_positions: list[dict[str, Any]],
        symbol: str,
        order_notional_usd: float,
        trades_today: int,
    ) -> dict[str, Any]:
        reasons: list[str] = []

        if equity_usd <= 0:
            reasons.append("invalid_equity")

        if cash_usd - order_notional_usd < self.capital_floor_usd:
            reasons.append("capital_floor_would_be_breached")

        if order_notional_usd > self.max_order_notional_usd:
            reasons.append("max_order_notional_exceeded")

        if equity_usd > 0 and daily_pnl_usd < 0:
            daily_loss_pct = abs(daily_pnl_usd) / equity_usd
            if daily_loss_pct >= self.max_daily_loss_pct:
                reasons.append("max_daily_loss_exceeded")

        if equity_usd > 0:
            total_exposure = sum(float(position.get("notional_usd", 0.0) or 0.0) for position in open_positions)
            projected_total_exposure = total_exposure + order_notional_usd
            if projected_total_exposure / equity_usd > self.max_total_exposure_pct:
                reasons.append("max_total_exposure_exceeded")

            symbol_exposure = sum(
                float(position.get("notional_usd", 0.0) or 0.0)
                for position in open_positions
                if position.get("symbol") == symbol
            )
            projected_symbol_exposure = symbol_exposure + order_notional_usd
            if projected_symbol_exposure / equity_usd > self.max_symbol_exposure_pct:
                reasons.append("max_symbol_exposure_exceeded")

        if len(open_positions) >= self.max_open_positions and not any(
            position.get("symbol") == symbol for position in open_positions
        ):
            reasons.append("max_open_positions_exceeded")

        if trades_today >= self.max_trades_per_day:
            reasons.append("max_trades_per_day_exceeded")

        return {
            "allowed": not reasons,
            "decision": "allow" if not reasons else "block",
            "reasons": reasons,
            "limits": {
                "capital_floor_usd": self.capital_floor_usd,
                "max_order_notional_usd": self.max_order_notional_usd,
                "max_daily_loss_pct": self.max_daily_loss_pct,
                "max_total_exposure_pct": self.max_total_exposure_pct,
                "max_symbol_exposure_pct": self.max_symbol_exposure_pct,
                "max_open_positions": self.max_open_positions,
                "max_trades_per_day": self.max_trades_per_day,
            },
        }
