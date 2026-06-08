import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "test-secret-for-settings-more-than-thirty-two-characters")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("RUNTIME_ROLE", "api")
os.environ.setdefault("API_EMBED_BOT_MANAGER", "false")

import pytest
from pydantic import ValidationError

from services.settings_v2 import RuntimeRole, SettingsV2, TradingMode, resolve_secret_env


LIVE_CONFIG = {
    "debug": False,
    "jwt_secret": "x" * 40,
    "cors_origins": ["https://example.com"],
    "trading_mode": TradingMode.LIVE_TRADING,
    "live_trading_enabled": True,
    "live_execution_adapter": "coinbase_exchange_v2",
    "live_manual_approval_required": True,
    "live_signed_approval_required": True,
    "live_mfa_required": True,
    "live_totp_secret": "JBSWY3DPEHPK3PXP",
    "live_rate_limiting_enabled": True,
    "live_idempotency_required": True,
    "runtime_role": RuntimeRole.API,
    "api_embed_bot_manager": False,
    "ops_admin_enabled": True,
    "ops_admin_emails": {"ops@example.com"},
    "live_operator_attestation_accepted": True,
    "live_credentials_withdrawals_disabled_confirmed": True,
    "live_credentials_transfers_disabled_confirmed": True,
    "live_credentials_ip_allowlist_confirmed": True,
}


def test_settings_redacted_report_never_exposes_secret_values():
    settings = SettingsV2(
        debug=False,
        jwt_secret="x" * 40,
        cors_origins=["https://example.com"],
        coinbase_exchange_api_key="key-value",
        coinbase_exchange_api_secret="secret-value",
        coinbase_exchange_passphrase="passphrase-value",
        live_approval_token="approval-value",
        live_totp_secret="totp-value",
        ops_alert_webhook_url="https://example.com/webhook-secret",
    )

    report = settings.redacted_report()
    rendered = str(report)

    assert "key-value" not in rendered
    assert "secret-value" not in rendered
    assert "passphrase-value" not in rendered
    assert "approval-value" not in rendered
    assert "totp-value" not in rendered
    assert "webhook-secret" not in rendered
    assert report["coinbase"]["api_key"]["configured"] is True
    assert report["coinbase"]["api_secret"]["redacted"] == "***"
    assert report["live_trading"]["approval_token"]["redacted"] == "***"
    assert report["live_trading"]["totp_secret"]["redacted"] == "***"


def test_settings_rejects_weak_production_jwt_secret():
    with pytest.raises(ValidationError):
        SettingsV2(debug=False, jwt_secret="short", cors_origins=["https://example.com"])


def test_settings_rejects_wildcard_cors_in_production():
    with pytest.raises(ValidationError):
        SettingsV2(debug=False, jwt_secret="x" * 40, cors_origins=["*"])


def test_settings_accepts_debug_wildcard_cors():
    settings = SettingsV2(debug=True, jwt_secret="local-debug-placeholder", cors_origins=["*"])
    assert settings.cors_origins == ["*"]


def test_settings_rejects_live_enabled_outside_live_trading_mode():
    with pytest.raises(ValidationError):
        SettingsV2(
            debug=False,
            jwt_secret="x" * 40,
            cors_origins=["https://example.com"],
            trading_mode=TradingMode.PAPER,
            live_trading_enabled=True,
        )


def test_settings_requires_live_adapter():
    with pytest.raises(ValidationError):
        SettingsV2(**{**LIVE_CONFIG, "live_execution_adapter": "disabled"})


def test_settings_requires_mfa_totp_secret():
    with pytest.raises(ValidationError):
        SettingsV2(**{**LIVE_CONFIG, "live_totp_secret": ""})


def test_settings_rejects_embedded_worker_in_live_mode():
    with pytest.raises(ValidationError):
        SettingsV2(**{**LIVE_CONFIG, "runtime_role": RuntimeRole.ALL, "api_embed_bot_manager": True})


def test_settings_requires_operator_credential_attestations():
    with pytest.raises(ValidationError):
        SettingsV2(**{**LIVE_CONFIG, "live_credentials_withdrawals_disabled_confirmed": False})


def test_settings_accepts_valid_live_trading_configuration():
    settings = SettingsV2(**LIVE_CONFIG)
    assert settings.trading_mode == TradingMode.LIVE_TRADING
    assert settings.live_trading_enabled is True
    assert settings.runtime_role == RuntimeRole.API
    assert settings.api_embed_bot_manager is False


def test_settings_runtime_role_values():
    settings = SettingsV2(debug=True, runtime_role=RuntimeRole.WORKER, jwt_secret="debug", cors_origins=["http://localhost:3000"])
    assert settings.runtime_role == RuntimeRole.WORKER


def test_resolve_secret_env_reads_mounted_file(monkeypatch, tmp_path):
    secret_file = tmp_path / "jwt-secret"
    secret_file.write_text("file-mounted-secret\n", encoding="utf-8")
    monkeypatch.delenv("TEST_MOUNTED_SECRET", raising=False)
    monkeypatch.setenv("TEST_MOUNTED_SECRET_FILE", str(secret_file))
    assert resolve_secret_env("TEST_MOUNTED_SECRET") == "file-mounted-secret"


def test_resolve_secret_env_prefers_mounted_file(monkeypatch, tmp_path):
    secret_file = tmp_path / "coinbase-secret"
    secret_file.write_text("from-file", encoding="utf-8")
    monkeypatch.setenv("TEST_SECRET_SOURCE", "from-env")
    monkeypatch.setenv("TEST_SECRET_SOURCE_FILE", str(secret_file))
    assert resolve_secret_env("TEST_SECRET_SOURCE") == "from-file"
