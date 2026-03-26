from datetime import datetime, timezone
import asyncio
import logging
import random

from services.execution_service_v2 import ExecutionServiceV2
from services.portfolio_service_v2 import PortfolioServiceV2
from services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class BotEngine:
    def __init__(self, db):
        self.db = db
        self.execution = ExecutionServiceV2()
        self.portfolio = PortfolioServiceV2(db)
        self.market = MarketDataService()
        self.running = False

    async def start(self, user_id: str):
        self.running = True
        logger.info(f"Bot started: {user_id}")

        while self.running:
            try:
                await self.cycle(user_id)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        self.running = False

    async def cycle(self, user_id: str):
        config = await self.db.bot_configs.find_one({"user_id": user_id})
        if not config or not config.get("is_active"):
            return

        symbols = config.get("symbols", ["BTC-USD"])

        for symbol in symbols:
            await self.trade_symbol(user_id, symbol)

    async def trade_symbol(self, user_id: str, symbol: str):
        price_data = await self.market.get_current_price(symbol)
        price = price_data.get("price", 0)

        if price <= 0:
            return

        position = await self.db.positions_v2.find_one({
            "user_id": user_id,
            "symbol": symbol
        })

        # Placeholder strategy for Phase 1 engine replacement.
        # Replace this in Phase 2 with deterministic signal generation.
        decision = random.choice(["BUY", "SELL", "HOLD"])

        if not position and decision == "BUY":
            await self.execute_buy(user_id, symbol, 100)

        elif position and decision == "SELL":
            await self.execute_sell(user_id, symbol, position)

    async def execute_buy(self, user_id: str, symbol: str, notional: float):
        order = await self.execution.buy(symbol, notional)

        if not order.get("success"):
            logger.error(f"Buy failed for {symbol}: {order}")
            return

        await self.portfolio.record_buy_fill(
            user_id=user_id,
            symbol=symbol,
            filled_price=order["filled_price"],
            base_units=order["base_units"],
            notional_usd=order["notional_usd"]
        )

        logger.info(f"BUY {symbol} ${notional}")

    async def execute_sell(self, user_id: str, symbol: str, position: dict):
        order = await self.execution.sell(
            symbol,
            position["base_units"]
        )

        if not order.get("success"):
            logger.error(f"Sell failed for {symbol}: {order}")
            return

        result = await self.portfolio.record_sell_fill(
            user_id=user_id,
            symbol=symbol,
            filled_price=order["filled_price"],
            base_units=order["base_units"]
        )

        logger.info(f"SELL {symbol} PnL={result.get('realized_pnl', 0)}")
