from services.execution_optimizer_v2 import ExecutionOptimizerV2
from services.regime_service_v2 import RegimeServiceV2
from services.signal_planner_v2 import SignalPlannerV2
from services.strategy_ensemble_v2 import StrategyEnsembleV2
from services.strategy_service_v2 import StrategyServiceV2


def rising_prices(count: int = 80, start: float = 100.0, drift: float = 0.01) -> list[float]:
    values = []
    price = start
    for _ in range(count):
        values.append(price)
        price *= 1 + drift
    return values


def falling_prices(count: int = 80, start: float = 200.0, drift: float = -0.01) -> list[float]:
    values = []
    price = start
    for _ in range(count):
        values.append(price)
        price *= 1 + drift
    return values


def range_prices(count: int = 80, center: float = 100.0) -> list[float]:
    return [center + ((index % 6) - 3) * 0.15 for index in range(count)]


def volatile_prices() -> list[float]:
    return [100.0, 106.0, 94.0, 108.0, 92.0, 110.0] * 6


def test_strategy_module_imports_and_ensemble_builds():
    ensemble = StrategyEnsembleV2()

    signals = ensemble.generate_all(rising_prices(), has_position=False)

    assert {signal["strategy"] for signal in signals} == {
        "trend_following",
        "mean_reversion",
        "breakout",
    }


def test_strategy_reports_hold_for_insufficient_history():
    signal = StrategyServiceV2().generate_signal([100.0, 101.0, 102.0], has_position=False)

    assert signal["action"] == "HOLD"
    assert signal["features"]["ready"] is False
    assert signal["score"] == 0.0


def test_strategy_feature_polarity_for_positive_and_negative_trends():
    service = StrategyServiceV2()

    positive = service.generate_signal(rising_prices(), has_position=False)
    negative = service.generate_signal(falling_prices(), has_position=True)

    assert positive["score"] > 0
    assert positive["features"]["return_20"] > 0
    assert negative["score"] < 0
    assert negative["features"]["return_20"] < 0


def test_regime_classifier_distinguishes_core_regimes():
    classifier = RegimeServiceV2()

    assert classifier.classify(rising_prices()) == "trend_up"
    assert classifier.classify(falling_prices()) == "trend_down"
    assert classifier.classify(range_prices()) == "range"
    assert classifier.classify(volatile_prices()) == "high_volatility"


def test_execution_optimizer_preserves_non_action_as_zero_notional():
    optimizer = ExecutionOptimizerV2()

    assert optimizer.shape_notional(0.0, confidence=50.0, volatility=0.01) == 0.0
    assert optimizer.shape_notional(-1.0, confidence=50.0, volatility=0.01) == 0.0


def test_planner_returns_zero_notional_when_history_is_insufficient():
    plan = SignalPlannerV2().build_plan("BTC-USD", [100.0, 101.0, 102.0], has_position=False)

    assert plan["action"] == "HOLD"
    assert plan["notional"] == 0.0


def test_planner_forces_zero_notional_for_hold_allocation():
    planner = SignalPlannerV2()
    planner.regime.classify = lambda prices: "mixed"
    planner.ensemble.generate_all = lambda prices, has_position: [
        {"strategy": "trend_following", "action": "HOLD", "score": 0.0, "confidence": 50.0},
        {"strategy": "mean_reversion", "action": "HOLD", "score": 0.0, "confidence": 50.0},
        {"strategy": "breakout", "action": "HOLD", "score": 0.0, "confidence": 50.0},
    ]

    plan = planner.build_plan("BTC-USD", rising_prices(), has_position=False)

    assert plan["action"] == "HOLD"
    assert plan["notional"] == 0.0
