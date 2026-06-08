from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from services.api_errors_v2 import error_envelope
from services.browser_session_v2 import SESSION_COOKIE_NAME, bearer_token_from_request, csrf_tokens_match
from services.request_context_v2 import get_request_id


class CookieCSRFMiddlewareV2(BaseHTTPMiddleware):
    """Require double-submit CSRF validation for cookie-authenticated mutations."""

    EXEMPT_PATHS = {"/api/auth/login", "/api/auth/signup"}
    MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next):
        uses_cookie_session = bool(request.cookies.get(SESSION_COOKIE_NAME)) and not bearer_token_from_request(request)
        requires_csrf = request.method in self.MUTATION_METHODS and request.url.path not in self.EXEMPT_PATHS
        if uses_cookie_session and requires_csrf and not csrf_tokens_match(request):
            request_id = get_request_id()
            payload = error_envelope(
                code="FORBIDDEN",
                message="Valid X-CSRF-Token header required for cookie-authenticated mutation",
                request_id=request_id,
                details={"status_code": 403},
            )
            return JSONResponse(
                status_code=403,
                content=payload,
                headers={"X-Request-ID": request_id} if request_id else {},
            )
        return await call_next(request)
