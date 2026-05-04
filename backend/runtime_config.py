from typing import List

from services.settings_v2 import SETTINGS, RuntimeRole, SettingsV2


def env_bool(name: str, default: bool = False) -> bool:
    return SettingsV2.env_bool(name, default)


def parse_csv_env(name: str, default: str) -> List[str]:
    import os

    return SettingsV2.parse_csv(os.environ.get(name, default))


def parse_runtime_role(raw_role: str | None) -> RuntimeRole:
    return RuntimeRole(str(raw_role or "all").strip().lower())


def validate_origin(origin: str) -> None:
    SettingsV2(debug=True, jwt_secret="debug", cors_origins=[origin])


def validate_cors_origins(origins: List[str], debug: bool) -> None:
    SettingsV2(debug=debug, jwt_secret="debug" if debug else "x" * 32, cors_origins=origins)


def validate_jwt_secret(secret: str, debug: bool) -> None:
    SettingsV2(debug=debug, jwt_secret=secret, cors_origins=["http://localhost:3000"])


DEBUG = SETTINGS.debug
SIMULATION_MODE = SETTINGS.simulation_mode
RUNTIME_ROLE = SETTINGS.runtime_role
RUN_MONGO_INDEX_BOOTSTRAP = SETTINGS.run_mongo_index_bootstrap
API_EMBED_BOT_MANAGER = SETTINGS.api_embed_bot_manager
OPS_ADMIN_ENABLED = SETTINGS.ops_admin_enabled
OPS_ADMIN_EMAILS = SETTINGS.ops_admin_emails
JWT_SECRET = SETTINGS.jwt_secret
CORS_ORIGINS = SETTINGS.cors_origins
