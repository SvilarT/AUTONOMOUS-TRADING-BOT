from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


class AuditIdempotencyGuardV2:
    """Mongo-backed idempotency and replay protection for mutation endpoints."""

    COLLECTION = "audit_idempotency_keys_v2"

    def __init__(self, db: Any, *, ttl_hours: int = 24):
        self.db = db
        self.collection = getattr(db, self.COLLECTION)
        self.ttl_hours = ttl_hours

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("idempotency_key", unique=True)
        await self.collection.create_index("expires_at")
        await self.collection.create_index([("user_id", 1), ("created_at", 1)])

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(UTC)

    async def check_and_reserve(
        self,
        *,
        user_id: str,
        idempotency_key: str,
        request_fingerprint: str,
        endpoint: str,
    ) -> dict[str, Any]:
        if not user_id:
            return {"allowed": False, "reason": "missing_user_id"}
        if not idempotency_key:
            return {"allowed": False, "reason": "missing_idempotency_key"}
        if not request_fingerprint:
            return {"allowed": False, "reason": "missing_request_fingerprint"}

        existing = await self.collection.find_one({"idempotency_key": idempotency_key}, {"_id": 0})
        if existing:
            if existing.get("request_fingerprint") != request_fingerprint:
                return {
                    "allowed": False,
                    "reason": "idempotency_key_reused_with_different_request",
                    "existing": existing,
                }
            return {"allowed": False, "reason": "duplicate_idempotency_key", "existing": existing}

        now = self.utc_now()
        record = {
            "user_id": user_id,
            "idempotency_key": idempotency_key,
            "request_fingerprint": request_fingerprint,
            "endpoint": endpoint,
            "created_at": now,
            "expires_at": now + timedelta(hours=self.ttl_hours),
        }
        await self.collection.insert_one(record)
        return {"allowed": True, "reason": "reserved", "idempotency_key": idempotency_key}
