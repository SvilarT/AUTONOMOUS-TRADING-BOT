"""Machine learning engine and adaptive models.

This module defines abstract interfaces and concrete implementations for
machine‑learning driven trading strategies.  A model is responsible for
learning from historical price data and producing actionable signals
given a recent price series.  The framework is intentionally simple but
illustrates how more sophisticated reinforcement‑learning or meta‑learning
systems can be integrated into the trading engine.

Classes
-------
AbstractModel
    Base class defining the interface for all ML models.

MomentumModel
    A basic momentum‑based model that uses the slope of recent price
    changes to determine bullish or bearish bias.

AdaptiveLearningEngine
    Manages one or more models, orchestrating training and inference.

Notes
-----
In a production environment, the ``MomentumModel`` could be replaced with
a neural network, reinforcement‑learning agent or other predictive
algorithm.  The ``AdaptiveLearningEngine`` could support online
learning, model versioning and rollback.  Here we keep the design
minimal to demonstrate the integration points.
"""

from __future__ import annotations

import abc
from typing import List, Dict, Any, Optional


class AbstractModel(abc.ABC):
    """Abstract base class for all machine learning models.

    Subclasses must implement ``train`` and ``predict``.  The ``train``
    method fits the model parameters using a historical price series,
    while ``predict`` returns a single signal dictionary for a given
    recent price series.
    """

    @abc.abstractmethod
    def train(self, prices: List[float]) -> None:
        """Train the model on a sequence of historical prices.

        Parameters
        ----------
        prices: List[float]
            Historical closing prices ordered from oldest to newest.  The
            model may compute statistics (e.g. means, variances) from
            this data.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def predict(self, prices: List[float]) -> Dict[str, Any]:
        """Generate a trading signal for the given price series.

        The returned dictionary must include at least ``action`` and
        ``confidence`` keys.  Additional metadata (e.g. model scores) may
        also be included.

        Parameters
        ----------
        prices: List[float]
            Recent closing prices ordered from oldest to newest.  The
            length of this series should be consistent with the model's
            expected lookback window.
        """
        raise NotImplementedError


class MomentumModel(AbstractModel):
    """Simple momentum model based on the slope of recent price changes.

    The model computes the average return over a configurable lookback
    period and compares it to a threshold.  If momentum exceeds the
    threshold, a buy signal is returned; if it falls below the negative
    threshold, a sell signal is produced.  Otherwise the model
    recommends holding.  The confidence is proportional to the
    magnitude of the momentum relative to the threshold.
    """

    def __init__(self, lookback: int = 20, threshold: float = 0.001) -> None:
        self.lookback = lookback
        self.threshold = threshold
        # In more complex models, training would update internal state.

    def train(self, prices: List[float]) -> None:
        """Momentum model does not require explicit training.

        For demonstration, this method could compute the average return
        and adjust the threshold adaptively.  Here we simply store
        statistics for potential analysis.
        """
        if len(prices) < 2:
            return
        # Compute mean absolute return for possible threshold tuning
        returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
        avg_abs_return = sum(abs(r) for r in returns) / len(returns)
        # Update threshold to a multiple of average absolute return
        self.threshold = max(self.threshold, avg_abs_return)

    def predict(self, prices: List[float]) -> Dict[str, Any]:
        if len(prices) < self.lookback + 1:
            # Not enough data; return hold signal with low confidence
            return {
                "action": "HOLD",
                "confidence": 0.0,
                "score": 0.0,
                "reasons": ["insufficient data for momentum"]
            }
        # Use the most recent ``lookback`` prices
        recent = prices[-self.lookback :]
        # Compute returns and their average (momentum)
        returns = [(recent[i] - recent[i - 1]) / recent[i - 1] for i in range(1, len(recent))]
        momentum = sum(returns) / len(returns)
        action: str
        if momentum > self.threshold:
            action = "BUY"
        elif momentum < -self.threshold:
            action = "SELL"
        else:
            action = "HOLD"
        # Confidence scaled relative to threshold
        confidence = min(100.0, max(0.0, abs(momentum) / self.threshold * 100)) if self.threshold > 0 else 0.0
        return {
            "action": action,
            "confidence": round(confidence, 2),
            "score": round(momentum, 6),
            "features": {"momentum": momentum, "threshold": self.threshold},
            "reasons": [f"momentum {momentum:+.5f} vs threshold {self.threshold:+.5f}"]
        }


class AdaptiveLearningEngine:
    """Orchestrates training and inference across multiple models.

    The engine allows registration of arbitrary models (instances of
    ``AbstractModel``).  At runtime, it can train all models on the same
    historical data and produce aggregated predictions.  This modular
    design makes it straightforward to mix and match models of different
    types or complexities.
    """

    def __init__(self, models: Optional[List[AbstractModel]] = None) -> None:
        self.models: List[AbstractModel] = models or []

    def add_model(self, model: AbstractModel) -> None:
        """Register a new model instance."""
        self.models.append(model)

    def train_all(self, prices: List[float]) -> None:
        """Train all models on the provided price series."""
        for model in self.models:
            try:
                model.train(prices)
            except Exception as exc:
                print(f"Model {model.__class__.__name__} training error: {exc}")

    def predict_all(self, prices: List[float]) -> List[Dict[str, Any]]:
        """Obtain predictions from all registered models.

        Returns a list of signal dictionaries which can be passed to an
        aggregation function or fed directly into allocation logic.
        """
        signals: List[Dict[str, Any]] = []
        for model in self.models:
            try:
                signals.append(model.predict(prices))
            except Exception as exc:
                print(f"Model {model.__class__.__name__} prediction error: {exc}")
        return signals