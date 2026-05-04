import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class OperationalReadinessServiceV2:
    """Environment and runtime readiness checks for deployment operations."""

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def env_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _check(name: str, passed: bool, severity: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "name": name,
            "passed": passed,
            "severity": severity,
            "message": message,
            "metadata": metadata or {},
        }

    def validate_environment(self, strict: bool = False) -> Dict[str, Any]:
        debug = self.env_bool("DEBUG", False)
        simulation = self.env_bool("SIMULATION_MODE", True)
        trading_mode = os.getenv("TRADING_MODE", "paper")
        live_enabled = self.env_bool("LIVE_TRADING_ENABLED", False)
        live_adapter = os.getenv("LIVE_EXECUTION_ADAPTER", "disabled")
        cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
        checks: List[Dict[str, Any]] = []

        checks.append(self._check("jwt_secret_configured", bool(os.getenv("JWT_SECRET")), "critical", "JWT_SECRET must be configured."))
        checks.append(self._check("mongo_url_configured", bool(os.getenv("MONGO_URL")), "critical", "MONGO_URL must be configured."))
        checks.append(self._check("db_name_configured", bool(os.getenv("DB_NAME")), "critical", "DB_NAME must be configured."))
        checks.append(self._check("cors_origins_explicit", bool(cors_origins) and "*" not in cors_origins, "critical", "CORS_ORIGINS must be explicit; wildcard is not allowed outside debug."))
        checks.append(self._check("valid_trading_mode", trading_mode in {"paper", "live-readonly", "live-trading"}, "critical", "TRADING_MODE must be paper, live-readonly, or live-trading.", {"trading_mode": trading_mode}))
        checks.append(self._check("live_trading_disabled_by_default", not live_enabled or trading_mode == "live-trading", "critical", "LIVE_TRADING_ENABLED should only be true with TRADING_MODE=live-trading.", {"live_trading_enabled": live_enabled, "trading_mode": trading_mode}))

        if trading_mode == "paper":
            checks.append(self._check("paper_mode_simulation", simulation, "warning", "Paper mode should normally run with SIMULATION_MODE=true."))

        if trading_mode == "live-readonly":
            checks.append(self._check("coinbase_readonly_key", bool(os.getenv("COINBASE_EXCHANGE_API_KEY")), "critical", "Readonly Coinbase API key required."))
            checks.append(self._check("coinbase_readonly_secret", bool(os.getenv("COINBASE_EXCHANGE_API_SECRET")), "critical", "Readonly Coinbase API secret required."))
            checks.append(self._check("coinbase_readonly_passphrase", bool(os.getenv("COINBASE_EXCHANGE_PASSPHRASE")), "critical", "Readonly Coinbase passphrase required."))
            checks.append(self._check("live_execution_off_in_readonly", not live_enabled, "critical", "LIVE_TRADING_ENABLED must be false in live-readonly mode."))

        if trading_mode == "live-trading":
            checks.append(self._check("live_global_gate_enabled", live_enabled, "critical", "LIVE_TRADING_ENABLED must be true for live-trading mode."))
            checks.append(self._check("live_adapter_selected", live_adapter == "coinbase_exchange_v2", "critical", "LIVE_EXECUTION_ADAPTER must be coinbase_exchange_v2."))
            checks.append(self._check("live_approval_token_configured", bool(os.getenv("LIVE_APPROVAL_TOKEN")), "critical", "LIVE_APPROVAL_TOKEN must be configured for non-dry-run live orders."))
            checks.append(self._check("live_max_notional_low", float(os.getenv("LIVE_MAX_ORDER_NOTIONAL_USD", "999999") or 999999) <= 25.0, "warning", "Initial live max order notional should be <= 25 USD."))
            checks.append(self._check("coinbase_live_key", bool(os.getenv("COINBASE_EXCHANGE_API_KEY")), "critical", "Coinbase API key required."))
            checks.append(self._check("coinbase_live_secret", bool(os.getenv("COINBASE_EXCHANGE_API_SECRET")), "critical", "Coinbase API secret required."))
            checks.append(self._check("coinbase_live_passphrase", bool(os.getenv("COINBASE_EXCHANGE_PASSPHRASE")), "critical", "Coinbase passphrase required."))

        if not debug:
            checks.append(self._check("debug_disabled", not debug, "critical", "DEBUG must be false in production."))

        failed_critical = [check for check in checks if not check["passed"] and check["severity"] == "critical"]
        failed_warning = [check for check in checks if not check["passed"] and check["severity"] == "warning"]
        status = "ready" if not failed_critical and not failed_warning else "degraded" if not failed_critical else "blocked"
        if strict and failed_warning and not failed_critical:
            status = "blocked"
        return {
            "status": status,
            "strict": strict,
            "checks": checks,
            "summary": {
                "total": len(checks),
                "failed_critical": len(failed_critical),
                "failed_warning": len(failed_warning),
            },
            "generated_at": self.utc_now(),
        }

    async def database_health(self, db) -> Dict[str, Any]:
        try:
            await db.command("ping")
            return {"status": "ready", "database": db.name, "checked_at": self.utc_now()}
        except Exception as exc:
            return {"status": "blocked", "error": str(exc), "checked_at": self.utc_now()}

    async def readiness(self, db, strict: bool = False) -> Dict[str, Any]:
        environment = self.validate_environment(strict=strict)
        database = await self.database_health(db)
        status = "ready" if environment["status"] == "ready" and database["status"] == "ready" else "degraded" if database["status"] == "ready" else "blocked"
        return {
            "status": status,
            "environment": environment,
            "database": database,
            "checked_at": self.utc_now(),
        }
