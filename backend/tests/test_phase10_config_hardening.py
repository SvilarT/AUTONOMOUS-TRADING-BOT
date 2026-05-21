from services.secret_hardening_service_v2 import SecretHardeningServiceV2
from services.settings_v2 import SettingsV2


def test_secret_hardening_service_imports_and_reports_default_state():
    settings = SettingsV2(debug=True, jwt_secret="debug", cors_origins=["http://localhost:3000"])

    report = SecretHardeningServiceV2.evaluate(settings=settings, env={})

    assert "status" in report
    assert "checks" in report
    assert "redacted_settings" in report


def test_redact_text_removes_known_sensitive_value():
    raw = "value one-two-three appears here"
    redacted = SecretHardeningServiceV2.redact_text(raw, ["one-two-three"])

    assert "one-two-three" not in redacted
    assert "***" in redacted
