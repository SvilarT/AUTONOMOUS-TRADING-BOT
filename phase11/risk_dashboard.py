"""Simple risk dashboard for Phase 5.

This script demonstrates how to compute and display advanced risk metrics
using the enhanced ``RiskManager``.  It loads the bot configuration,
generates synthetic price histories for each configured symbol and prints
key portfolio metrics, including volatility, value‑at‑risk (VaR), expected
shortfall (ES) and correlation matrices.  In a real application, the
dashboard would receive live data from a database or data pipeline and
render visual charts; here we focus on text output for clarity.
"""

import yaml
import random
from typing import Dict, List

# Use the latest RiskManager from phase11 for advanced metrics
from phase11.core.risk_manager import RiskManager


def generate_synthetic_history(base_price: float, length: int = 100, volatility: float = 0.003) -> List[float]:
    """Generate a random walk price series around a base price."""
    prices = []
    price = base_price
    for _ in range(length):
        delta = random.uniform(-volatility, volatility)
        price *= 1 + delta
        prices.append(round(price, 2))
    return prices


def display_metrics(metrics: Dict[str, any]) -> None:
    """Pretty‑print risk metrics to the console."""
    print("\n=== Portfolio Metrics ===")
    for key in ["cash_balance", "market_value", "total_equity", "daily_loss_pct", "drawdown_pct", "exposure_pct"]:
        val = metrics.get(key)
        if key.endswith("_pct"):
            print(f"{key:20}: {val:.2%}")
        else:
            print(f"{key:20}: {val}")
    print("\nVolatility (annualised)")
    for sym, vol in metrics.get("volatility", {}).items():
        print(f"  {sym}: {vol:.2%}")
    print("\nValue‑at‑Risk (VaR)")
    for sym, v in metrics.get("var", {}).items():
        print(f"  {sym}: {v:.4f}")
    print("\nExpected Shortfall (ES)")
    for sym, v in metrics.get("es", {}).items():
        print(f"  {sym}: {v:.4f}")
    corr = metrics.get("correlation", {})
    if corr:
        syms = list(corr.keys())
        print("\nCorrelation matrix:")
        # header
        header = "      " + "  ".join([f"{s:>8}" for s in syms])
        print(header)
        for s1 in syms:
            row = [f"{s1:>4}"]
            for s2 in syms:
                row.append(f"{corr[s1][s2]:>8.2f}")
            print("  ".join(row))


def run_dashboard(config_path: str) -> None:
    """Load configuration, generate synthetic data and compute metrics."""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    symbols = set()
    # Extract symbols from connector base prices (mock connectors)
    for conn in config.get("connectors", []):
        params = conn.get("params", {})
        base_prices = params.get("base_prices", {})
        symbols.update(base_prices.keys())
    # Synthetic price histories for each symbol
    history: Dict[str, List[float]] = {}
    price_map: Dict[str, float] = {}
    for sym in symbols:
        # pick a base price from first connector or default to 1000
        base = None
        for conn in config.get("connectors", []):
            bp = conn.get("params", {}).get("base_prices", {})
            if sym in bp:
                base = bp[sym]
                break
        base_price = base or 1000.0
        series = generate_synthetic_history(base_price)
        history[sym] = series
        price_map[sym] = series[-1]
    # Instantiate risk manager with moderate profile
    risk = RiskManager(risk_profile="moderate")
    state = {"cash_balance": 10000.0, "equity_high": 10000.0, "daily_start_equity": 10000.0}
    metrics = risk.portfolio_metrics(state, [], price_map, history)
    display_metrics(metrics)


if __name__ == "__main__":
    import os
    cfg = os.path.join(os.path.dirname(__file__), "config.yml")
    run_dashboard(cfg)