"""ML‑driven trading strategy plugin.

This module exposes a strategy that wraps a machine‑learning model.  It
implements the ``AbstractStrategy`` interface from the core framework and
delegates signal generation to a model instance.  By using the
``MomentumModel`` or any other ``AbstractModel`` implementation, this
strategy enables adaptive decision‑making based on historical price
dynamics.

The plugin system will load ``MLStrategy`` when configured in the
``config.yml`` file.  Users can customise the underlying model by
passing a pre‑initialised model instance to the constructor or by
subclassing ``MLStrategy`` and overriding its behaviour.
"""

from __future__ import annotations

from typing import List, Dict, Any

from ..core.strategy_engine import AbstractStrategy
from ..core.ml_engine import MomentumModel, AbstractModel


class MLStrategy(AbstractStrategy):
    """Strategy that uses a machine‑learning model to generate signals."""

    name: str = "ml_strategy"

    def __init__(self, model: AbstractModel | None = None) -> None:
        # Allow injection of a custom model; default to MomentumModel
        self.model: AbstractModel = model or MomentumModel()

    def generate_signals(self, prices: List[float], has_position: bool) -> List[Dict[str, Any]]:
        """Generate signals using the underlying model.

        Parameters
        ----------
        prices: List[float]
            Historical closing prices (oldest to newest).
        has_position: bool
            Whether a position is currently held.  This strategy does not
            condition on position state but the flag is provided for
            compatibility.

        Returns
        -------
        List[Dict[str, Any]]
            A single‑element list containing the model's signal.
        """
        # Train the model on the full price history (optional) and then predict
        try:
            self.model.train(prices)
        except Exception:
            # Training errors should not prevent signal generation
            pass
        signal = self.model.predict(prices)
        return [signal]