from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
import os
import logging
import uuid
import jwt
from passlib.context import CryptContext
from contextlib import asynccontextmanager
import asyncio

# Service imports
from services.trading_service import TradingService
from services.market_data_service import MarketDataService
from services.ai_analysis_service import AIAnalysisService
from services.risk_manager import RiskManager
from services.bot_engine import BotEngine
from services.bot_manager import BotManager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'trading_bot')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global bot manager
bot_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    global bot_manager
    
    # Startup
    logger.info("Starting Autonomous Trading Bot application...")
    bot_manager = BotManager(db)
    
    # Start bot manager in background
    manager_task = asyncio.create_task(bot_manager.start_manager())
    logger.info("Bot Manager started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await bot_manager.stop_manager()
    manager_task.cancel()
    try:
        await manager_task
    except asyncio.CancelledError:
        pass
    client.close()
    logger.info("Application shutdown complete")

# Create the main app
app = FastAPI(title="Autonomous Trading Bot", lifespan=lifespan)
api_router = APIRouter(prefix="/api")

# ============= MODELS =============
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class Trade(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    symbol: str
    side: str  # BUY/SELL
    order_type: str  # market/limit
    quantity: float
    price: Optional[float] = None
    filled_price: Optional[float] = None
    status: str  # pending/filled/cancelled
    ai_reasoning: Optional[str] = None
    regime: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None

class Position(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    symbol: str
    quantity: float
    avg_price: float
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BotConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    is_active: bool = False
    capital_floor: float = 0.97
    max_daily_loss: float = 0.015
    risk_target_vol: float = 0.10
    symbols: List[str] = ["BTC-USD", "ETH-USD"]
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RiskMetrics(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    total_equity: float
    max_equity: float
    equity_floor: float
    current_drawdown: float
    daily_pnl: float
    positions_value: float
    cash_balance: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MarketAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    regime: str  # trend/mean-reversion/vol-crush/shock
    signal_strength: float
    ai_analysis: str
    buy_recommendation: bool
    confidence: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ============= AUTH HELPERS =============
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    to_encode.update({"exp": expire})
    jwt_secret = os.environ.get('JWT_SECRET', 'dev-secret-keep-it-safe')
    return jwt.encode(to_encode, jwt_secret, algorithm="HS256")

def verify_token(token: str):
    try:
        jwt_secret = os.environ.get('JWT_SECRET', 'dev-secret-keep-it-safe')
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        return payload
    except:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# ============= AUTH ROUTES =============
@api_router.post("/auth/signup", response_model=TokenResponse)
async def signup(user_data: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=pwd_context.hash(user_data.password)
    )
    user_dict = user.model_dump()
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    # Initialize bot config
    config = BotConfig(user_id=user.id)
    config_dict = config.model_dump()
    config_dict['updated_at'] = config_dict['updated_at'].isoformat()
    await db.bot_configs.insert_one(config_dict)
    
    # Create token
    token = create_access_token({"user_id": user.id, "email": user.email})
    
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "email": user.email}
    )

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not pwd_context.verify(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"user_id": user['id'], "email": user['email']})
    
    return TokenResponse(
        access_token=token,
        user={"id": user['id'], "email": user['email']}
    )

# ============= TRADING ROUTES =============
@api_router.get("/trades")
async def get_trades(current_user: dict = Depends(get_current_user)):
    trades = await db.trades.find({"user_id": current_user['id']}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"trades": trades}

@api_router.get("/positions")
async def get_positions(current_user: dict = Depends(get_current_user)):
    positions = await db.positions.find({"user_id": current_user['id']}, {"_id": 0}).to_list(100)
    return {"positions": positions}

@api_router.get("/risk-metrics")
async def get_risk_metrics(current_user: dict = Depends(get_current_user)):
    metrics = await db.risk_metrics.find_one({"user_id": current_user['id']}, {"_id": 0}, sort=[("timestamp", -1)])
    if not metrics:
        # Initialize default metrics
        metrics_obj = RiskMetrics(
            user_id=current_user['id'],
            total_equity=10000.0,
            max_equity=10000.0,
            equity_floor=9700.0,
            current_drawdown=0.0,
            daily_pnl=0.0,
            positions_value=0.0,
            cash_balance=10000.0
        )
        metrics = metrics_obj.model_dump()
        metrics['timestamp'] = metrics['timestamp'].isoformat()
        await db.risk_metrics.insert_one(metrics)
        # Return the clean metrics without _id
        return metrics
    
    # Ensure no ObjectId fields are present
    if '_id' in metrics:
        del metrics['_id']
    
    return metrics

@api_router.get("/bot-config")
async def get_bot_config(current_user: dict = Depends(get_current_user)):
    config = await db.bot_configs.find_one({"user_id": current_user['id']}, {"_id": 0})
    return config

@api_router.post("/bot-config")
async def update_bot_config(config_update: BotConfig, current_user: dict = Depends(get_current_user)):
    config_dict = config_update.model_dump()
    config_dict['user_id'] = current_user['id']
    config_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.bot_configs.update_one(
        {"user_id": current_user['id']},
        {"$set": config_dict},
        upsert=True
    )
    return {"status": "success", "config": config_dict}

@api_router.get("/market-analysis")
async def get_market_analysis(symbol: str = "BTC-USD"):
    analysis = await db.market_analysis.find_one({"symbol": symbol}, {"_id": 0}, sort=[("timestamp", -1)])
    if not analysis:
        return {"message": "No analysis available yet"}
    return analysis

@api_router.get("/technical-indicators/{symbol}")
async def get_technical_indicators(symbol: str, current_user: dict = Depends(get_current_user)):
    """Get latest technical indicators for a symbol"""
    analysis = await db.market_analysis.find_one(
        {"symbol": symbol},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    if analysis and 'technical_indicators' in analysis:
        return {
            "symbol": symbol,
            "technical_indicators": analysis['technical_indicators'],
            "technical_signals": analysis.get('technical_signals', {}),
            "timestamp": analysis.get('timestamp')
        }
    else:
        return {"message": "No technical data available yet"}

@api_router.get("/market-data/{symbol}")
async def get_market_data(symbol: str):
    try:
        service = MarketDataService()
        price_data = await service.get_current_price(symbol)
        return price_data
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============= BOT CONTROL =============
@api_router.post("/bot/start")
async def start_bot(current_user: dict = Depends(get_current_user)):
    await db.bot_configs.update_one(
        {"user_id": current_user['id']},
        {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    logger.info(f"Bot activation requested for user {current_user['id']}")
    return {"status": "Bot started", "is_active": True}

@api_router.post("/bot/stop")
async def stop_bot(current_user: dict = Depends(get_current_user)):
    await db.bot_configs.update_one(
        {"user_id": current_user['id']},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    logger.info(f"Bot stop requested for user {current_user['id']}")
    return {"status": "Bot stopped", "is_active": False}

@api_router.get("/risk/advanced-assessment")
async def get_advanced_risk_assessment(current_user: dict = Depends(get_current_user)):
    """Get advanced risk assessment with CVaR, portfolio heat, etc."""
    from services.advanced_risk_manager import AdvancedRiskManager
    
    advanced_risk = AdvancedRiskManager()
    
    # Get risk metrics
    metrics = await db.risk_metrics.find_one(
        {"user_id": current_user['id']},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    # Get positions
    positions = await db.positions.find({"user_id": current_user['id']}, {"_id": 0}).to_list(100)
    
    # Get recent trades for CVaR
    recent_trades = await db.trades.find(
        {"user_id": current_user['id']},
        {"_id": 0}
    ).sort("created_at", -1).limit(30).to_list(30)
    
    if not metrics:
        metrics = {
            "total_equity": 10000.0,
            "max_equity": 10000.0,
            "daily_pnl": 0.0
        }
    
    assessment = advanced_risk.get_risk_assessment(metrics, positions, recent_trades)
    
    return assessment

@api_router.get("/performance/metrics")
async def get_performance_metrics(current_user: dict = Depends(get_current_user)):
    """Get detailed performance metrics"""
    # Get all trades
    all_trades = await db.trades.find({"user_id": current_user['id']}, {"_id": 0}).to_list(1000)
    
    # Calculate metrics
    total_trades = len(all_trades)
    winning_trades = [t for t in all_trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in all_trades if t.get('pnl', 0) < 0]
    
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
    
    avg_profit = sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    total_profit = sum(t.get('pnl', 0) for t in winning_trades)
    total_loss = sum(t.get('pnl', 0) for t in losing_trades)
    net_pnl = total_profit + total_loss
    
    # Best and worst trades
    best_trade = max(all_trades, key=lambda t: t.get('pnl', 0)) if all_trades else None
    worst_trade = min(all_trades, key=lambda t: t.get('pnl', 0)) if all_trades else None
    
    # Get current equity
    metrics = await db.risk_metrics.find_one(
        {"user_id": current_user['id']},
        {"_id": 0},
        sort=[("timestamp", -1)]
    )
    
    starting_equity = 10000.0
    current_equity = metrics.get('total_equity', starting_equity) if metrics else starting_equity
    roi = ((current_equity - starting_equity) / starting_equity * 100) if starting_equity > 0 else 0
    
    return {
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": round(win_rate, 2),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "total_profit": round(total_profit, 2),
        "total_loss": round(total_loss, 2),
        "net_pnl": round(net_pnl, 2),
        "roi": round(roi, 2),
        "best_trade": {
            "symbol": best_trade.get('symbol'),
            "pnl": round(best_trade.get('pnl', 0), 2),
            "pnl_percent": round(best_trade.get('pnl_percent', 0), 2)
        } if best_trade and best_trade.get('pnl') else None,
        "worst_trade": {
            "symbol": worst_trade.get('symbol'),
            "pnl": round(worst_trade.get('pnl', 0), 2),
            "pnl_percent": round(worst_trade.get('pnl_percent', 0), 2)
        } if worst_trade and worst_trade.get('pnl') else None
    }

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    # Get metrics
    metrics = await db.risk_metrics.find_one({"user_id": current_user['id']}, {"_id": 0}, sort=[("timestamp", -1)])
    
    # Get positions
    positions = await db.positions.find({"user_id": current_user['id']}, {"_id": 0}).to_list(100)
    
    # Get recent trades
    trades_count = await db.trades.count_documents({"user_id": current_user['id']})
    
    # Get bot status
    config = await db.bot_configs.find_one({"user_id": current_user['id']}, {"_id": 0})
    
    if not metrics:
        metrics = {
            "total_equity": 10000.0,
            "daily_pnl": 0.0,
            "current_drawdown": 0.0,
            "positions_value": 0.0
        }
    
    return {
        "total_equity": metrics.get("total_equity", 10000.0),
        "daily_pnl": metrics.get("daily_pnl", 0.0),
        "total_positions": len(positions),
        "total_trades": trades_count,
        "bot_active": config.get("is_active", False) if config else False,
        "current_drawdown": metrics.get("current_drawdown", 0.0)
    }

# Health check
@app.get("/")
async def root():
    return {"status": "ok", "service": "Autonomous Trading Bot"}

# Include router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
