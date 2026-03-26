"""Data models for the strategy marketplace.

These lightweight classes represent strategies, performance statistics,
subscriptions, reputations and users.  In a production environment,
these would likely be SQLAlchemy models or documents stored in a
database.  For simplicity we use dataclasses and store objects in
in‑memory collections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class StrategyMetadata:
    """Metadata describing a trading strategy."""

    id: int
    name: str
    version: str
    author: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    risk_profile: str = "moderate"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerformanceStats:
    """Performance statistics for a strategy."""

    strategy_id: int
    returns: float
    sharpe_ratio: float
    max_drawdown: float
    subscribers: int = 0
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Subscription:
    """Represents a user's subscription to a strategy."""

    user_id: str
    strategy_id: int
    subscribed_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "active"  # could be "active", "cancelled", "paused"


@dataclass
class Reputation:
    """Community reputation for a strategy."""

    strategy_id: int
    rating_sum: float = 0.0
    votes: int = 0

    def add_rating(self, rating: float) -> None:
        self.rating_sum += rating
        self.votes += 1

    @property
    def average(self) -> float:
        return self.rating_sum / self.votes if self.votes > 0 else 0.0


@dataclass
class User:
    """Represents a marketplace user."""

    id: str
    name: str
    role: str = "trader"  # could be "trader", "author", etc.