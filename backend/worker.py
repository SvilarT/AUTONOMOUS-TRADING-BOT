import asyncio
import logging

from app_state import client, db
from runtime_config import RUNTIME_ROLE, RuntimeRole
from services.bot_manager import BotManager
from services.structured_logging import configure_logging, log_event

configure_logging()
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Run the autonomous paper bot worker as a dedicated process.

    The worker owns BotManager polling and bot task lifecycle. It intentionally
    does not expose an HTTP server. Live autonomous trading remains unavailable;
    BotManager still routes through the paper-only execution path.
    """
    if RUNTIME_ROLE not in {RuntimeRole.WORKER, RuntimeRole.ALL}:
        log_event(logger, logging.WARNING, "worker_started_with_non_worker_role", runtime_role=RUNTIME_ROLE.value)

    manager = BotManager(db)
    log_event(logger, logging.INFO, "worker_starting", runtime_role=RUNTIME_ROLE.value)
    try:
        await manager.start_manager()
    finally:
        await manager.stop_manager()
        client.close()
        log_event(logger, logging.INFO, "worker_stopped", runtime_role=RUNTIME_ROLE.value)


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
