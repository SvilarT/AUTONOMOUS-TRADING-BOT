"""Pydantic schemas for API requests and responses.

These models define the structure of incoming requests and outgoing
responses for the Phase‑6 REST API.  Using Pydantic ensures type
validation and generates OpenAPI documentation automatically when used
with FastAPI.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Position(BaseModel):
    symbol: str
    base_units: float
    avg_price: float
    notional_usd: Optional[float] = None


class State(BaseModel):
    cash_balance: float = Field(..., description="Current cash balance in base currency")
    equity_high: float
    daily_start_equity: float
    realized_pnl: Optional[float] = 0.0


class PortfolioResponse(BaseModel):
    state: State
    positions: List[Position]


class MetricsResponse(BaseModel):
    metrics: Dict[str, Any]


class TradeRequest(BaseModel):
    symbol: str
    action: str  # "BUY" or "SELL"
    notional: float


class TradeResponse(BaseModel):
    success: bool
    details: Dict[str, Any]

# Marketplace schemas

class StrategyCreateRequest(BaseModel):
    """Request model for registering a new strategy in the marketplace."""
    name: str
    version: str
    author: str
    description: str | None = None
    tags: List[str] | None = None
    risk_profile: str | None = "moderate"


class StrategyResponse(BaseModel):
    """Response model representing a strategy with performance and reputation."""
    id: int
    name: str
    version: str
    author: str
    description: Optional[str] = None
    tags: List[str] = []
    risk_profile: str
    returns: float
    sharpe_ratio: float
    max_drawdown: float
    subscribers: int
    reputation: float


class PerformanceUpdateRequest(BaseModel):
    """Request model for updating a strategy's performance statistics."""
    returns: float
    sharpe_ratio: float
    max_drawdown: float


class RatingRequest(BaseModel):
    """Request model for submitting a rating for a strategy."""
    rating: float


class SubscriptionRequest(BaseModel):
    """Request model for subscribing a user to a strategy."""
    user_id: str
    strategy_id: int


class SubscriptionResponse(BaseModel):
    """Response model representing a subscription."""
    user_id: str
    strategy_id: int
    status: str


class SubscriptionListResponse(BaseModel):
    """Response model for listing subscriptions for a user."""
    subscriptions: List[SubscriptionResponse]
