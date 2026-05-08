import os
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


class WorkerHeartbeatServiceV2:
    """Worker heartbeat and bot ownership registry for paper-production stability."""

    DEFAULT_STALE_AFTER_SECONDS = 30

    def __init__(self, db, worker_id: Optional[str] = None):
        self.db = db
        self.worker_id = worker_id or os.getenv("WORKER_ID") or f"worker-{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
        self.hostname = socket.gethostname()

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat()

    @classmethod
    def stale_after_seconds(cls) -> int:
        try:
            return int(os.getenv("WORKER_HEARTBEAT_STALE_AFTER_SECONDS", str(cls.DEFAULT_STALE_AFTER_SECONDS)))
        except ValueError:
            return cls.DEFAULT_STALE_AFTER_SECONDS

    async def beat(self, *, role: str, status: str = "running", active_bots: Optional[list[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        now = self.utc_now()
        record = {
            "worker_id": self.worker_id,
            "hostname": self.hostname,
            "role": role,
            "status": status,
            "active_bots": active_bots or [],
            "metadata": metadata or {},
            "last_heartbeat_at": self.iso(now),
            "stale_after_seconds": self.stale_after_seconds(),
            "updated_at": self.iso(now),
        }
        await self.db.worker_heartbeats.update_one(
            {"worker_id": self.worker_id},
            {"$set": record, "$setOnInsert": {"started_at": self.iso(now)}},
            upsert=True,
        )
        return record

    async def mark_stopped(self, *, role: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.beat(role=role, status="stopped", active_bots=[], metadata=metadata)

    @classmethod
    def is_stale(cls, record: Dict[str, Any]) -> bool:
        raw = record.get("last_heartbeat_at")
        if not raw:
            return True
        try:
            last = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
        except ValueError:
            return True
        stale_after = int(record.get("stale_after_seconds") or cls.DEFAULT_STALE_AFTER_SECONDS)
        return datetime.now(timezone.utc) - last > timedelta(seconds=stale_after)

    async def list_workers(self, limit: int = 100) -> Dict[str, Any]:
        records = await self.db.worker_heartbeats.find({}, {"_id": 0}).sort("updated_at", -1).limit(limit).to_list(limit)
        for record in records:
            record["stale"] = self.is_stale(record)
        return {"workers": records}

    async def acquire_bot_ownership(self, user_id: str, ttl_seconds: int = 30) -> bool:
        now = self.utc_now()
        expires_at = now + timedelta(seconds=ttl_seconds)
        existing = await self.db.bot_ownership.find_one({"user_id": user_id}, {"_id": 0})
        if existing:
            expired = False
            try:
                existing_expires = datetime.fromisoformat(str(existing.get("expires_at")).replace("Z", "+00:00"))
                if existing_expires.tzinfo is None:
                    existing_expires = existing_expires.replace(tzinfo=timezone.utc)
                expired = existing_expires <= now
            except Exception:
                expired = True
            if existing.get("worker_id") != self.worker_id and not expired:
                return False
        await self.db.bot_ownership.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "worker_id": self.worker_id,
                    "hostname": self.hostname,
                    "acquired_at": self.iso(now),
                    "expires_at": self.iso(expires_at),
                    "updated_at": self.iso(now),
                }
            },
            upsert=True,
        )
        return True

    async def release_bot_ownership(self, user_id: str) -> None:
        await self.db.bot_ownership.delete_one({"user_id": user_id, "worker_id": self.worker_id})
