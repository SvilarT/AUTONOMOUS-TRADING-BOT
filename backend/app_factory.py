from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from api_routes import api_router
from app_state import lifespan
from runtime_config import CORS_ORIGINS


def create_app() -> FastAPI:
    app = FastAPI(title="Autonomous Trading Bot", lifespan=lifespan)

    @app.get("/")
    async def root():
        return {"status": "ok", "service": "Autonomous Trading Bot"}

    app.include_router(api_router)
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    return app
