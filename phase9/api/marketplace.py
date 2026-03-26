"""API routes for the strategy marketplace.

This module defines endpoints for registering strategies, listing and
ranking them, updating performance, submitting ratings and managing
subscriptions.  It uses an in‑memory MarketplaceService instance to
store strategies, performance statistics, subscriptions and
reputation scores.  In a production deployment, this service
should be backed by a persistent database and incorporate proper
authentication, authorization and input validation.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from .schemas import (
    StrategyCreateRequest,
    StrategyResponse,
    PerformanceUpdateRequest,
    RatingRequest,
    SubscriptionRequest,
    SubscriptionResponse,
    SubscriptionListResponse,
)
from ..marketplace.service import MarketplaceService


router = APIRouter(prefix="/marketplace", tags=["marketplace"])

# Global marketplace service instance.  In a real application this
# would be injected via a dependency or application state.
service = MarketplaceService()


def _build_response(strategy_id: int) -> StrategyResponse:
    """Helper to construct a StrategyResponse from stored data."""
    meta = service.get_strategy(strategy_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    perf = service._performance.get(strategy_id)
    rep = service._reputation.get(strategy_id)
    return StrategyResponse(
        id=meta.id,
        name=meta.name,
        version=meta.version,
        author=meta.author,
        description=meta.description,
        tags=meta.tags or [],
        risk_profile=meta.risk_profile,
        returns=perf.returns if perf else 0.0,
        sharpe_ratio=perf.sharpe_ratio if perf else 0.0,
        max_drawdown=perf.max_drawdown if perf else 0.0,
        subscribers=perf.subscribers if perf else 0,
        reputation=rep.average if rep else 0.0,
    )


@router.post("/strategies", response_model=StrategyResponse)
def register_strategy(request: StrategyCreateRequest) -> StrategyResponse:
    """Register a new strategy and return its metadata with default metrics."""
    meta = service.register_strategy(
        name=request.name,
        version=request.version,
        author=request.author,
        description=request.description or "",
        tags=request.tags or [],
        risk_profile=request.risk_profile or "moderate",
    )
    return _build_response(meta.id)


@router.get("/strategies", response_model=List[StrategyResponse])
def list_strategies() -> List[StrategyResponse]:
    """Return a list of all registered strategies with metrics and reputation."""
    results: List[StrategyResponse] = []
    for meta in service.list_strategies():
        results.append(_build_response(meta.id))
    return results


@router.get("/strategies/ranked", response_model=List[StrategyResponse])
def ranked_strategies() -> List[StrategyResponse]:
    """Return strategies ranked by reputation and subscriber count."""
    return [_build_response(s.id) for s in service.ranked_strategies()]


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
def get_strategy(strategy_id: int) -> StrategyResponse:
    """Get detailed information about a specific strategy."""
    return _build_response(strategy_id)


@router.post("/strategies/{strategy_id}/performance")
def update_performance(strategy_id: int, request: PerformanceUpdateRequest) -> StrategyResponse:
    """Update a strategy's performance statistics and return updated info."""
    if service.get_strategy(strategy_id) is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    service.update_performance(
        strategy_id=strategy_id,
        returns=request.returns,
        sharpe_ratio=request.sharpe_ratio,
        max_drawdown=request.max_drawdown,
    )
    return _build_response(strategy_id)


@router.post("/strategies/{strategy_id}/rating")
def rate_strategy(strategy_id: int, request: RatingRequest) -> StrategyResponse:
    """Submit a rating for a strategy and return updated info."""
    if service.get_strategy(strategy_id) is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    service.rate_strategy(strategy_id, request.rating)
    return _build_response(strategy_id)


@router.post("/subscriptions", response_model=SubscriptionResponse)
def subscribe(request: SubscriptionRequest) -> SubscriptionResponse:
    """Subscribe a user to a strategy."""
    if service.get_strategy(request.strategy_id) is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    sub = service.subscribe(user_id=request.user_id, strategy_id=request.strategy_id)
    return SubscriptionResponse(user_id=sub.user_id, strategy_id=sub.strategy_id, status=sub.status)


@router.get("/subscriptions/{user_id}", response_model=SubscriptionListResponse)
def list_subscriptions(user_id: str) -> SubscriptionListResponse:
    """List all active subscriptions for a user."""
    subs = service.list_subscriptions(user_id)
    return SubscriptionListResponse(
        subscriptions=[SubscriptionResponse(user_id=s.user_id, strategy_id=s.strategy_id, status=s.status) for s in subs]
    )


@router.post("/subscriptions/cancel", response_model=SubscriptionResponse)
def cancel_subscription(request: SubscriptionRequest) -> SubscriptionResponse:
    """Cancel a user's subscription to a strategy."""
    if service.get_strategy(request.strategy_id) is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    success = service.cancel_subscription(user_id=request.user_id, strategy_id=request.strategy_id)
    if not success:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return SubscriptionResponse(user_id=request.user_id, strategy_id=request.strategy_id, status="cancelled")
