import os

os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "test-secret-for-runtime-role-tests")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import pytest

from runtime_config import RuntimeRole, parse_runtime_role


def test_parse_runtime_role_accepts_supported_roles():
    assert parse_runtime_role("api") == RuntimeRole.API
    assert parse_runtime_role("worker") == RuntimeRole.WORKER
    assert parse_runtime_role("all") == RuntimeRole.ALL
    assert parse_runtime_role("indexes") == RuntimeRole.INDEXES


def test_parse_runtime_role_normalizes_case_and_whitespace():
    assert parse_runtime_role(" Worker ") == RuntimeRole.WORKER


def test_parse_runtime_role_rejects_invalid_role():
    with pytest.raises(RuntimeError):
        parse_runtime_role("live-autonomous")
