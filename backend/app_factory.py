from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware

from api_routes import api_router
from app_state import lifespan
from runtime_config import CORS_ORIGINS
from services.api_errors_v2 import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from services.request_context_v2 import RequestContextMiddlewareV2
from services.scope_enforcement_middleware_v2 import ScopeEnforcementMiddlewareV2
from services.security_headers_v2 import SecurityHeadersMiddlewareV2


def create_app() -> FastAPI:
    app = FastAPI(title="Autonomous Trading Bot", lifespan=lifespan)

    @app.get("/")
    async def root():
        return {"status": "ok", "service": "Autonomous Trading Bot"}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "service": "Autonomous Trading Bot"}

    @app.get("/readyz")
    async def readyz():
        return {"status": "ready", "service": "Autonomous Trading Bot"}

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(api_router)
    app.add_middleware(SecurityHeadersMiddlewareV2)
    app.add_middleware(ScopeEnforcementMiddlewareV2)
    app.add_middleware(RequestContextMiddlewareV2)
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    return app
