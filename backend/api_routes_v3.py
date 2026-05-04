from api_routes_v2 import api_router
from auth_core import get_current_user
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from services.alert_service import AlertService
from services.backtesting_service_v2 import BacktestConfig, BacktestingServiceV2
from services.coinbase_live_execution_adapter_v2 import CoinbaseLiveExecutionError
from services.coinbase_readonly_adapter_v2 import CoinbaseReadonlyError
from services.ledger_service_v2 import LedgerServiceV2
from services.live_readonly_service_v2 import LiveReadonlyServiceV2
from services.live_trading_gate_v2 import LiveTradingGateV2
from services.live_trading_service_v2 import LiveTradingServiceV2
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


class ReconciliationRequest(BaseModel):
    starting_cash: float = Field(default=10000.0, gt=0)


class LiveReadonlySymbolsRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["BTC-USD", "ETH-USD"])


class LiveMarketBuyRequest(BaseModel):
    symbol: str = "BTC-USD"
    notional_usd: float = Field(gt=0)
    approval_token: str | None = None
    dry_run: bool = True


class LiveMarketSellRequest(BaseModel):
    symbol: str = "BTC-USD"
    base_units: float = Field(gt=0)
    reference_price: float = Field(gt=0)
    approval_token: str | None = None
    dry_run: bool = True


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


@api_router.get("/ledger/entries")
async def get_ledger_entries(current_user: dict = Depends(get_current_user), limit: int = 250):
    return {"entries": await LedgerServiceV2(db).list_entries(current_user["id"], limit=limit)}


@api_router.post("/ledger/rebuild")
async def rebuild_ledger_state(request: ReconciliationRequest, current_user: dict = Depends(get_current_user)):
    return await LedgerServiceV2(db).rebuild_from_ledger(current_user["id"], starting_cash=request.starting_cash)


@api_router.post("/ledger/reconcile")
async def reconcile_ledger_state(request: ReconciliationRequest, current_user: dict = Depends(get_current_user)):
    return await LedgerServiceV2(db).reconcile(current_user["id"], starting_cash=request.starting_cash)


@api_router.post("/live-readonly/snapshot")
async def get_live_readonly_snapshot(request: LiveReadonlySymbolsRequest, current_user: dict = Depends(get_current_user)):
    try:
        return await LiveReadonlyServiceV2(db).snapshot(current_user["id"], symbols=request.symbols)
    except CoinbaseReadonlyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@api_router.post("/live-readonly/reconcile")
async def reconcile_live_readonly(request: LiveReadonlySymbolsRequest, current_user: dict = Depends(get_current_user)):
    try:
        return await LiveReadonlyServiceV2(db).compare_exchange_to_internal(current_user["id"], symbols=request.symbols)
    except CoinbaseReadonlyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@api_router.get("/live-readonly/orders")
async def get_live_readonly_orders(current_user: dict = Depends(get_current_user), status: str = "all", limit: int = 100):
    try:
        return await LiveReadonlyServiceV2(db).recent_orders(current_user["id"], status=status, limit=limit)
    except CoinbaseReadonlyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@api_router.get("/live-readonly/fills")
async def get_live_readonly_fills(current_user: dict = Depends(get_current_user), product_id: str | None = None, limit: int = 100):
    try:
        return await LiveReadonlyServiceV2(db).recent_fills(current_user["id"], product_id=product_id, limit=limit)
    except CoinbaseReadonlyError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@api_router.get("/live-trading/gate")
async def get_live_trading_gate(current_user: dict = Depends(get_current_user)):
    return LiveTradingGateV2().describe()


@api_router.post("/live-trading/market-buy")
async def live_market_buy(request: LiveMarketBuyRequest, current_user: dict = Depends(get_current_user)):
    try:
        return await LiveTradingServiceV2(db).place_market_buy(
            current_user["id"],
            request.symbol,
            request.notional_usd,
            approval_token=request.approval_token,
            dry_run=request.dry_run,
        )
    except CoinbaseLiveExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@api_router.post("/live-trading/market-sell")
async def live_market_sell(request: LiveMarketSellRequest, current_user: dict = Depends(get_current_user)):
    try:
        return await LiveTradingServiceV2(db).place_market_sell(
            current_user["id"],
            request.symbol,
            request.base_units,
            reference_price=request.reference_price,
            approval_token=request.approval_token,
            dry_run=request.dry_run,
        )
    except CoinbaseLiveExecutionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@api_router.get("/live-trading/audits")
async def get_live_order_audits(current_user: dict = Depends(get_current_user), limit: int = 100):
    return {"audits": await LiveTradingServiceV2(db).list_audits(current_user["id"], limit=limit)}
