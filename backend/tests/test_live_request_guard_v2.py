import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "test-secret-for-request-guard-more-than-thirty-two-characters")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("RUNTIME_ROLE", "api")
os.environ.setdefault("API_EMBED_BOT_MANAGER", "false")

import sys
import types

import pytest

try:
    from pymongo.errors import DuplicateKeyError
except ModuleNotFoundError:  # Local syntax/unit execution without optional runtime dependencies.
    pymongo_module = types.ModuleType("pymongo")
    errors_module = types.ModuleType("pymongo.errors")

    class DuplicateKeyError(Exception):
        pass

    errors_module.DuplicateKeyError = DuplicateKeyError
    pymongo_module.errors = errors_module
    sys.modules["pymongo"] = pymongo_module
    sys.modules["pymongo.errors"] = errors_module

from services.live_request_guard_v2 import LiveIdempotencyError, LiveRateLimitError, LiveRequestGuardV2


class FakeInsertResult:
    pass


class FakeUpdateResult:
    def __init__(self, modified_count=0):
        self.modified_count = modified_count


class FakeCollection:
    def __init__(self, unique_fields=()):
        self.docs = []
        self.unique_fields = tuple(unique_fields)

    @staticmethod
    def _matches(doc, query):
        for key, expected in query.items():
            actual = doc.get(key)
            if isinstance(expected, dict) and "$gte" in expected:
                if actual is None or actual < expected["$gte"]:
                    return False
            elif actual != expected:
                return False
        return True

    async def insert_one(self, doc):
        candidate = dict(doc)
        if self.unique_fields:
            for existing in self.docs:
                if all(existing.get(field) == candidate.get(field) for field in self.unique_fields):
                    raise DuplicateKeyError("duplicate")
        self.docs.append(candidate)
        return FakeInsertResult()

    async def count_documents(self, query):
        return len([doc for doc in self.docs if self._matches(doc, query)])

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if self._matches(doc, query):
                return {key: value for key, value in doc.items() if key != "_id"}
        return None

    async def update_one(self, query, update):
        for doc in self.docs:
            if self._matches(doc, query):
                doc.update(update.get("$set", {}))
                return FakeUpdateResult(1)
        return FakeUpdateResult(0)


class FakeDB:
    def __init__(self):
        self.live_rate_limit_events = FakeCollection()
        self.live_idempotency_records = FakeCollection(("user_id", "idempotency_key"))


@pytest.mark.asyncio
async def test_completed_identical_idempotency_retry_returns_cached_response():
    guard = LiveRequestGuardV2(FakeDB())
    body = {"symbol": "BTC-USD", "notional_usd": 5.0, "dry_run": False}
    claim = await guard.claim_idempotency(
        user_id="user-1",
        key="live-order-key-0001",
        method="POST",
        path="/api/live-trading/market-buy",
        body=body,
    )
    await guard.complete_idempotency(claim, status_code=200, response_body={"status": "blocked"})
    retry = await guard.claim_idempotency(
        user_id="user-1",
        key="live-order-key-0001",
        method="POST",
        path="/api/live-trading/market-buy",
        body=body,
    )
    assert retry["replay"] is True
    assert retry["record"]["response_status_code"] == 200
    assert retry["record"]["response_body"] == {"status": "blocked"}


@pytest.mark.asyncio
async def test_idempotency_key_cannot_be_reused_with_changed_payload():
    guard = LiveRequestGuardV2(FakeDB())
    await guard.claim_idempotency(
        user_id="user-1",
        key="live-order-key-0002",
        method="POST",
        path="/api/live-trading/market-buy",
        body={"symbol": "BTC-USD", "notional_usd": 5.0, "dry_run": False},
    )
    with pytest.raises(LiveIdempotencyError, match="different request payload"):
        await guard.claim_idempotency(
            user_id="user-1",
            key="live-order-key-0002",
            method="POST",
            path="/api/live-trading/market-buy",
            body={"symbol": "BTC-USD", "notional_usd": 6.0, "dry_run": False},
        )


@pytest.mark.asyncio
async def test_rate_limit_fails_closed_after_configured_threshold(monkeypatch):
    monkeypatch.setenv("LIVE_RATE_LIMITING_ENABLED", "true")
    monkeypatch.setenv("LIVE_RATE_LIMIT_PER_USER", "1")
    monkeypatch.setenv("LIVE_RATE_LIMIT_PER_IP", "100")
    monkeypatch.setenv("LIVE_RATE_LIMIT_GLOBAL", "100")
    guard = LiveRequestGuardV2(FakeDB())
    await guard.enforce_rate_limits(user_id="user-1", request_ip="127.0.0.1", route="/api/live-trading/market-buy")
    with pytest.raises(LiveRateLimitError, match="rate limit exceeded"):
        await guard.enforce_rate_limits(user_id="user-1", request_ip="127.0.0.1", route="/api/live-trading/market-buy")


def test_idempotency_key_format_is_strict():
    assert LiveRequestGuardV2.IDEMPOTENCY_KEY_PATTERN.fullmatch("live-order-key-0003")
    assert not LiveRequestGuardV2.IDEMPOTENCY_KEY_PATTERN.fullmatch("too-short")
    assert not LiveRequestGuardV2.IDEMPOTENCY_KEY_PATTERN.fullmatch("invalid key with spaces")
