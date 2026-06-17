import pytest

from services.audit_idempotency_guard_v2 import AuditIdempotencyGuardV2


class FakeCollection:
    def __init__(self):
        self.docs = []

    async def create_index(self, *args, **kwargs):
        return None

    async def insert_one(self, doc):
        if any(existing.get("idempotency_key") == doc.get("idempotency_key") for existing in self.docs):
            raise AssertionError("duplicate idempotency key inserted")
        self.docs.append(dict(doc))

    async def find_one(self, query, projection=None):
        for doc in self.docs:
            if all(doc.get(key) == value for key, value in query.items()):
                return dict(doc)
        return None


class FakeDb:
    def __init__(self):
        self.audit_idempotency_keys_v2 = FakeCollection()


@pytest.mark.asyncio
async def test_audit_idempotency_guard_requires_key_and_blocks_duplicate():
    guard = AuditIdempotencyGuardV2(FakeDb())

    missing = await guard.check_and_reserve(
        user_id="u1",
        idempotency_key="",
        request_fingerprint="fp1",
        endpoint="/api/live-trading/buy",
    )
    assert missing["allowed"] is False
    assert missing["reason"] == "missing_idempotency_key"

    first = await guard.check_and_reserve(
        user_id="u1",
        idempotency_key="k1",
        request_fingerprint="fp1",
        endpoint="/api/live-trading/buy",
    )
    assert first["allowed"] is True

    duplicate = await guard.check_and_reserve(
        user_id="u1",
        idempotency_key="k1",
        request_fingerprint="fp1",
        endpoint="/api/live-trading/buy",
    )
    assert duplicate["allowed"] is False
    assert duplicate["reason"] == "duplicate_idempotency_key"

    mismatch = await guard.check_and_reserve(
        user_id="u1",
        idempotency_key="k1",
        request_fingerprint="fp2",
        endpoint="/api/live-trading/buy",
    )
    assert mismatch["allowed"] is False
    assert mismatch["reason"] == "idempotency_key_reused_with_different_request"
