"""Strategy interfaces and engine.

Consolidated from phase12 into canonical runtime.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class AbstractStrategy(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def generate_signals(self, prices: List[float], has_position: bool) -> List[Dict[str, Any]]:
        raise NotImplementedError


class StrategyEngine:
    def __init__(self, strategies: Optional[List[AbstractStrategy]] = None):
        self.strategies: List[AbstractStrategy] = strategies or []

    def add_strategy(self, strategy: AbstractStrategy) -> None:
        self.strategies.append(strategy)

    def generate_all(self, prices: List[float], has_position: bool) -> List[Dict[str, Any]]:
        signals: List[Dict[str, Any]] = []
        for strategy in self.strategies:
            try:
                signals.extend(strategy.generate_signals(prices, has_position))
            except Exception as exc:
                print(f"Strategy {strategy.name} error: {exc}")
        return signals
