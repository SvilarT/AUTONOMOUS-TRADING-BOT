from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app_state import db, logger
from auth_core import TokenResponse, UserCreate, UserLogin, get_current_user, login, signup
from services.advanced_risk_manager import AdvancedRiskManager
from services.market_data_service import MarketDataService

api_router = APIRouter(prefix="/api")


class BotConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    is_active: bool = False
    capital_floor: float = 0.97
    max_daily_loss: float = 0.015
    risk_target_vol: float = 0.10
    symbols: List[str] = Field(default_factory=lambda: ["BTC-USD", "ETH-USD"])
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup_route(user_data: UserCreate):
    return await signup(user_data)


@api_router.post("/auth/login", response_model=TokenResponse)
async def login_route(credentials: UserLogin):
    return await login(credentials)


@api_router.get("/trades")
async def get_trades(current_user: dict = Depends(get_current_user)):
    trades = await db.trades.find({"user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"trades": trades}


@api_router.get("/positions")
async def get_positions(current_user: dict = Depends(get_current_user)):
    positions = await db.positions.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(100)
    return {"positions": positions}


@api_router.get("/risk-metrics")
async def get_risk_metrics(current_user: dict = Depends(get_current_user)):
    metrics = await db.risk_metrics.find_one({"user_id": current_user["id"]}, {"_id": 0}, sort=[("timestamp", -1)])
    if not metrics:
        metrics = {
            "user_id": current_user["id"],
            "total_equity": 10000.0,
            "max_equity": 10000.0,
            "equity_floor": 9700.0,
            "current_drawdown": 0.0,
            "daily_pnl": 0.0,
            "positions_value": 0.0,
            "cash_balance": 10000.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await db.risk_metrics.insert_one(metrics)
        return metrics
    metrics.pop("_id", None)
    return metrics


@api_router.get("/bot-config")
async def get_bot_config(current_user: dict = Depends(get_current_user)):
    return await db.bot_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})


@api_router.post("/bot-config")
async def update_bot_config(config_update: BotConfig, current_user: dict = Depends(get_current_user)):
    config_dict = config_update.model_dump()
    config_dict["user_id"] = current_user["id"]
    config_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.bot_configs.update_one({"user_id": current_user["id"]}, {"$set": config_dict}, upsert=True)
    return {"status": "success", "config": config_dict}


@api_router.get("/market-analysis")
async def get_market_analysis(symbol: str = "BTC-USD", current_user: dict = Depends(get_current_user)):
    analysis = await db.market_analysis.find_one({"symbol": symbol}, {"_id": 0}, sort=[("timestamp", -1)])
    if not analysis:
        return {"message": "No analysis available yet"}
    return analysis


@api_router.get("/technical-indicators/{symbol}")
async def get_technical_indicators(symbol: str, current_user: dict = Depends(get_current_user)):
    analysis = await db.market_analysis.find_one({"symbol": symbol}, {"_id": 0}, sort=[("timestamp", -1)])
    if analysis and "technical_indicators" in analysis:
        return {
            "symbol": symbol,
            "technical_indicators": analysis["technical_indicators"],
            "technical_signals": analysis.get("technical_signals", {}),
            "timestamp": analysis.get("timestamp"),
        }
    return {"message": "No technical data available yet"}


@api_router.get("/market-data/{symbol}")
async def get_market_data(symbol: str, current_user: dict = Depends(get_current_user)):
    try:
        return await MarketDataService().get_current_price(symbol)
    except Exception as exc:
        logger.error("Error fetching market data: %s", exc)
        raise HTTPException(status_code=503, detail="Market data unavailable")


@api_router.post("/bot/start")
async def start_bot(current_user: dict = Depends(get_current_user)):
    await db.bot_configs.update_one(
        {"user_id": current_user["id"]},
        {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    logger.info("Bot activation requested for user %s", current_user["id"])
    return {"status": "Bot started", "is_active": True}


@api_router.post("/bot/stop")
async def stop_bot(current_user: dict = Depends(get_current_user)):
    await db.bot_configs.update_one(
        {"user_id": current_user["id"]},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    logger.info("Bot stop requested for user %s", current_user["id"])
    return {"status": "Bot stopped", "is_active": False}


@api_router.get("/risk/advanced-assessment")
async def get_advanced_risk_assessment(current_user: dict = Depends(get_current_user)):
    metrics = await db.risk_metrics.find_one({"user_id": current_user["id"]}, {"_id": 0}, sort=[("timestamp", -1)])
    positions = await db.positions.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(100)
    recent_trades = await db.trades.find({"user_id": current_user["id"]}, {"_id": 0}).sort("created_at", -1).limit(30).to_list(30)
    if not metrics:
        metrics = {"total_equity": 10000.0, "max_equity": 10000.0, "daily_pnl": 0.0}
    return AdvancedRiskManager().get_risk_assessment(metrics, positions, recent_trades)


@api_router.get("/performance/metrics")
async def get_performance_metrics(current_user: dict = Depends(get_current_user)):
    all_trades = await db.trades.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(1000)
    total_trades = len(all_trades)
    winning_trades = [t for t in all_trades if t.get("pnl", 0) > 0]
    losing_trades = [t for t in all_trades if t.get("pnl", 0) < 0]
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
    avg_profit = sum(t.get("pnl", 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t.get("pnl", 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
    total_profit = sum(t.get("pnl", 0) for t in winning_trades)
    total_loss = sum(t.get("pnl", 0) for t in losing_trades)
    metrics = await db.risk_metrics.find_one({"user_id": current_user["id"]}, {"_id": 0}, sort=[("timestamp", -1)])
    current_equity = metrics.get("total_equity", 10000.0) if metrics else 10000.0
    roi = ((current_equity - 10000.0) / 10000.0 * 100)
    return {
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": round(win_rate, 2),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "net_pnl": round(total_profit + total_loss, 2),
        "roi": round(roi, 2),
    }


@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    metrics = await db.risk_metrics.find_one({"user_id": current_user["id"]}, {"_id": 0}, sort=[("timestamp", -1)])
    positions = await db.positions.find({"user_id": current_user["id"]}, {"_id": 0}).to_list(100)
    trades_count = await db.trades.count_documents({"user_id": current_user["id"]})
    config = await db.bot_configs.find_one({"user_id": current_user["id"]}, {"_id": 0})
    if not metrics:
        metrics = {"total_equity": 10000.0, "daily_pnl": 0.0, "current_drawdown": 0.0, "positions_value": 0.0}
    return {
        "total_equity": metrics.get("total_equity", 10000.0),
        "daily_pnl": metrics.get("daily_pnl", 0.0),
        "total_positions": len(positions),
        "total_trades": trades_count,
        "bot_active": config.get("is_active", False) if config else False,
        "current_drawdown": metrics.get("current_drawdown", 0.0),
    }
