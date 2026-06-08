from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.settings_v2 import SETTINGS, RuntimeRole, SettingsV2, TradingMode


class OperationalReadinessServiceV2:
    """Environment and runtime readiness checks for deployment operations."""

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _check(name: str, passed: bool, severity: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"name": name, "passed": passed, "severity": severity, "message": message, "metadata": metadata or {}}

    def validate_environment(self, strict: bool = False, settings: SettingsV2 = SETTINGS) -> Dict[str, Any]:
        checks: List[Dict[str, Any]] = []

        checks.append(self._check("jwt_secret_configured", bool(settings.jwt_secret), "critical", "JWT_SECRET must be configured."))
        checks.append(self._check("mongo_url_configured", bool(settings.mongo_url), "critical", "MONGO_URL must be configured."))
        checks.append(self._check("db_name_configured", bool(settings.db_name), "critical", "DB_NAME must be configured."))
        checks.append(self._check("cors_origins_explicit", bool(settings.cors_origins) and "*" not in settings.cors_origins, "critical", "CORS_ORIGINS must be explicit; wildcard is not allowed outside debug."))
        checks.append(self._check("valid_runtime_role", settings.runtime_role.value in {"api", "worker", "all", "indexes"}, "critical", "RUNTIME_ROLE must be api, worker, all, or indexes.", {"runtime_role": settings.runtime_role.value}))
        checks.append(self._check("valid_trading_mode", settings.trading_mode.value in {"paper", "live-readonly", "live-trading"}, "critical", "TRADING_MODE must be paper, live-readonly, or live-trading.", {"trading_mode": settings.trading_mode.value}))
        checks.append(self._check("live_trading_disabled_by_default", not settings.live_trading_enabled or settings.trading_mode == TradingMode.LIVE_TRADING, "critical", "LIVE_TRADING_ENABLED should only be true with TRADING_MODE=live-trading.", {"live_trading_enabled": settings.live_trading_enabled, "trading_mode": settings.trading_mode.value}))

        if settings.trading_mode == TradingMode.PAPER:
            checks.append(self._check("paper_mode_simulation", settings.simulation_mode, "warning", "Paper mode should normally run with SIMULATION_MODE=true."))

        if settings.trading_mode == TradingMode.LIVE_READONLY:
            checks.append(self._check("coinbase_readonly_key", bool(settings.coinbase_exchange_api_key), "critical", "Readonly Coinbase API key required."))
            checks.append(self._check("coinbase_readonly_secret", bool(settings.coinbase_exchange_api_secret), "critical", "Readonly Coinbase API secret required."))
            checks.append(self._check("coinbase_readonly_passphrase", bool(settings.coinbase_exchange_passphrase), "critical", "Readonly Coinbase passphrase required."))
            checks.append(self._check("live_execution_off_in_readonly", not settings.live_trading_enabled, "critical", "LIVE_TRADING_ENABLED must be false in live-readonly mode."))

        if settings.trading_mode == TradingMode.LIVE_TRADING:
            checks.append(self._check("debug_disabled", not settings.debug, "critical", "DEBUG must be false in live-trading mode."))
            checks.append(self._check("api_worker_process_separated", settings.runtime_role == RuntimeRole.API and not settings.api_embed_bot_manager, "critical", "Live trading requires RUNTIME_ROLE=api and API_EMBED_BOT_MANAGER=false."))
            checks.append(self._check("live_global_gate_enabled", settings.live_trading_enabled, "critical", "LIVE_TRADING_ENABLED must be true for live-trading mode."))
            checks.append(self._check("live_adapter_selected", settings.live_execution_adapter == "coinbase_exchange_v2", "critical", "LIVE_EXECUTION_ADAPTER must be coinbase_exchange_v2."))
            checks.append(self._check("live_mfa_enabled", settings.live_mfa_required and bool(settings.live_totp_secret), "critical", "TOTP-backed live-session elevation must be configured."))
            checks.append(self._check("live_rate_limiting_enabled", settings.live_rate_limiting_enabled, "critical", "Live endpoint rate limiting must remain enabled."))
            checks.append(self._check("live_idempotency_required", settings.live_idempotency_required, "critical", "Live order idempotency keys must remain required."))
            checks.append(self._check("ops_admin_configured", settings.ops_admin_enabled and bool(settings.ops_admin_emails), "critical", "OPS admin emails must be configured for emergency operations."))
            checks.append(self._check("ops_alert_webhook_configured", bool(settings.ops_alert_webhook_url), "critical", "OPS_ALERT_WEBHOOK_URL or OPS_ALERT_WEBHOOK_URL_FILE must be configured."))
            checks.append(self._check("live_credential_boundary_attested", settings.live_operator_attestation_accepted and settings.live_credentials_withdrawals_disabled_confirmed and settings.live_credentials_transfers_disabled_confirmed and settings.live_credentials_ip_allowlist_confirmed, "critical", "Live credentials must be reviewed: withdrawals disabled, transfers disabled, IP allowlist configured, and operator attestation accepted."))
            checks.append(self._check("live_max_notional_low", settings.live_max_order_notional_usd <= 25.0, "warning", "Initial live max order notional should be <= 25 USD."))
            checks.append(self._check("coinbase_live_key", bool(settings.coinbase_exchange_api_key), "critical", "Coinbase API key required."))
            checks.append(self._check("coinbase_live_secret", bool(settings.coinbase_exchange_api_secret), "critical", "Coinbase API secret required."))
            checks.append(self._check("coinbase_live_passphrase", bool(settings.coinbase_exchange_passphrase), "critical", "Coinbase passphrase required."))
            checks.append(self._check("live_order_kill_switch_default", settings.coinbase_live_order_kill_switch, "warning", "COINBASE_LIVE_ORDER_KILL_SWITCH should remain true outside approved execution windows."))

        failed_critical = [check for check in checks if not check["passed"] and check["severity"] == "critical"]
        failed_warning = [check for check in checks if not check["passed"] and check["severity"] == "warning"]
        status = "ready" if not failed_critical and not failed_warning else "degraded" if not failed_critical else "blocked"
        if strict and failed_warning and not failed_critical:
            status = "blocked"
        return {
            "status": status,
            "strict": strict,
            "settings": settings.redacted_report(),
            "checks": checks,
            "summary": {"total": len(checks), "failed_critical": len(failed_critical), "failed_warning": len(failed_warning)},
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
        return {"status": status, "environment": environment, "database": database, "checked_at": self.utc_now()}
