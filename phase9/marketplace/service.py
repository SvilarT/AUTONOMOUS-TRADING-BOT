"""Marketplace service for managing strategies, subscriptions and ratings.

The service provides an in‑memory implementation of basic marketplace
operations: registering strategies, listing them, subscribing users,
recording performance and calculating reputation scores.  It uses simple
incrementing IDs for strategies and does not persist data beyond the
process lifetime.  Replace with a persistent database and proper
transaction handling in a production deployment.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from datetime import datetime

from .models import StrategyMetadata, PerformanceStats, Subscription, Reputation, User


class MarketplaceService:
    def __init__(self) -> None:
        # storage dictionaries keyed by strategy_id or composite keys
        self._strategies: Dict[int, StrategyMetadata] = {}
        self._performance: Dict[int, PerformanceStats] = {}
        self._subscriptions: List[Subscription] = []
        self._reputation: Dict[int, Reputation] = {}
        self._strategy_counter: int = 1

    # Strategy operations
    def register_strategy(
        self,
        name: str,
        version: str,
        author: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        risk_profile: str = "moderate",
    ) -> StrategyMetadata:
        """Register a new strategy and return its metadata."""
        sid = self._strategy_counter
        self._strategy_counter += 1
        meta = StrategyMetadata(
            id=sid,
            name=name,
            version=version,
            author=author,
            description=description,
            tags=tags or [],
            risk_profile=risk_profile,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self._strategies[sid] = meta
        # initialise performance and reputation records
        self._performance[sid] = PerformanceStats(strategy_id=sid, returns=0.0, sharpe_ratio=0.0, max_drawdown=0.0, subscribers=0)
        self._reputation[sid] = Reputation(strategy_id=sid)
        return meta

    def list_strategies(self) -> List[StrategyMetadata]:
        return list(self._strategies.values())

    def get_strategy(self, strategy_id: int) -> Optional[StrategyMetadata]:
        return self._strategies.get(strategy_id)

    def update_performance(
        self,
        strategy_id: int,
        returns: float,
        sharpe_ratio: float,
        max_drawdown: float,
    ) -> None:
        perf = self._performance.get(strategy_id)
        if perf:
            perf.returns = returns
            perf.sharpe_ratio = sharpe_ratio
            perf.max_drawdown = max_drawdown
            perf.updated_at = datetime.utcnow()

    # Subscription operations
    def subscribe(self, user_id: str, strategy_id: int) -> Subscription:
        # Check if subscription already exists
        for sub in self._subscriptions:
            if sub.user_id == user_id and sub.strategy_id == strategy_id and sub.status == "active":
                return sub
        sub = Subscription(user_id=user_id, strategy_id=strategy_id, subscribed_at=datetime.utcnow(), status="active")
        self._subscriptions.append(sub)
        # Increment subscriber count in performance stats
        perf = self._performance.get(strategy_id)
        if perf:
            perf.subscribers += 1
        return sub

    def list_subscriptions(self, user_id: str) -> List[Subscription]:
        return [sub for sub in self._subscriptions if sub.user_id == user_id and sub.status == "active"]

    def cancel_subscription(self, user_id: str, strategy_id: int) -> bool:
        for sub in self._subscriptions:
            if sub.user_id == user_id and sub.strategy_id == strategy_id and sub.status == "active":
                sub.status = "cancelled"
                # Decrement subscriber count
                perf = self._performance.get(strategy_id)
                if perf and perf.subscribers > 0:
                    perf.subscribers -= 1
                return True
        return False

    # Reputation operations
    def rate_strategy(self, strategy_id: int, rating: float) -> float:
        rep = self._reputation.get(strategy_id)
        if rep:
            rep.add_rating(rating)
            return rep.average
        else:
            # Create reputation record if not existing
            self._reputation[strategy_id] = Reputation(strategy_id)
            self._reputation[strategy_id].add_rating(rating)
            return self._reputation[strategy_id].average

    def get_reputation(self, strategy_id: int) -> float:
        rep = self._reputation.get(strategy_id)
        return rep.average if rep else 0.0

    # Ranking
    def ranked_strategies(self) -> List[StrategyMetadata]:
        # Sort strategies by average reputation score and number of subscribers
        def key_fn(s: StrategyMetadata) -> tuple[float, int]:
            rep = self._reputation[s.id].average if s.id in self._reputation else 0.0
            subs = self._performance[s.id].subscribers if s.id in self._performance else 0
            return (rep, subs)
        return sorted(self._strategies.values(), key=key_fn, reverse=True)