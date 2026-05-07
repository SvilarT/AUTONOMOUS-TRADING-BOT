from fastapi import Depends, HTTPException

from auth_core import get_current_user
from services.authorization_v2 import Scope, effective_scopes, has_scope


async def current_user_with_defaults(current_user: dict = Depends(get_current_user)):
    if not current_user.get("roles"):
        current_user["roles"] = ["user"]
    if "scopes" not in current_user:
        current_user["scopes"] = []
    current_user["effective_scopes"] = sorted(effective_scopes(current_user))
    return current_user


def require_scope(required_scope: str):
    async def dependency(current_user: dict = Depends(current_user_with_defaults)):
        if not has_scope(current_user, required_scope):
            raise HTTPException(status_code=403, detail=f"Missing required scope: {required_scope}")
        return current_user

    return dependency


require_live_preview = require_scope(Scope.TRADING_LIVE_PREVIEW.value)
require_live_execute = require_scope(Scope.TRADING_LIVE_EXECUTE.value)
require_ops_readiness = require_scope(Scope.OPS_READINESS.value)
require_ops_indexes = require_scope(Scope.OPS_INDEXES.value)
require_ops_halt = require_scope(Scope.OPS_HALT.value)
