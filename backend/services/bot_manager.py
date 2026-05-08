import asyncio
import logging
from typing import Dict

from services.bot_engine import BotEngine
from services.worker_heartbeat_service_v2 import WorkerHeartbeatServiceV2

logger = logging.getLogger(__name__)


class BotManager:
    """Manages paper bot instances for different users with worker ownership."""

    def __init__(self, db, heartbeat: WorkerHeartbeatServiceV2 | None = None):
        self.db = db
        self.active_bots: Dict[str, asyncio.Task] = {}
        self.bot_engines: Dict[str, BotEngine] = {}
        self.running = False
        self.heartbeat = heartbeat or WorkerHeartbeatServiceV2(db)

    async def start_manager(self):
        """Start the bot manager and monitor active paper bot configs."""
        self.running = True
        logger.info("Bot Manager started")

        while self.running:
            try:
                await self.heartbeat.beat(role="worker", status="running", active_bots=list(self.active_bots.keys()))
                active_configs = await self.db.bot_configs.find({"is_active": True}, {"_id": 0}).to_list(100)

                for config in active_configs:
                    user_id = config["user_id"]
                    if user_id not in self.active_bots or self.active_bots[user_id].done():
                        acquired = await self.heartbeat.acquire_bot_ownership(user_id)
                        if not acquired:
                            logger.info("Bot ownership held by another worker for user %s", user_id)
                            continue
                        logger.info("Starting bot for user %s", user_id)
                        await self.start_bot(user_id)

                for user_id in list(self.active_bots.keys()):
                    config = await self.db.bot_configs.find_one({"user_id": user_id})
                    if not config or not config.get("is_active"):
                        logger.info("Stopping bot for user %s", user_id)
                        await self.stop_bot(user_id)

                await asyncio.sleep(5)

            except Exception as exc:
                logger.error("Bot manager error: %s", exc)
                await self.heartbeat.beat(role="worker", status="error", active_bots=list(self.active_bots.keys()), metadata={"error": str(exc)})
                await asyncio.sleep(5)

    async def start_bot(self, user_id: str):
        """Start a paper bot for a specific user."""
        if user_id in self.active_bots and not self.active_bots[user_id].done():
            logger.info("Bot already running for user %s", user_id)
            return

        bot_engine = BotEngine(self.db)
        self.bot_engines[user_id] = bot_engine
        task = asyncio.create_task(bot_engine.start(user_id))
        self.active_bots[user_id] = task
        logger.info("Bot started for user %s", user_id)

    async def stop_bot(self, user_id: str):
        """Stop a paper bot for a specific user and release ownership."""
        if user_id in self.active_bots:
            if user_id in self.bot_engines:
                await self.bot_engines[user_id].stop()
                del self.bot_engines[user_id]

            self.active_bots[user_id].cancel()
            try:
                await self.active_bots[user_id]
            except asyncio.CancelledError:
                pass

            del self.active_bots[user_id]
            await self.heartbeat.release_bot_ownership(user_id)
            logger.info("Bot stopped for user %s", user_id)

    async def stop_manager(self):
        """Stop the bot manager and all running paper bots."""
        self.running = False
        for user_id in list(self.active_bots.keys()):
            await self.stop_bot(user_id)
        await self.heartbeat.mark_stopped(role="worker")
        logger.info("Bot Manager stopped")
