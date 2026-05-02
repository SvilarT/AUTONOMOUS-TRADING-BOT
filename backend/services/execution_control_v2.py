from datetime import datetime, timezone, timedelta
from typing import Any, Dict


class ExecutionControlV2:
    def __init__(self, db, lock_ttl_seconds: int = 30):
        self.db = db
        self.lock_ttl_seconds = lock_ttl_seconds

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def build_idempotency_key(user_id: str, symbol: str, side: str, signal_snapshot: Dict[str, Any] | None = None) -> str:
        signal_snapshot = signal_snapshot or {}
        strategy = signal_snapshot.get("selected", {}).get("strategy") or signal_snapshot.get("strategy", "unknown")
        action = signal_snapshot.get("action", side)
        return f"{user_id}:{symbol}:{side}:{action}:{strategy}"

    async def acquire_lock(self, user_id: str, symbol: str, side: str) -> Dict[str, Any]:
        key = f"{user_id}:{symbol}:{side}"
        now = self.utc_now()
        expires_at = now + timedelta(seconds=self.lock_ttl_seconds)
        existing = await self.db.execution_locks.find_one({"key": key}, {"_id": 0})
        if existing:
            existing_expiry = existing.get("expires_at")
            if isinstance(existing_expiry, str):
                try:
                    existing_expiry = datetime.fromisoformat(existing_expiry)
                except ValueError:
                    existing_expiry = None
            if existing_expiry and existing_expiry > now:
                return {"acquired": False, "key": key, "reason": "execution lock active"}

        await self.db.execution_locks.update_one(
            {"key": key},
            {"$set": {"key": key, "user_id": user_id, "symbol": symbol, "side": side, "expires_at": expires_at.isoformat(), "updated_at": now.isoformat()}},
            upsert=True,
        )
        return {"acquired": True, "key": key, "expires_at": expires_at.isoformat()}

    async def release_lock(self, key: str) -> None:
        await self.db.execution_locks.delete_one({"key": key})

    async def already_executed(self, idempotency_key: str) -> bool:
        existing = await self.db.trades_v2.find_one({"idempotency_key": idempotency_key, "status": "filled"}, {"_id": 0})
        return existing is not None
