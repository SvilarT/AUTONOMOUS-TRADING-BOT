"""Strategy interfaces and engine.

This module defines the base ``AbstractStrategy`` class and a ``StrategyEngine``
responsible for managing multiple strategy instances.  Strategies produce
recommendations (buy, sell, hold) based on historical price vectors and
current position state.  The engine aggregates signals for downstream
allocation and risk management.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class AbstractStrategy(abc.ABC):
    """Base class for trading strategies.

    Concrete strategies must implement ``generate_signals``.  They should
    accept a list of historical prices and a flag indicating whether a
    position is currently held, returning a list of signal dictionaries.  A
    single strategy may produce multiple candidate signals (e.g. breakout
    levels at different lookback periods).
    """

    name: str = "abstract"

    @abc.abstractmethod
    def generate_signals(self, prices: List[float], has_position: bool) -> List[Dict[str, Any]]:
        """Generate trading signals for the given price series.

        Parameters
        ----------
        prices: List[float]
            A list of historical closing prices ordered from oldest to
            newest.
        has_position: bool
            ``True`` if a position is currently held; strategies may use
            this to avoid generating conflicting signals.

        Returns
        -------
        List[Dict[str, Any]]
            Each dictionary must include keys: ``action`` ("BUY", "SELL",
            "HOLD"), ``confidence`` (0–100), ``score`` (float) and
            optionally ``reasons`` and ``features``.
        """
        raise NotImplementedError


class StrategyEngine:
    """Manages strategy instances and aggregates their signals.

    The engine loads strategy classes via dependency injection (e.g. from
    ``plugin_loader``) and calls their ``generate_signals`` methods to
    produce a consolidated list of signals.  Consumers can then rank and
    allocate capital based on these signals.
    """

    def __init__(self, strategies: Optional[List[AbstractStrategy]] = None):
        self.strategies: List[AbstractStrategy] = strategies or []

    def add_strategy(self, strategy: AbstractStrategy) -> None:
        """Register a new strategy instance."""
        self.strategies.append(strategy)

    def generate_all(self, prices: List[float], has_position: bool) -> List[Dict[str, Any]]:
        """Generate signals from all registered strategies.

        Parameters
        ----------
        prices: List[float]
            Historical closing prices.
        has_position: bool
            Whether a position is currently open for the symbol.

        Returns
        -------
        List[Dict[str, Any]]
            Flattened list of signal dictionaries from all strategies.
        """
        signals: List[Dict[str, Any]] = []
        for strategy in self.strategies:
            try:
                signals.extend(strategy.generate_signals(prices, has_position))
            except Exception as exc:
                # In production, consider logging and continuing rather than failing the engine.
                print(f"Strategy {strategy.name} error: {exc}")
        return signals
