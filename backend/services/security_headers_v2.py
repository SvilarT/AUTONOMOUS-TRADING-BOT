from starlette.middleware.base import BaseHTTPMiddleware

from runtime_config import DEBUG


class SecurityHeadersMiddlewareV2(BaseHTTPMiddleware):
    """Adds conservative browser security headers to every response."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")

        if not DEBUG:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
            response.headers.setdefault("Pragma", "no-cache")

        return response
