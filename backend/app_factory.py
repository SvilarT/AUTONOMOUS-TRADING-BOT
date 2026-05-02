from fastapi import FastAPI
from api_routes import api_router
from app_state import lifespan


def create_app() -> FastAPI:
    app = FastAPI(title="Autonomous Trading Bot", lifespan=lifespan)

    @app.get("/")
    async def root():
        return {"status": "ok", "service": "Autonomous Trading Bot"}

    app.include_router(api_router)
    return app
