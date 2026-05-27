import os

# Runtime import regression coverage for the autonomous paper service graph.
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("JWT_SECRET", "runtime-import-integrity-value-12345678901234567890")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("SIMULATION_MODE", "True")
os.environ.setdefault("TRADING_MODE", "paper")
os.environ.setdefault("RUNTIME_ROLE", "api")
os.environ.setdefault("API_EMBED_BOT_MANAGER", "false")
os.environ.setdefault("RUN_MONGO_INDEX_BOOTSTRAP", "false")
os.environ.setdefault("COINBASE_LIVE_ORDER_KILL_SWITCH", "true")
os.environ.setdefault("LIVE_TRADING_ENABLED", "false")
os.environ.setdefault("LIVE_EXECUTION_ADAPTER", "disabled")


def test_runtime_critical_services_import():
    from app_factory import create_app
    from services.bot_engine import BotEngine
    from services.bot_manager import BotManager
    from services.live_trading_service_v2 import LiveTradingServiceV2
    from services.signal_planner_v2 import SignalPlannerV2
    from services.strategy_ensemble_v2 import StrategyEnsembleV2
    from services.strategy_service_v2 import StrategyServiceV2

    assert create_app is not None
    assert BotEngine is not None
    assert BotManager is not None
    assert LiveTradingServiceV2 is not None
    assert SignalPlannerV2 is not None
    assert StrategyEnsembleV2 is not None
    assert StrategyServiceV2 is not None


def test_strategy_service_contract_and_planner_output_are_compatible():
    from services.signal_planner_v2 import SignalPlannerV2
    from services.strategy_service_v2 import StrategyServiceV2

    prices = [100.0 + index * 0.35 for index in range(40)]

    base_signal = StrategyServiceV2().generate_signal(prices, has_position=False)
    assert base_signal["action"] in {"BUY", "SELL", "HOLD"}
    assert isinstance(base_signal["score"], float)
    assert 0 <= base_signal["confidence"] <= 100
    assert base_signal["features"]["sufficient_history"] is True
    assert "zscore_20" in base_signal["features"]

    plan = SignalPlannerV2().build_plan("BTC-USD", prices, has_position=False, base_notional=100.0)
    assert plan["symbol"] == "BTC-USD"
    assert plan["action"] in {"BUY", "SELL", "HOLD"}
    assert "signals" in plan
    assert "allocation" in plan
    assert "selected" in plan
    assert "notional" in plan


def test_strategy_service_holds_with_insufficient_history():
    from services.strategy_service_v2 import StrategyServiceV2

    signal = StrategyServiceV2().generate_signal([100.0, 101.0, 102.0], has_position=False)
    assert signal["action"] == "HOLD"
    assert signal["score"] == 0.0
    assert signal["features"]["sufficient_history"] is False
