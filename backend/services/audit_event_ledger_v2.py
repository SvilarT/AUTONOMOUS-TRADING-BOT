from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


class AuditEventLedgerV2:
    """Append-only audit event ledger for trading-domain facts.

    This service records important events such as signals, risk decisions,
    approvals, order submissions, fills, reconciliation results, and kill-switch
    events. It is intentionally additive and does not replace existing services.
    """

    COLLECTION = "audit_events_v2"

    def __init__(self, db: Any):
        self.db = db
        self.collection = getattr(db, self.COLLECTION)

    @staticmethod
    def utc_now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def canonical_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    @classmethod
    def event_hash(cls, event: dict[str, Any]) -> str:
        material = {
            "event_id": event["event_id"],
            "user_id": event["user_id"],
            "stream_id": event["stream_id"],
            "sequence": event["sequence"],
            "event_type": event["event_type"],
            "payload": event["payload"],
            "previous_hash": event.get("previous_hash") or "",
            "created_at": event["created_at"],
        }
        return hashlib.sha256(cls.canonical_json(material).encode("utf-8")).hexdigest()

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("event_id", unique=True)
        await self.collection.create_index([("user_id", 1), ("created_at", 1)])
        await self.collection.create_index([("stream_id", 1), ("sequence", 1)], unique=True)
        await self.collection.create_index([("event_type", 1), ("created_at", 1)])
        await self.collection.create_index([("correlation_id", 1), ("created_at", 1)])

    async def _next_sequence(self, stream_id: str) -> int:
        latest = await self.collection.find_one(
            {"stream_id": stream_id},
            {"_id": 0, "sequence": 1},
            sort=[("sequence", -1)],
        )
        return int((latest or {}).get("sequence", 0)) + 1

    async def _previous_hash(self, user_id: str) -> str | None:
        latest = await self.collection.find_one(
            {"user_id": user_id},
            {"_id": 0, "event_hash": 1},
            sort=[("created_at", -1)],
        )
        return (latest or {}).get("event_hash")

    async def append(
        self,
        *,
        user_id: str,
        stream_id: str,
        event_type: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
        actor: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not user_id:
            raise ValueError("user_id is required")
        if not stream_id:
            raise ValueError("stream_id is required")
        if not event_type:
            raise ValueError("event_type is required")

        event = {
            "event_id": uuid4().hex,
            "user_id": user_id,
            "stream_id": stream_id,
            "sequence": await self._next_sequence(stream_id),
            "event_type": event_type,
            "payload": payload,
            "correlation_id": correlation_id,
            "actor": actor,
            "metadata": metadata or {},
            "created_at": self.utc_now(),
            "previous_hash": await self._previous_hash(user_id),
        }
        event["event_hash"] = self.event_hash(event)
        await self.collection.insert_one(event)
        return {key: value for key, value in event.items() if key != "_id"}

    async def load_stream(self, stream_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        cursor = self.collection.find({"stream_id": stream_id}, {"_id": 0}).sort("sequence", 1).limit(limit)
        return await cursor.to_list(length=limit)

    async def load_user_events(self, user_id: str, limit: int = 1000) -> list[dict[str, Any]]:
        cursor = self.collection.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).limit(limit)
        return await cursor.to_list(length=limit)

    async def verify_user_chain(self, user_id: str, limit: int = 1000) -> dict[str, Any]:
        events = await self.load_user_events(user_id, limit=limit)
        previous_hash = None
        errors = []
        for event in events:
            if event.get("previous_hash") != previous_hash:
                errors.append({"event_id": event.get("event_id"), "error": "previous_hash_mismatch"})
            expected_hash = self.event_hash(event)
            if event.get("event_hash") != expected_hash:
                errors.append({"event_id": event.get("event_id"), "error": "event_hash_mismatch"})
            previous_hash = event.get("event_hash")
        return {"valid": not errors, "checked": len(events), "errors": errors}
