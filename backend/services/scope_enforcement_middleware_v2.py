import json
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app_state import db, pwd_context
from auth_core import verify_token
from services.api_errors_v2 import error_envelope
from services.authorization_v2 import Scope, effective_scopes, has_scope
from services.browser_session_v2 import session_token_from_request
from services.live_approval_challenge_service_v2 import LiveApprovalChallengeError, LiveApprovalChallengeServiceV2
from services.live_circuit_breaker_service_v2 import LiveCircuitBreakerError, LiveCircuitBreakerServiceV2
from services.live_execution_elevation_service_v2 import LiveExecutionElevationError, LiveExecutionElevationServiceV2
from services.live_pre_submit_safety_service_v2 import LivePreSubmitSafetyServiceV2
from services.live_request_guard_v2 import LiveIdempotencyError, LiveRateLimitError, LiveRequestGuardV2
from services.request_context_v2 import get_request_id


class ScopeEnforcementMiddlewareV2(BaseHTTPMiddleware):
    """Central authorization and safety choke point for live and privileged ops routes."""

    LIVE_ORDER_PATHS = {"/api/live-trading/market-buy", "/api/live-trading/market-sell"}

    def required_scope_for(self, method: str, path: str, body: Optional[dict]) -> Optional[str]:
        if path.startswith("/api/live-readonly/"):
            return Scope.TRADING_LIVE_PREVIEW.value

        if path in {"/api/live-trading/gate", "/api/live-trading/audits", "/api/live-approvals"}:
            return Scope.TRADING_LIVE_PREVIEW.value

        if path in {"/api/live-approvals/challenge", "/api/live-auth/elevate", "/api/live-auth/status", "/api/live-auth/revoke"}:
            return Scope.TRADING_LIVE_EXECUTE.value

        if path in self.LIVE_ORDER_PATHS and method == "POST":
            if body and body.get("dry_run") is False:
                return Scope.TRADING_LIVE_EXECUTE.value
            return Scope.TRADING_LIVE_PREVIEW.value

        if path == "/api/ops/readiness":
            return Scope.OPS_READINESS.value

        if path == "/api/ops/indexes/ensure":
            return Scope.OPS_INDEXES.value

        if path == "/api/ops/emergency-halt" or path.startswith("/api/ops/live-halts"):
            return Scope.OPS_HALT.value

        return None

    @classmethod
    def is_non_dry_run_live_order(cls, method: str, path: str, body: Optional[dict]) -> bool:
        return method == "POST" and path in cls.LIVE_ORDER_PATHS and bool(body and body.get("dry_run") is False)

    @classmethod
    def is_rate_limited_live_mutation(cls, method: str, path: str, body: Optional[dict]) -> bool:
        if method != "POST":
            return False
        return path in {"/api/live-auth/elevate", "/api/live-approvals/challenge"} or cls.is_non_dry_run_live_order(method, path, body)

    @classmethod
    def requires_live_elevation(cls, method: str, path: str, body: Optional[dict]) -> bool:
        return path == "/api/live-approvals/challenge" or cls.is_non_dry_run_live_order(method, path, body)

    @staticmethod
    async def parse_json_body(request: Request) -> tuple[Optional[dict], bytes]:
        body_bytes = await request.body()
        if not body_bytes:
            return None, body_bytes
        try:
            parsed = json.loads(body_bytes.decode("utf-8"))
            return parsed if isinstance(parsed, dict) else None, body_bytes
        except json.JSONDecodeError:
            return None, body_bytes

    @staticmethod
    def restore_body(request: Request, body: bytes) -> None:
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request._receive = receive

    @staticmethod
    def auth_error(status_code: int, code: str, message: str) -> JSONResponse:
        request_id = get_request_id()
        return JSONResponse(
            status_code=status_code,
            content=error_envelope(code=code, message=message, request_id=request_id, details={"status_code": status_code}),
            headers={"X-Request-ID": request_id} if request_id else {},
        )

    @staticmethod
    def request_ip(request: Request) -> str:
        return request.client.host if request.client else "unknown"

    async def load_user(self, request: Request) -> Optional[dict]:
        token = session_token_from_request(request)
        payload = verify_token(token) if token else None
        if not payload or "user_id" not in payload:
            return None
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            return None
        if not user.get("roles"):
            user["roles"] = ["user"]
        if "scopes" not in user:
            user["scopes"] = []
        user["effective_scopes"] = sorted(effective_scopes(user))
        return user

    async def verify_live_approval(self, user: dict, path: str, body: dict) -> Optional[JSONResponse]:
        try:
            if path == "/api/live-trading/market-buy":
                await LiveApprovalChallengeServiceV2(db).verify_and_consume(
                    user_id=user["id"],
                    approval_token=body.get("approval_token"),
                    side="BUY",
                    symbol=body.get("symbol"),
                    notional_usd=body.get("notional_usd"),
                )
            else:
                await LiveApprovalChallengeServiceV2(db).verify_and_consume(
                    user_id=user["id"],
                    approval_token=body.get("approval_token"),
                    side="SELL",
                    symbol=body.get("symbol"),
                    base_units=body.get("base_units"),
                    reference_price=body.get("reference_price"),
                )
        except LiveApprovalChallengeError as exc:
            await self.record_circuit_event(user["id"], "approval_replay", str(exc), {"path": path})
            return self.auth_error(403, "FORBIDDEN", str(exc))
        return None

    async def verify_live_pre_submit_safety(self, user: dict) -> Optional[JSONResponse]:
        result = await LivePreSubmitSafetyServiceV2(db).safe_check(user["id"])
        if not result.get("allowed"):
            return self.auth_error(409, "CONFLICT", str(result.get("reason", "live pre-submit safety check failed")))
        return None

    async def verify_live_elevation(self, user: dict, request: Request) -> Optional[JSONResponse]:
        token = request.headers.get("X-Live-Session-Token")
        try:
            await LiveExecutionElevationServiceV2(db, pwd_context).verify(
                user_id=user["id"],
                token=token,
                request_ip=self.request_ip(request),
            )
        except LiveExecutionElevationError as exc:
            await self.record_circuit_event(user["id"], "elevation_failure", str(exc), {"path": request.url.path})
            return self.auth_error(403, "FORBIDDEN", str(exc))
        return None

    @staticmethod
    async def record_circuit_event(user_id: str, event_type: str, message: str, context: Optional[dict] = None) -> None:
        try:
            await LiveCircuitBreakerServiceV2(db).record_event(
                user_id=user_id,
                event_type=event_type,
                message=message,
                severity="warning",
                context=context or {},
            )
        except Exception:
            return

    @staticmethod
    def response_payload(body_bytes: bytes) -> Any:
        if not body_bytes:
            return {}
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"raw_response": body_bytes.decode("utf-8", errors="replace")}

    async def finalize_idempotent_response(self, guard: LiveRequestGuardV2, claim: dict, response: Response, user_id: str) -> Response:
        if hasattr(response, "body_iterator"):
            body_bytes = b"".join([chunk async for chunk in response.body_iterator])
        else:
            body_bytes = bytes(getattr(response, "body", b""))
        payload = self.response_payload(body_bytes)
        await guard.complete_idempotency(claim, status_code=response.status_code, response_body=payload)

        if response.status_code >= 500:
            await self.record_circuit_event(user_id, "adapter_error", "Live execution endpoint returned server error", {"status_code": response.status_code})
        elif isinstance(payload, dict) and str(payload.get("status", "")).lower() in {"rejected", "failed", "adapter_error"}:
            await self.record_circuit_event(user_id, "broker_rejection", "Live broker order returned a rejected or failed status", {"response": payload})

        headers = dict(response.headers)
        headers["X-Idempotent-Replay"] = "false"
        return Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
            background=response.background,
        )

    async def complete_error_response(self, guard: LiveRequestGuardV2, claim: dict, response: JSONResponse) -> JSONResponse:
        await guard.complete_idempotency(claim, status_code=response.status_code, response_body=self.response_payload(response.body))
        return response

    async def dispatch(self, request: Request, call_next):
        parsed_body = None
        raw_body = b""
        if request.method in {"POST", "PUT", "PATCH"}:
            parsed_body, raw_body = await self.parse_json_body(request)
            self.restore_body(request, raw_body)

        required_scope = self.required_scope_for(request.method, request.url.path, parsed_body)
        if not required_scope:
            return await call_next(request)

        user = await self.load_user(request)
        if not user:
            return self.auth_error(401, "UNAUTHORIZED", "Authentication required")

        if not has_scope(user, required_scope):
            return self.auth_error(403, "FORBIDDEN", f"Missing required scope: {required_scope}")

        guard = LiveRequestGuardV2(db)
        if self.is_rate_limited_live_mutation(request.method, request.url.path, parsed_body):
            try:
                await guard.enforce_rate_limits(user_id=user["id"], request_ip=self.request_ip(request), route=request.url.path)
            except LiveRateLimitError as exc:
                await self.record_circuit_event(user["id"], "rate_limit_violation", str(exc), {"path": request.url.path})
                return self.auth_error(429, "RATE_LIMITED", str(exc))

        if self.requires_live_elevation(request.method, request.url.path, parsed_body):
            elevation_error = await self.verify_live_elevation(user, request)
            if elevation_error:
                return elevation_error

        claim: dict = {"enabled": False, "claimed": False}
        if self.is_non_dry_run_live_order(request.method, request.url.path, parsed_body):
            try:
                claim = await guard.claim_idempotency(
                    user_id=user["id"],
                    key=request.headers.get("Idempotency-Key"),
                    method=request.method,
                    path=request.url.path,
                    body=parsed_body or {},
                )
            except LiveIdempotencyError as exc:
                await self.record_circuit_event(user["id"], "idempotency_violation", str(exc), {"path": request.url.path})
                return self.auth_error(409, "CONFLICT", str(exc))

            if claim.get("replay"):
                record = claim["record"]
                return JSONResponse(
                    status_code=int(record.get("response_status_code") or 200),
                    content=record.get("response_body") or {},
                    headers={"X-Idempotent-Replay": "true"},
                )

            try:
                await LiveCircuitBreakerServiceV2(db).assert_audit_chain(user["id"])
            except LiveCircuitBreakerError as exc:
                await guard.fail_idempotency(claim, reason=str(exc))
                return self.auth_error(409, "CONFLICT", str(exc))

            approval_error = await self.verify_live_approval(user, request.url.path, parsed_body or {})
            if approval_error:
                return await self.complete_error_response(guard, claim, approval_error)

            safety_error = await self.verify_live_pre_submit_safety(user)
            if safety_error:
                return await self.complete_error_response(guard, claim, safety_error)

        request.state.authorized_user = user
        response = await call_next(request)
        if claim.get("enabled") and claim.get("claimed"):
            return await self.finalize_idempotent_response(guard, claim, response, user["id"])
        return response
