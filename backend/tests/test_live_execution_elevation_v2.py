import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "test-secret-for-elevation-more-than-thirty-two-characters")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("RUNTIME_ROLE", "api")
os.environ.setdefault("API_EMBED_BOT_MANAGER", "false")

from services.live_execution_elevation_service_v2 import LiveExecutionElevationError, LiveExecutionElevationServiceV2


def test_totp_is_deterministic_and_accepts_small_clock_drift():
    secret = "JBSWY3DPEHPK3PXP"
    timestamp = 1_700_000_000
    code = LiveExecutionElevationServiceV2.totp_code(secret, timestamp=timestamp)
    assert len(code) == 6
    assert code.isdigit()
    assert LiveExecutionElevationServiceV2.verify_totp(secret, code, timestamp=timestamp)
    assert LiveExecutionElevationServiceV2.verify_totp(secret, code, timestamp=timestamp + 30)
    assert not LiveExecutionElevationServiceV2.verify_totp(secret, "000000", timestamp=timestamp)


def test_totp_rejects_invalid_base32_secret():
    try:
        LiveExecutionElevationServiceV2.totp_code("not-valid-!", timestamp=1_700_000_000)
    except LiveExecutionElevationError as exc:
        assert "base32" in str(exc)
    else:
        raise AssertionError("invalid base32 secret should fail closed")
