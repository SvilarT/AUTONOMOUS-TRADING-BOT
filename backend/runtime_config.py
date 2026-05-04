import logging
import os
from enum import Enum
from typing import List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RuntimeRole(str, Enum):
    API = "api"
    WORKER = "worker"
    ALL = "all"
    INDEXES = "indexes"


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_csv_env(name: str, default: str) -> List[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def parse_runtime_role(raw_role: str | None) -> RuntimeRole:
    normalized = str(raw_role or "all").strip().lower()
    try:
        return RuntimeRole(normalized)
    except ValueError as exc:
        allowed = ", ".join(role.value for role in RuntimeRole)
        raise RuntimeError(f"Invalid RUNTIME_ROLE={raw_role!r}. Allowed values: {allowed}") from exc


def validate_origin(origin: str) -> None:
    parsed = urlparse(origin)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError(f"Invalid CORS origin {origin!r}; expected absolute http(s) origin")


def validate_cors_origins(origins: List[str], debug: bool) -> None:
    if not origins:
        raise RuntimeError("CORS_ORIGINS must include at least one explicit origin.")
    if "*" in origins and not debug:
        raise RuntimeError("Wildcard CORS is only allowed when DEBUG=True.")
    for origin in origins:
        if origin == "*" and debug:
            continue
        validate_origin(origin)
        if not debug and origin.startswith("http://") and "localhost" not in origin and "127.0.0.1" not in origin:
            raise RuntimeError("Production CORS origins must use https unless localhost-only.")


def validate_jwt_secret(secret: str, debug: bool) -> None:
    if debug:
        return
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters when DEBUG=False.")
    weak_values = {"secret", "password", "changeme", "replace-me", "local-debug-placeholder"}
    if secret.strip().lower() in weak_values:
        raise RuntimeError("JWT_SECRET is too weak for production use.")


DEBUG = env_bool("DEBUG", False)
SIMULATION_MODE = env_bool("SIMULATION_MODE", True)
RUNTIME_ROLE = parse_runtime_role(os.getenv("RUNTIME_ROLE", "all" if DEBUG else "api"))
RUN_MONGO_INDEX_BOOTSTRAP = env_bool("RUN_MONGO_INDEX_BOOTSTRAP", DEBUG)
API_EMBED_BOT_MANAGER = env_bool("API_EMBED_BOT_MANAGER", DEBUG or RUNTIME_ROLE == RuntimeRole.ALL)
OPS_ADMIN_ENABLED = env_bool("OPS_ADMIN_ENABLED", False)
OPS_ADMIN_EMAILS = {email.lower() for email in parse_csv_env("OPS_ADMIN_EMAILS", "")}

JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    if DEBUG:
        JWT_SECRET = "local-debug-placeholder"
        logger.warning("Using local DEBUG JWT placeholder. Set JWT_SECRET before deployment.")
    else:
        raise RuntimeError("JWT_SECRET must be configured unless DEBUG=True.")
validate_jwt_secret(JWT_SECRET, DEBUG)

CORS_ORIGINS: List[str] = parse_csv_env("CORS_ORIGINS", "http://localhost:3000")
validate_cors_origins(CORS_ORIGINS, DEBUG)
