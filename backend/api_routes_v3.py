from api_routes_v2 import api_router
from auth_core import get_current_user
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from services.alert_service import AlertService
from services.backtesting_service_v2 import BacktestConfig, BacktestingServiceV2
from services.market_data_service import MarketDataService, MarketDataUnavailable
from services.trading_mode_v2 import TradingModeService
from app_state import db


class BacktestRequest(BaseModel):
    symbol: str = "BTC-USD"
    timeframe: str = "1h"
    periods: int = Field(default=300, ge=30, le=300)
    initial_cash: float = Field(default=10000.0, gt=0)
    fee_bps: float = Field(default=10.0, ge=0)
    slippage_bps: float = Field(default=5.0, ge=0)
    max_position_pct: float = Field(default=0.30, gt=0, le=1.0)
    max_drawdown_pct: float = Field(default=0.10, gt=0, le=1.0)
    max_daily_loss_pct: float = Field(default=0.05, gt=0, le=1.0)
    fast_window: int = Field(default=10, ge=2, le=100)
    slow_window: int = Field(default=30, ge=3, le=200)
    min_trade_notional: float = Field(default=10.0, ge=0)

    def to_config(self) -> BacktestConfig:
        return BacktestConfig(
            initial_cash=self.initial_cash,
            fee_bps=self.fee_bps,
            slippage_bps=self.slippage_bps,
            max_position_pct=self.max_position_pct,
            max_drawdown_pct=self.max_drawdown_pct,
            max_daily_loss_pct=self.max_daily_loss_pct,
            fast_window=self.fast_window,
            slow_window=self.slow_window,
            min_trade_notional=self.min_trade_notional,
        )


class WalkForwardRequest(BacktestRequest):
    train_periods: int = Field(default=120, ge=30, le=300)
    test_periods: int = Field(default=60, ge=30, le=300)
    periods: int = Field(default=300, ge=90, le=300)


@api_router.get("/trading-mode")
async def get_trading_mode(current_user: dict = Depends(get_current_user)):
    return TradingModeService().describe()


@api_router.get("/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user), limit: int = 100):
    return {"alerts": await AlertService(db).list_alerts(current_user["id"], limit=limit)}


@api_router.post("/backtests/run")
async def run_backtest(request: BacktestRequest, current_user: dict = Depends(get_current_user)):
    try:
        candles = await MarketDataService(db=db).get_candles(
            request.symbol,
            timeframe=request.timeframe,
            periods=request.periods,
        )
    except (ValueError, MarketDataUnavailable) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = BacktestingServiceV2().run_moving_average_backtest(candles, request.to_config())
    result["user_id"] = current_user["id"]
    result["symbol"] = request.symbol
    result["timeframe"] = request.timeframe
    return result


@api_router.post("/backtests/walk-forward")
async def run_walk_forward(request: WalkForwardRequest, current_user: dict = Depends(get_current_user)):
    try:
        candles = await MarketDataService(db=db).get_candles(
            request.symbol,
            timeframe=request.timeframe,
            periods=request.periods,
        )
    except (ValueError, MarketDataUnavailable) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = BacktestingServiceV2().walk_forward_validation(
        candles,
        train_periods=request.train_periods,
        test_periods=request.test_periods,
        config=request.to_config(),
    )
    result["user_id"] = current_user["id"]
    result["symbol"] = request.symbol
    result["timeframe"] = request.timeframe
    return result
