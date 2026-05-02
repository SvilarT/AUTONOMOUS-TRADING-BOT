import os
from enum import Enum
from typing import Any, Dict


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE_READONLY = "live-readonly"
    LIVE_TRADING = "live-trading"


class TradingModeError(RuntimeError):
    pass


class TradingModeService:
    def __init__(self, configured_mode: str | None = None):
        raw_mode = configured_mode or os.getenv("TRADING_MODE", "paper")
        self.mode = self.parse(raw_mode)

    @staticmethod
    def parse(raw_mode: str) -> TradingMode:
        normalized = str(raw_mode or "paper").strip().lower()
        try:
            return TradingMode(normalized)
        except ValueError as exc:
            allowed = ", ".join(mode.value for mode in TradingMode)
            raise TradingModeError(f"Invalid TRADING_MODE={raw_mode!r}. Allowed values: {allowed}") from exc

    @property
    def is_paper(self) -> bool:
        return self.mode == TradingMode.PAPER

    @property
    def is_readonly(self) -> bool:
        return self.mode == TradingMode.LIVE_READONLY

    @property
    def is_live_trading(self) -> bool:
        return self.mode == TradingMode.LIVE_TRADING

    def assert_can_trade(self) -> None:
        if self.is_readonly:
            raise TradingModeError("Trading is disabled in live-readonly mode")
        if self.is_live_trading:
            raise TradingModeError("live-trading mode requires a live execution adapter before orders can be placed")

    def describe(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "orders_allowed": self.is_paper,
            "market_data_allowed": True,
            "live_execution_enabled": False,
        }
