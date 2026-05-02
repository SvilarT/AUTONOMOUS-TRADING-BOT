import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DEBUG", False)
SIMULATION_MODE = env_bool("SIMULATION_MODE", True)

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    if DEBUG:
        JWT_SECRET = "local-debug-placeholder"
        logger.warning("Using local DEBUG JWT placeholder. Set JWT_SECRET before deployment.")
    else:
        raise RuntimeError("JWT_SECRET must be configured unless DEBUG=True.")

CORS_ORIGINS: List[str] = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
if not CORS_ORIGINS:
    raise RuntimeError("CORS_ORIGINS must include at least one explicit origin.")
if "*" in CORS_ORIGINS and not DEBUG:
    raise RuntimeError("Wildcard CORS is only allowed when DEBUG=True.")
