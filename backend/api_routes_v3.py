from api_routes_v2 import api_router
from auth_core import get_current_user
from fastapi import Depends
from services.trading_mode_v2 import TradingModeService


@api_router.get("/trading-mode")
async def get_trading_mode(current_user: dict = Depends(get_current_user)):
    return TradingModeService().describe()
