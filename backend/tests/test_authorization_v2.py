import pytest
from fastapi import HTTPException

from services.authorization_v2 import Role, Scope, effective_scopes, has_scope, public_user
from services.authz_dependencies_v2 import require_ops_indexes


def test_default_user_gets_safe_baseline_scopes_only():
    user = {"id": "user-1", "email": "user@example.com"}
    scopes = effective_scopes(user)

    assert Scope.TRADING_PAPER.value in scopes
    assert Scope.TRADING_LIVE_PREVIEW.value in scopes
    assert Scope.OPS_READINESS.value in scopes
    assert Scope.OPS_HALT.value in scopes
    assert Scope.TRADING_LIVE_EXECUTE.value not in scopes
    assert Scope.OPS_INDEXES.value not in scopes


def test_trader_role_adds_live_execute_scope():
    user = {"id": "user-1", "email": "user@example.com", "roles": [Role.TRADER.value]}

    assert has_scope(user, Scope.TRADING_LIVE_EXECUTE.value) is True
    assert has_scope(user, Scope.OPS_INDEXES.value) is False


def test_admin_role_has_all_scopes():
    user = {"id": "admin-1", "email": "admin@example.com", "roles": [Role.ADMIN.value]}

    assert has_scope(user, Scope.TRADING_LIVE_EXECUTE.value) is True
    assert has_scope(user, Scope.OPS_INDEXES.value) is True
    assert has_scope(user, Scope.ADMIN_ROLES.value) is True


def test_explicit_scope_grant_is_honored_without_admin_role():
    user = {"id": "ops-1", "email": "ops@example.com", "roles": [Role.USER.value], "scopes": [Scope.OPS_INDEXES.value]}

    assert has_scope(user, Scope.OPS_INDEXES.value) is True
    assert has_scope(user, Scope.TRADING_LIVE_EXECUTE.value) is False


def test_public_user_includes_effective_scopes_without_password_hash():
    user = {
        "id": "user-1",
        "email": "user@example.com",
        "password_hash": "must-not-leak",
        "roles": [Role.TRADER.value],
        "scopes": [],
    }
    payload = public_user(user)

    assert payload["id"] == "user-1"
    assert payload["email"] == "user@example.com"
    assert Role.TRADER.value in payload["roles"]
    assert Scope.TRADING_LIVE_EXECUTE.value in payload["scopes"]
    assert "password_hash" not in payload


@pytest.mark.asyncio
async def test_scope_dependency_blocks_missing_scope():
    dependency = require_ops_indexes
    user = {"id": "user-1", "email": "user@example.com", "roles": [Role.USER.value], "scopes": []}

    with pytest.raises(HTTPException) as exc:
        await dependency(user)

    assert exc.value.status_code == 403
    assert Scope.OPS_INDEXES.value in exc.value.detail


@pytest.mark.asyncio
async def test_scope_dependency_allows_admin_scope():
    dependency = require_ops_indexes
    user = {"id": "admin-1", "email": "admin@example.com", "roles": [Role.ADMIN.value], "scopes": []}

    allowed = await dependency(user)

    assert allowed["id"] == "admin-1"
