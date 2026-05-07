import json
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app_state import db
from auth_core import verify_token
from services.api_errors_v2 import error_envelope
from services.authorization_v2 import Scope, effective_scopes, has_scope
from services.request_context_v2 import get_request_id


class ScopeEnforcementMiddlewareV2(BaseHTTPMiddleware):
    """Central authorization choke point for live and privileged ops routes."""

    def required_scope_for(self, method: str, path: str, body: Optional[dict]) -> Optional[str]:
        if path.startswith("/api/live-readonly/"):
            return Scope.TRADING_LIVE_PREVIEW.value

        if path in {"/api/live-trading/gate", "/api/live-trading/audits"}:
            return Scope.TRADING_LIVE_PREVIEW.value

        if path in {"/api/live-trading/market-buy", "/api/live-trading/market-sell"} and method == "POST":
            if body and body.get("dry_run") is False:
                return Scope.TRADING_LIVE_EXECUTE.value
            return Scope.TRADING_LIVE_PREVIEW.value

        if path == "/api/ops/readiness":
            return Scope.OPS_READINESS.value

        if path == "/api/ops/indexes/ensure":
            return Scope.OPS_INDEXES.value

        if path == "/api/ops/emergency-halt":
            return Scope.OPS_HALT.value

        return None

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

    async def load_user(self, request: Request) -> Optional[dict]:
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        payload = verify_token(token)
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

        request.state.authorized_user = user
        return await call_next(request)
