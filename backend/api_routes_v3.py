from api_routes_v2 import api_router
from auth_core import get_current_user
from fastapi import Depends
from services.alert_service import AlertService
from services.trading_mode_v2 import TradingModeService
from app_state import db


@api_router.get("/trading-mode")
async def get_trading_mode(current_user: dict = Depends(get_current_user)):
    return TradingModeService().describe()


@api_router.get("/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user), limit: int = 100):
    return {"alerts": await AlertService(db).list_alerts(current_user["id"], limit=limit)}
