from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api_routes import api_router
from app_state import db, lifespan
from runtime_config import CORS_ORIGINS
from services.operational_readiness_v2 import OperationalReadinessServiceV2


def create_app() -> FastAPI:
    app = FastAPI(title="Autonomous Trading Bot", lifespan=lifespan)

    @app.get("/")
    async def root():
        return {"status": "ok", "service": "Autonomous Trading Bot"}

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "service": "Autonomous Trading Bot"}

    @app.get("/readyz")
    async def readyz(strict: bool = False):
        return await OperationalReadinessServiceV2().readiness(db, strict=strict)

    app.include_router(api_router)
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    return app
