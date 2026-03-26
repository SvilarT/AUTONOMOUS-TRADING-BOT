class BotEngine:
    def __init__(self, db):
        self.db = db
        self.execution = ExecutionServiceV2()
        self.exec_opt = ExecutionOptimizerV2()
        self.portfolio = PortfolioServiceV2(db)
        self.market = MarketDataService()
        self.risk = RiskGuardV2()
        self.ensemble = StrategyEnsembleV2()
        self.allocator = AllocatorV2()
        self.regime = RegimeServiceV2()
        self.running = False

    async def cycle(self, user_id: str):
        config = await self.db.bot_configs.find_one({"user_id": user_id})
        if not config or not config.get("is_active"):
            return

        positions = await self.db.positions_v2.find({"user_id": user_id}).to_list(100)
        state = await self.db.portfolio_state.find_one({"user_id": user_id}) or {}

        symbols = config.get("symbols", ["BTC-USD"])

        for symbol in symbols:
            await self.process_symbol(user_id, symbol, positions, state)

    async def process_symbol(self, user_id, symbol, positions, state):
        hist = await self.market.get_historical_data(symbol, periods=120)
        prices = [h["price"] for h in hist if h.get("price")]

        if len(prices) < 30:
            return

        regime = self.regime.classify(prices)

        position = next((p for p in positions if p["symbol"] == symbol), None)

        signals = self.ensemble.generate_all(prices, has_position=bool(position))

        # 🔥 Regime filtering
        if regime == "range":
            signals = [s for s in signals if s["strategy"] != "trend_following"]
        elif regime == "trend_up":
            signals = [s for s in signals if s["strategy"] != "mean_reversion"]

        allocation = self.allocator.allocate(signals, base_notional=100.0)

        volatility = abs((prices[-1] - prices[-10]) / prices[-10]) if prices[-10] else 0

        final_notional = self.exec_opt.shape_notional(
            allocation["notional"],
            allocation["selected"]["confidence"],
            volatility
        )

        if allocation["action"] == "BUY" and not position:
            guard = self.risk.can_open_position(
                self.risk.portfolio_metrics(state, positions, {symbol: prices[-1]}),
                positions,
                final_notional,
                state.get("last_trade_at")
            )

            if guard["allowed"]:
                await self.execute_buy(user_id, symbol, final_notional, allocation)

        elif allocation["action"] == "SELL" and position:
            await self.execute_sell(user_id, symbol, position)

    async def execute_buy(self, user_id, symbol, notional, context):
        order = await self.execution.buy(symbol, notional, signal_snapshot=context)
        if not order.get("success"):
            return

        await self.portfolio.record_buy_fill(
            user_id,
            symbol,
            order["filled_price"],
            order["base_units"],
            order["notional_usd"]
        )

    async def execute_sell(self, user_id, symbol, position):
        order = await self.execution.sell(symbol, position["base_units"])
        if not order.get("success"):
            return

        await self.portfolio.record_sell_fill(
            user_id,
            symbol,
            order["filled_price"],
            order["base_units"]
        )
