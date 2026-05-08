import os
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "test-secret-for-worker-heartbeat-more-than-32-chars")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest

from app_state import db
from services.worker_heartbeat_service_v2 import WorkerHeartbeatServiceV2


async def cleanup():
    await db.worker_heartbeats.delete_many({})
    await db.bot_ownership.delete_many({})


@pytest.mark.asyncio
async def test_worker_heartbeat_records_and_lists_staleness():
    await cleanup()
    try:
        service = WorkerHeartbeatServiceV2(db, worker_id="worker-test-1")
        await service.beat(role="worker", status="running", active_bots=["user-1"])
        workers = await service.list_workers()

        assert len(workers["workers"]) == 1
        assert workers["workers"][0]["worker_id"] == "worker-test-1"
        assert workers["workers"][0]["active_bots"] == ["user-1"]
        assert workers["workers"][0]["stale"] is False

        stale_record = dict(workers["workers"][0])
        stale_record["last_heartbeat_at"] = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
        stale_record["stale_after_seconds"] = 1
        assert WorkerHeartbeatServiceV2.is_stale(stale_record) is True
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_bot_ownership_blocks_second_worker_until_expired():
    await cleanup()
    try:
        first = WorkerHeartbeatServiceV2(db, worker_id="worker-owner-1")
        second = WorkerHeartbeatServiceV2(db, worker_id="worker-owner-2")

        assert await first.acquire_bot_ownership("user-1", ttl_seconds=30) is True
        assert await second.acquire_bot_ownership("user-1", ttl_seconds=30) is False

        expired_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        await db.bot_ownership.update_one({"user_id": "user-1"}, {"$set": {"expires_at": expired_at}})

        assert await second.acquire_bot_ownership("user-1", ttl_seconds=30) is True
        owner = await db.bot_ownership.find_one({"user_id": "user-1"}, {"_id": 0})
        assert owner["worker_id"] == "worker-owner-2"
    finally:
        await cleanup()


@pytest.mark.asyncio
async def test_release_bot_ownership_only_releases_current_worker():
    await cleanup()
    try:
        first = WorkerHeartbeatServiceV2(db, worker_id="worker-release-1")
        second = WorkerHeartbeatServiceV2(db, worker_id="worker-release-2")
        await first.acquire_bot_ownership("user-1", ttl_seconds=30)
        await second.release_bot_ownership("user-1")
        assert await db.bot_ownership.find_one({"user_id": "user-1"}) is not None
        await first.release_bot_ownership("user-1")
        assert await db.bot_ownership.find_one({"user_id": "user-1"}) is None
    finally:
        await cleanup()
