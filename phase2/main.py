"""Example entry point for the refactored trading bot.

This script demonstrates how to wire together the core components, load
plugins from the configuration and execute a simple trading loop.  For
production use, integrate this with an event loop scheduler, real data
providers and persistent storage.
"""

import asyncio
import yaml
from typing import Dict, Any, List

# Use absolute imports so the module can be run as a script.
from phase2.core.strategy_engine import StrategyEngine
from phase2.core.execution_router import ExecutionRouter
from phase2.core.risk_manager import RiskManager
from phase2.core.portfolio_service import PortfolioService, AbstractPortfolioRepo
from phase2.plugin_loader import load_strategies, load_connectors


class InMemoryRepo(AbstractPortfolioRepo):
    """Simple in‑memory repository for portfolio state and positions.

    This is intended for testing only.  In production, replace with a
    database‑backed implementation.
    """
    def __init__(self):
        self.state: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, List[Dict[str, Any]]] = {}

    async def get_state(self, user_id: str):
        return self.state.get(user_id)

    async def upsert_state(self, user_id: str, updates: Dict[str, Any]):
        current = self.state.get(user_id, {})
        # merge updates (adding numbers for cash_balance and realized_pnl)
        merged = current.copy()
        for k, v in updates.items():
            if k in ("cash_balance", "realized_pnl"):
                merged[k] = merged.get(k, 0.0) + v
            else:
                merged[k] = v
        self.state[user_id] = merged

    async def get_positions(self, user_id: str):
        return self.positions.get(user_id, [])

    async def upsert_position(self, user_id: str, symbol: str, updates: Dict[str, Any]):
        pos_list = self.positions.setdefault(user_id, [])
        existing = next((p for p in pos_list if p["symbol"] == symbol), None)
        if existing:
            existing.update(updates)
        else:
            pos_list.append(updates)

    async def delete_position(self, user_id: str, symbol: str):
        pos_list = self.positions.get(user_id)
        if not pos_list:
            return
        self.positions[user_id] = [p for p in pos_list if p["symbol"] != symbol]


async def run_bot(config_path: str):
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    # load plugins
    strategies = load_strategies(config)
    connectors = load_connectors(config)
    # instantiate core services
    strategy_engine = StrategyEngine(strategies)
    execution_router = ExecutionRouter(connectors)
    risk_manager = RiskManager()
    portfolio_repo = InMemoryRepo()
    portfolio_service = PortfolioService(portfolio_repo)
    # Example: simulate one cycle for user1 and symbol BTC-USD
    user_id = "user1"
    symbol = "BTC-USD"
    # get mock price history from connector base prices; in real scenario, use DataProvider
    base_price = connectors[0].base_prices[symbol]
    prices = [base_price * (1 + 0.001 * i) for i in range(40)]  # fake uptrend
    # generate signals
    positions = await portfolio_repo.get_positions(user_id)
    has_position = bool(next((p for p in positions if p["symbol"] == symbol), None))
    signals = strategy_engine.generate_all(prices, has_position)
    # choose best signal (simple ranking by score and confidence)
    signals_sorted = sorted(signals, key=lambda s: (abs(s.get("score", 0.0)), s.get("confidence", 0.0)), reverse=True)
    top = signals_sorted[0]
    action = top.get("action")
    notional = 100.0 * (top.get("confidence", 50.0) / 100.0)
    # compute metrics and decide if allowed
    state = await portfolio_repo.get_state(user_id) or {}
    price_map = {symbol: prices[-1]}
    metrics = risk_manager.portfolio_metrics(state, positions, price_map)
    allowed = risk_manager.can_open_position(metrics, positions, notional)
    if action == "BUY" and allowed.get("allowed"):
        result = await execution_router.buy(symbol, notional)
        await portfolio_service.record_buy_fill(user_id, symbol, result["filled_price"], result["base_units"], result["notional_usd"])
        print(f"Bought {symbol}:", result)
    elif action == "SELL" and has_position:
        # sell all units
        pos = next((p for p in positions if p["symbol"] == symbol), None)
        if pos:
            result = await execution_router.sell(symbol, pos["base_units"])
            await portfolio_service.record_sell_fill(user_id, symbol, result["filled_price"], result["base_units"])
            print(f"Sold {symbol}:", result)
    else:
        print("No trade executed.")
    # display portfolio
    print("Portfolio state:", await portfolio_repo.get_state(user_id))
    print("Positions:", await portfolio_repo.get_positions(user_id))


if __name__ == "__main__":
    import os
    # Resolve configuration relative to this file’s directory
    config_path = os.path.join(os.path.dirname(__file__), "config.yml")
    asyncio.run(run_bot(config_path))
