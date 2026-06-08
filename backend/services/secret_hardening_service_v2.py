import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

from services.settings_v2 import SettingsV2, TradingMode


SENSITIVE_NAME_PATTERNS = (
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSPHRASE",
    "PRIVATE",
    "API_KEY",
    "ACCESS_KEY",
    "AUTH",
    "WEBHOOK",
)

DANGEROUS_SECRET_VALUES = {
    "",
    "secret",
    "password",
    "changeme",
    "change-me",
    "replace-me",
    "test",
    "demo",
    "local-debug-placeholder",
}


@dataclass(frozen=True)
class HardeningCheck:
    name: str
    passed: bool
    severity: str
    detail: str
    observed: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "name": self.name,
            "passed": self.passed,
            "severity": self.severity,
            "detail": self.detail,
        }
        if self.observed is not None:
            payload["observed"] = self.observed
        return payload


class SecretHardeningServiceV2:
    """Credential and live-execution posture checks for production readiness.

    Exchange-side API permissions cannot be inferred reliably from local
    configuration. The runtime therefore requires explicit operator attestations
    before live-trading mode may boot. Sensitive settings may be delivered through
    mounted ``*_FILE`` paths supplied by a secret manager.
    """

    @staticmethod
    def is_sensitive_name(name: str) -> bool:
        upper = str(name or "").upper()
        return any(pattern in upper for pattern in SENSITIVE_NAME_PATTERNS)

    @staticmethod
    def fingerprint(value: str) -> str:
        import hashlib

        if not value:
            return ""
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]

    @classmethod
    def redact_value(cls, value: Any) -> Any:
        if value is None:
            return None
        text = str(value)
        if not text:
            return ""
        if len(text) <= 4:
            return "***"
        return f"{text[:2]}***{text[-2:]}"

    @classmethod
    def redact_mapping(cls, values: Mapping[str, Any]) -> Dict[str, Any]:
        redacted: Dict[str, Any] = {}
        for key, value in values.items():
            if cls.is_sensitive_name(key):
                redacted[key] = {
                    "configured": bool(value),
                    "length": len(str(value or "")),
                    "fingerprint": cls.fingerprint(str(value or "")),
                    "redacted": cls.redact_value(value),
                }
            else:
                redacted[key] = value
        return redacted

    @classmethod
    def redact_text(cls, text: str, secrets: Iterable[str]) -> str:
        redacted = str(text or "")
        for secret in sorted({str(item) for item in secrets if item}, key=len, reverse=True):
            if len(secret) < 4:
                continue
            redacted = redacted.replace(secret, cls.redact_value(secret))
        redacted = re.sub(
            r"(?i)(api[_-]?key|secret|token|password|passphrase|webhook)\s*[:=]\s*[^\s,'\"]+",
            r"\1=***",
            redacted,
        )
        return redacted

    @staticmethod
    def env_present(name: str, env: Optional[Mapping[str, str]] = None) -> bool:
        source = os.environ if env is None else env
        return bool(source.get(name))

    @classmethod
    def secret_file_sources(cls, env: Mapping[str, str]) -> Dict[str, bool]:
        names = (
            "JWT_SECRET_FILE",
            "COINBASE_EXCHANGE_API_KEY_FILE",
            "COINBASE_EXCHANGE_API_SECRET_FILE",
            "COINBASE_EXCHANGE_PASSPHRASE_FILE",
            "LIVE_APPROVAL_TOKEN_FILE",
            "LIVE_TOTP_SECRET_FILE",
            "OPS_ALERT_WEBHOOK_URL_FILE",
        )
        return {name: bool(env.get(name)) for name in names}

    @classmethod
    def credential_report(cls, settings: SettingsV2) -> Dict[str, Any]:
        return {
            "coinbase_exchange_url": settings.coinbase_exchange_url,
            "api_key": {
                "configured": bool(settings.coinbase_exchange_api_key),
                "length": len(settings.coinbase_exchange_api_key or ""),
                "fingerprint": cls.fingerprint(settings.coinbase_exchange_api_key),
            },
            "api_secret": {
                "configured": bool(settings.coinbase_exchange_api_secret),
                "length": len(settings.coinbase_exchange_api_secret or ""),
                "fingerprint": cls.fingerprint(settings.coinbase_exchange_api_secret),
            },
            "passphrase": {
                "configured": bool(settings.coinbase_exchange_passphrase),
                "length": len(settings.coinbase_exchange_passphrase or ""),
                "fingerprint": cls.fingerprint(settings.coinbase_exchange_passphrase),
            },
        }

    @classmethod
    def evaluate(
        cls,
        settings: Optional[SettingsV2] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        settings = settings or SettingsV2.from_env()
        source = os.environ if env is None else env
        checks: List[HardeningCheck] = []
        is_live_trading = settings.trading_mode == TradingMode.LIVE_TRADING

        coinbase_fields = {
            "COINBASE_EXCHANGE_API_KEY": settings.coinbase_exchange_api_key,
            "COINBASE_EXCHANGE_API_SECRET": settings.coinbase_exchange_api_secret,
            "COINBASE_EXCHANGE_PASSPHRASE": settings.coinbase_exchange_passphrase,
        }
        configured_coinbase = [name for name, value in coinbase_fields.items() if value]
        missing_coinbase = [name for name, value in coinbase_fields.items() if not value]
        coinbase_required = settings.trading_mode in {TradingMode.LIVE_READONLY, TradingMode.LIVE_TRADING}

        checks.append(HardeningCheck(
            name="coinbase_credentials_present_when_live_mode",
            passed=not coinbase_required or not missing_coinbase,
            severity="critical",
            detail="Coinbase key, secret, and passphrase must be configured for live-readonly or live-trading modes.",
            observed={"configured": configured_coinbase, "missing": missing_coinbase, "trading_mode": settings.trading_mode.value},
        ))

        dangerous = [name for name, value in coinbase_fields.items() if value and str(value).strip().lower() in DANGEROUS_SECRET_VALUES]
        checks.append(HardeningCheck(
            name="coinbase_credentials_not_placeholder_values",
            passed=not dangerous,
            severity="critical",
            detail="Configured Coinbase credential variables must not use placeholder, demo, or obvious test values.",
            observed={"dangerous_fields": dangerous},
        ))

        checks.append(HardeningCheck(
            name="jwt_secret_production_strength",
            passed=settings.debug or (bool(settings.jwt_secret) and len(settings.jwt_secret) >= 32 and settings.jwt_secret.strip().lower() not in DANGEROUS_SECRET_VALUES),
            severity="critical",
            detail="JWT_SECRET must be non-placeholder and at least 32 characters when DEBUG=False.",
            observed={"debug": settings.debug, "configured": bool(settings.jwt_secret), "length": len(settings.jwt_secret or "")},
        ))

        checks.append(HardeningCheck(
            name="live_trading_requires_explicit_live_mode",
            passed=not settings.live_trading_enabled or is_live_trading,
            severity="critical",
            detail="LIVE_TRADING_ENABLED may only be true when TRADING_MODE=live-trading.",
            observed={"trading_mode": settings.trading_mode.value, "live_trading_enabled": settings.live_trading_enabled},
        ))

        checks.append(HardeningCheck(
            name="live_execution_adapter_locked",
            passed=not is_live_trading or settings.live_execution_adapter == "coinbase_exchange_v2",
            severity="critical",
            detail="LIVE_EXECUTION_ADAPTER must be coinbase_exchange_v2 in live-trading mode.",
            observed={"execution_adapter": settings.live_execution_adapter},
        ))

        checks.append(HardeningCheck(
            name="manual_approval_boundary_configured",
            passed=not is_live_trading or not settings.live_manual_approval_required or settings.live_signed_approval_required or bool(settings.live_approval_token),
            severity="critical",
            detail="Manual live approval requires signed one-time challenges or a configured legacy approval token.",
            observed={
                "manual_approval_required": settings.live_manual_approval_required,
                "signed_approval_required": settings.live_signed_approval_required,
                "legacy_token_configured": bool(settings.live_approval_token),
            },
        ))

        checks.append(HardeningCheck(
            name="mfa_live_session_elevation_configured",
            passed=not is_live_trading or (settings.live_mfa_required and bool(settings.live_totp_secret)),
            severity="critical",
            detail="Live-trading mode requires TOTP-backed short-lived execution-session elevation.",
            observed={"mfa_required": settings.live_mfa_required, "totp_secret_configured": bool(settings.live_totp_secret)},
        ))

        checks.append(HardeningCheck(
            name="live_request_abuse_controls_enabled",
            passed=not is_live_trading or (settings.live_rate_limiting_enabled and settings.live_idempotency_required),
            severity="critical",
            detail="Mongo-backed live rate limiting and idempotency enforcement must remain enabled.",
            observed={"rate_limiting_enabled": settings.live_rate_limiting_enabled, "idempotency_required": settings.live_idempotency_required},
        ))

        checks.append(HardeningCheck(
            name="live_api_worker_process_separation",
            passed=not is_live_trading or (settings.runtime_role.value == "api" and not settings.api_embed_bot_manager),
            severity="critical",
            detail="The live-trading API must run with RUNTIME_ROLE=api and API_EMBED_BOT_MANAGER=False.",
            observed={"runtime_role": settings.runtime_role.value, "api_embed_bot_manager": settings.api_embed_bot_manager},
        ))

        checks.append(HardeningCheck(
            name="live_ops_admin_configured",
            passed=not is_live_trading or (settings.ops_admin_enabled and bool(settings.ops_admin_emails)),
            severity="critical",
            detail="Live-trading mode requires an enabled ops-admin emergency boundary and at least one admin email.",
            observed={"ops_admin_enabled": settings.ops_admin_enabled, "ops_admin_email_count": len(settings.ops_admin_emails)},
        ))

        attestation_values = {
            "operator_attestation_accepted": settings.live_operator_attestation_accepted,
            "withdrawals_disabled_confirmed": settings.live_credentials_withdrawals_disabled_confirmed,
            "transfers_disabled_confirmed": settings.live_credentials_transfers_disabled_confirmed,
            "ip_allowlist_confirmed": settings.live_credentials_ip_allowlist_confirmed,
        }
        checks.append(HardeningCheck(
            name="exchange_credential_boundary_attested",
            passed=not is_live_trading or all(attestation_values.values()),
            severity="critical",
            detail="Operator attestation must confirm no withdrawals, no transfers, and an API-key IP allowlist before live-trading startup.",
            observed=attestation_values,
        ))

        checks.append(HardeningCheck(
            name="live_order_notional_cap_is_tiny",
            passed=float(settings.live_max_order_notional_usd) <= 25.0,
            severity="critical",
            detail="Manual live pilot max notional should remain tiny until after repeated reviewed pilots.",
            observed={"live_max_order_notional_usd": settings.live_max_order_notional_usd},
        ))

        checks.append(HardeningCheck(
            name="kill_switch_defaults_safe_when_not_live_trading",
            passed=is_live_trading or settings.coinbase_live_order_kill_switch is True,
            severity="critical",
            detail="COINBASE_LIVE_ORDER_KILL_SWITCH must stay true outside an explicitly approved live submit window.",
            observed={"trading_mode": settings.trading_mode.value, "coinbase_live_order_kill_switch": settings.coinbase_live_order_kill_switch},
        ))

        checks.append(HardeningCheck(
            name="wildcard_cors_not_enabled_in_production",
            passed=settings.debug or "*" not in settings.cors_origins,
            severity="critical",
            detail="Wildcard CORS is only acceptable in local debug mode.",
            observed={"debug": settings.debug, "cors_origins": settings.cors_origins},
        ))

        accidental_frontend_secrets = [name for name in source.keys() if str(name).startswith("REACT_APP_") and cls.is_sensitive_name(name)]
        checks.append(HardeningCheck(
            name="no_frontend_prefixed_secrets",
            passed=not accidental_frontend_secrets,
            severity="critical",
            detail="Secrets must never use REACT_APP_ prefixes because frontend build variables are public.",
            observed={"frontend_secret_like_variables": accidental_frontend_secrets},
        ))

        checks.append(HardeningCheck(
            name="ops_alert_webhook_configured_for_live_trading",
            passed=not is_live_trading or bool(settings.ops_alert_webhook_url),
            severity="warning",
            detail="Configure OPS_ALERT_WEBHOOK_URL or OPS_ALERT_WEBHOOK_URL_FILE so persisted critical alerts are forwarded during live windows.",
            observed={"webhook_configured": bool(settings.ops_alert_webhook_url)},
        ))

        blockers = [check.to_dict() for check in checks if check.severity == "critical" and not check.passed]
        warnings = [check.to_dict() for check in checks if check.severity == "warning" and not check.passed]
        return {
            "status": "hardened" if not blockers else "not_hardened",
            "ready_for_live_credentials": not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "checks": [check.to_dict() for check in checks],
            "credentials": cls.credential_report(settings),
            "secret_file_sources": cls.secret_file_sources(source),
            "redacted_settings": settings.redacted_report(),
        }
