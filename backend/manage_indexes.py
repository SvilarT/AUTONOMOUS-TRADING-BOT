import asyncio
import logging

from app_state import client, db
from services.mongo_indexes_v2 import MongoIndexServiceV2
from services.structured_logging import configure_logging, log_event

configure_logging()
logger = logging.getLogger(__name__)


async def run() -> None:
    log_event(logger, logging.INFO, "index_bootstrap_starting")
    result = await MongoIndexServiceV2(db).ensure_indexes()
    log_event(logger, logging.INFO, "index_bootstrap_complete", result=result)
    client.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
