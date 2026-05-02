import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi.security import HTTPBearer
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

from services.bot_manager import BotManager
from services.structured_logging import configure_logging, log_event

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

configure_logging()
logger = logging.getLogger(__name__)

mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
db_name = os.environ.get("DB_NAME", "trading_bot")
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
bot_manager = None


@asynccontextmanager
async def lifespan(app):
    global bot_manager
    log_event(logger, logging.INFO, "app_starting", service="autonomous_trading_bot")
    bot_manager = BotManager(db)
    manager_task = asyncio.create_task(bot_manager.start_manager())
    log_event(logger, logging.INFO, "bot_manager_started")

    yield

    log_event(logger, logging.INFO, "app_shutting_down")
    await bot_manager.stop_manager()
    manager_task.cancel()
    try:
        await manager_task
    except asyncio.CancelledError:
        pass
    client.close()
    log_event(logger, logging.INFO, "app_shutdown_complete")
