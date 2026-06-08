import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from pymongo.errors import DuplicateKeyError


class LiveRequestGuardError(RuntimeError):
    status_code = 409


class LiveRateLimitError(LiveRequestGuardError):
    status_code = 429


class LiveIdempotencyError(LiveRequestGuardError):
    status_code = 409


class LiveRequestGuardV2:
    """Mongo-backed abuse resistance and idempotency for privileged live mutations."""

    IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")

    def __init__(self, db):
        self.db = db

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def env_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def env_int(name: str, default: int, minimum: int = 1, maximum: int = 10_000) -> int:
        try:
            return max(minimum, min(int(os.getenv(name, str(default))), maximum))
        except ValueError:
            return default

    @classmethod
    def rate_limiting_enabled(cls) -> bool:
        return cls.env_bool("LIVE_RATE_LIMITING_ENABLED", True)

    @classmethod
    def idempotency_required(cls) -> bool:
        return cls.env_bool("LIVE_IDEMPOTENCY_REQUIRED", True)

    @staticmethod
    def canonical_json(payload: Dict[str, Any]) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)

    @classmethod
    def request_hash(cls, *, method: str, path: str, body: Dict[str, Any]) -> str:
        payload = {"method": method.upper(), "path": path, "body": body}
        return hashlib.sha256(cls.canonical_json(payload).encode("utf-8")).hexdigest()

    async def enforce_rate_limits(self, *, user_id: str, request_ip: str, route: str) -> Dict[str, Any]:
        if not self.rate_limiting_enabled():
            return {"enabled": False, "allowed": True}

        now = self.utc_now()
        window_seconds = self.env_int("LIVE_RATE_LIMIT_WINDOW_SECONDS", 60, minimum=10, maximum=3600)
        cutoff = now - timedelta(seconds=window_seconds)
        event = {"user_id": user_id, "request_ip": request_ip, "route": route, "created_at": now}
        await self.db.live_rate_limit_events.insert_one(event)

        user_limit = self.env_int("LIVE_RATE_LIMIT_PER_USER", 3)
        ip_limit = self.env_int("LIVE_RATE_LIMIT_PER_IP", 5)
        global_limit = self.env_int("LIVE_RATE_LIMIT_GLOBAL", 10)
        user_count = await self.db.live_rate_limit_events.count_documents({"user_id": user_id, "created_at": {"$gte": cutoff}})
        ip_count = await self.db.live_rate_limit_events.count_documents({"request_ip": request_ip, "created_at": {"$gte": cutoff}})
        global_count = await self.db.live_rate_limit_events.count_documents({"created_at": {"$gte": cutoff}})
        snapshot = {
            "enabled": True,
            "window_seconds": window_seconds,
            "user": {"count": user_count, "limit": user_limit},
            "ip": {"count": ip_count, "limit": ip_limit},
            "global": {"count": global_count, "limit": global_limit},
        }
        if user_count > user_limit or ip_count > ip_limit or global_count > global_limit:
            raise LiveRateLimitError("Live-trading rate limit exceeded")
        return {"allowed": True, **snapshot}

    async def claim_idempotency(
        self,
        *,
        user_id: str,
        key: Optional[str],
        method: str,
        path: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.idempotency_required():
            return {"enabled": False, "claimed": False}
        if not key or not self.IDEMPOTENCY_KEY_PATTERN.fullmatch(str(key)):
            raise LiveIdempotencyError("Idempotency-Key header required; use 16-128 letters, numbers, '.', '_', ':', or '-'")

        normalized_key = str(key)
        payload_hash = self.request_hash(method=method, path=path, body=body)
        now = self.utc_now()
        expires_at = now + timedelta(days=self.env_int("LIVE_IDEMPOTENCY_RETENTION_DAYS", 7, minimum=1, maximum=30))
        record = {
            "user_id": user_id,
            "idempotency_key": normalized_key,
            "request_hash": payload_hash,
            "method": method.upper(),
            "path": path,
            "status": "in_progress",
            "created_at": now,
            "expires_at": expires_at,
            "response_status_code": None,
            "response_body": None,
            "completed_at": None,
        }
        try:
            await self.db.live_idempotency_records.insert_one(record)
            return {"enabled": True, "claimed": True, "replay": False, "record": record}
        except DuplicateKeyError:
            existing = await self.db.live_idempotency_records.find_one(
                {"user_id": user_id, "idempotency_key": normalized_key},
                {"_id": 0},
            )
            if not existing:
                raise LiveIdempotencyError("Idempotency record conflict")
            if existing.get("request_hash") != payload_hash:
                raise LiveIdempotencyError("Idempotency-Key was already used with a different request payload")
            if existing.get("status") == "completed":
                return {"enabled": True, "claimed": False, "replay": True, "record": existing}
            raise LiveIdempotencyError("Identical live request is already in progress")

    async def complete_idempotency(self, claim: Dict[str, Any], *, status_code: int, response_body: Any) -> None:
        if not claim.get("enabled") or not claim.get("claimed"):
            return
        record = claim["record"]
        await self.db.live_idempotency_records.update_one(
            {"user_id": record["user_id"], "idempotency_key": record["idempotency_key"], "status": "in_progress"},
            {"$set": {"status": "completed", "response_status_code": int(status_code), "response_body": response_body, "completed_at": self.utc_now()}},
        )

    async def fail_idempotency(self, claim: Dict[str, Any], *, reason: str) -> None:
        if not claim.get("enabled") or not claim.get("claimed"):
            return
        record = claim["record"]
        await self.db.live_idempotency_records.update_one(
            {"user_id": record["user_id"], "idempotency_key": record["idempotency_key"], "status": "in_progress"},
            {"$set": {"status": "failed", "failure_reason": reason, "completed_at": self.utc_now()}},
        )
