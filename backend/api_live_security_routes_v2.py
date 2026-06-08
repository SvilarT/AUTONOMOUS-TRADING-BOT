from typing import Optional

from fastapi import Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from api_routes_v2 import api_router
from app_state import db, pwd_context
from auth_core import get_current_user
from runtime_config import DEBUG, OPS_ADMIN_EMAILS, OPS_ADMIN_ENABLED
from services.authz_dependencies_v2 import require_live_execute, require_ops_halt
from services.live_circuit_breaker_service_v2 import LiveCircuitBreakerServiceV2
from services.live_execution_elevation_service_v2 import LiveExecutionElevationError, LiveExecutionElevationServiceV2


class LiveElevationRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
    totp_code: Optional[str] = Field(default=None, max_length=12)


class LiveHaltRequest(BaseModel):
    reason: str = Field(default="operator emergency live halt", min_length=3, max_length=500)


class LiveHaltResetRequest(BaseModel):
    user_id: Optional[str] = None
    reason: str = Field(default="operator reviewed and reset live halt", min_length=3, max_length=500)


async def require_ops_admin(current_user: dict = Depends(get_current_user)):
    if DEBUG and not OPS_ADMIN_ENABLED:
        return current_user
    email = str(current_user.get("email", "")).lower().strip()
    if OPS_ADMIN_ENABLED and email in OPS_ADMIN_EMAILS:
        return current_user
    raise HTTPException(status_code=403, detail="Admin privileges required")


def request_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@api_router.post("/live-auth/elevate")
async def elevate_live_execution_session(
    payload: LiveElevationRequest,
    request: Request,
    current_user: dict = Depends(require_live_execute),
):
    try:
        return await LiveExecutionElevationServiceV2(db, pwd_context).elevate(
            user=current_user,
            password=payload.password,
            totp_code=payload.totp_code,
            request_ip=request_ip(request),
        )
    except LiveExecutionElevationError as exc:
        await LiveCircuitBreakerServiceV2(db).record_event(
            user_id=current_user["id"],
            event_type="elevation_failure",
            message=str(exc),
            severity="warning",
            context={"request_ip": request_ip(request)},
        )
        raise HTTPException(status_code=403, detail=str(exc))


@api_router.get("/live-auth/status")
async def live_execution_session_status(
    request: Request,
    x_live_session_token: Optional[str] = Header(default=None, alias="X-Live-Session-Token"),
    current_user: dict = Depends(require_live_execute),
):
    if not x_live_session_token:
        return {"active": False}
    try:
        result = await LiveExecutionElevationServiceV2(db, pwd_context).verify(
            user_id=current_user["id"],
            token=x_live_session_token,
            request_ip=request_ip(request),
        )
        return {"active": True, **result}
    except LiveExecutionElevationError:
        return {"active": False}


@api_router.post("/live-auth/revoke")
async def revoke_live_execution_session(
    x_live_session_token: Optional[str] = Header(default=None, alias="X-Live-Session-Token"),
    current_user: dict = Depends(get_current_user),
):
    revoked = await LiveExecutionElevationServiceV2(db, pwd_context).revoke(user_id=current_user["id"], token=x_live_session_token)
    return {"status": "revoked", "revoked_count": revoked}


@api_router.post("/ops/live-halts/emergency")
async def emergency_live_halt(payload: LiveHaltRequest, current_user: dict = Depends(require_ops_halt)):
    halt = await LiveCircuitBreakerServiceV2(db).trip(
        user_id=current_user["id"],
        reason=payload.reason,
        event_type="operator_emergency_halt",
        context={"triggered_by": current_user["id"]},
    )
    return {"status": "halted", "halt": halt}


@api_router.get("/ops/live-halts")
async def list_live_halts(current_user: dict = Depends(require_ops_halt), limit: int = 100):
    halts = await db.live_halts.find(
        {"$or": [{"scope": "global"}, {"scope": "user", "user_id": current_user["id"]}]},
        {"_id": 0},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    return {"halts": halts}


@api_router.post("/ops/live-halts/reset")
async def reset_live_halts(payload: LiveHaltResetRequest, current_user: dict = Depends(require_ops_admin)):
    target_user_id = payload.user_id or current_user["id"]
    reset_count = await LiveCircuitBreakerServiceV2(db).reset_user_halts(
        user_id=target_user_id,
        reset_by=current_user["id"],
        reason=payload.reason,
    )
    return {"status": "reset", "user_id": target_user_id, "reset_count": reset_count}
