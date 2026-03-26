"""Unit tests for the strategy marketplace.

These tests exercise the core marketplace service: registering
strategies, subscribing users, updating performance and rating.  The
in‑memory implementation is used; no external dependencies are
required.
"""

from __future__ import annotations

from phase12.marketplace.service import MarketplaceService


def test_register_and_rate_strategy() -> None:
    svc = MarketplaceService()
    meta = svc.register_strategy(name="MyStrategy", version="1.0", author="Alice")
    assert meta.id == 1
    # Rate the strategy and check reputation
    avg_rating = svc.rate_strategy(meta.id, 4.0)
    assert avg_rating == 4.0
    assert svc.get_reputation(meta.id) == 4.0


def test_subscription_flow() -> None:
    svc = MarketplaceService()
    meta = svc.register_strategy(name="S1", version="0.1", author="Bob")
    sub = svc.subscribe(user_id="u1", strategy_id=meta.id)
    assert sub.user_id == "u1"
    assert sub.status == "active"
    # Attempting to subscribe again should return the same subscription
    sub2 = svc.subscribe(user_id="u1", strategy_id=meta.id)
    assert sub2 is sub
    # Listing subscriptions returns one entry
    subs = svc.list_subscriptions("u1")
    assert len(subs) == 1
    # Cancel and verify
    cancelled = svc.cancel_subscription("u1", meta.id)
    assert cancelled is True
    subs_after = svc.list_subscriptions("u1")
    assert len(subs_after) == 0
