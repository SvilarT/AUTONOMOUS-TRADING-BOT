# Autonomous Trading Bot

An AI-powered cryptocurrency trading bot prototype with market analysis, risk-management scaffolding, paper execution, gated live-execution preview endpoints, and a dashboard for simulated cryptocurrency trading.

> **Current execution status:** autonomous bot execution remains paper/simulation-only through `BotEngine -> ExecutionServiceV2 -> TradingServiceV2`. Separately, the API contains manually invoked, gated live Coinbase order endpoints through `LiveTradingServiceV2`. Those endpoints are fail-closed by default and are not production-ready for autonomous live trading.

## Features

### AI-Powered Analysis
- Market/regime analysis scaffolding
- Signal-generation pipeline with confidence scores
- Risk-assessment scaffolding for trade decisions

### Risk Management
- Configurable capital floor and daily-loss settings in the API model
- V2 risk guard for max position notional, total exposure, open-position count, daily-loss, drawdown, and cooldown checks
- Simulation-first operating model
- Gated live-order preflight checks for manually invoked live endpoints

### Execution
- **Paper/Simulation Bot Execution:** autonomous bot cycles execute through the paper adapter only
- **Gated Live Execution Endpoints:** manual `/live-trading/*` endpoints can reach Coinbase only when all live gates pass
- **Live Autonomous Trading:** not production-ready and intentionally blocked from the autonomous bot path

### Dashboard
- Portfolio, P&L, positions, trades, risk, and analysis views

## Tech Stack

**Backend:**
- FastAPI (Python)
- MongoDB
- JWT authentication
- Paper execution adapter for autonomous bot cycles
- Coinbase live execution adapter behind explicit gated manual endpoints

**Frontend:**
- React
- Tailwind CSS + shadcn/ui
- Recharts
- Axios

## Getting Started

### 1. Environment Setup

The application runs in paper/simulation mode by default.

Recommended local-development environment:

```bash
DEBUG=True
JWT_SECRET=replace-with-a-long-random-local-secret
SIMULATION_MODE=True
TRADING_MODE=paper
CORS_ORIGINS=http://localhost:3000
MONGO_URL=mongodb://localhost:27017
DB_NAME=trading_bot
```

Production-like deployments should set:

```bash
DEBUG=False
JWT_SECRET=<long-random-secret-from-a-secret-manager>
SIMULATION_MODE=True
TRADING_MODE=paper
CORS_ORIGINS=https://your-frontend-domain.example
```

Do not use wildcard CORS origins in production.

### 2. Launch the Application

```bash
# Check service status
sudo supervisorctl status

# Restart services if needed
sudo supervisorctl restart backend frontend
```

### 3. Access the Dashboard

Open your browser to: **http://localhost:3000**

1. Sign up with email/password
2. View the simulated portfolio
3. Start the bot to begin paper-mode autonomous trading

## Paper / Simulation Mode

**Default supported autonomous mode:** Paper/simulation

- Uses strategy/control-flow scaffolding
- Executes paper trades with modeled fills, costs, slippage, minimums, rejections, and partial fills
- No real funds are used by the autonomous bot path
- Suitable for UI, orchestration, strategy, accounting, and risk-control development

## Live Trading Status

Live trading exists only through explicit, manually invoked, gated endpoints:

- `POST /live-trading/market-buy`
- `POST /live-trading/market-sell`
- `GET /live-trading/gate`
- `GET /live-trading/audits`

The autonomous bot path does **not** use live execution. `TradingModeService.assert_can_trade()` rejects `TRADING_MODE=live-trading` for normal bot execution and requires live orders to use `LiveTradingServiceV2`.

Live execution is fail-closed unless all of the following are true:

1. `TRADING_MODE=live-trading`
2. `LIVE_TRADING_ENABLED=True`
3. `LIVE_EXECUTION_ADAPTER=coinbase_exchange_v2`
4. `COINBASE_LIVE_ORDER_KILL_SWITCH` is not enabled
5. The user's bot config has `live_trading_enabled=True`
6. The symbol is listed in `LIVE_ALLOWED_SYMBOLS`
7. The order notional is below `LIVE_MAX_ORDER_NOTIONAL_USD`
8. Manual approval is satisfied when required

Before any real-money deployment, the project still needs stronger production controls: hardened auth, MFA/approval challenge, complete ledger reconciliation, observability, incident runbooks, broker sandbox testing, and operational sign-off.

## P0 Safety Hardening

This branch includes P0 safety hardening:

1. Documentation accurately distinguishes autonomous paper execution from manually gated live endpoints.
2. Coinbase live adapter has an adapter-level kill switch.
3. Live trading gate tests cover fail-closed, dry-run, approval, symbol, and notional behavior.
4. Auth input validation rejects invalid emails and weak passwords.
5. Autonomous bot execution is regression-tested to remain blocked from live trading mode.
6. Live order audits are written through a hash-chained audit service.

## Safety Features

The codebase includes safety scaffolding, but several controls still need full production integration before live autonomous use:

1. Capital floor configuration
2. Daily-loss configuration
3. Position and exposure checks in `RiskGuardV2`
4. Cooldown checks in `RiskGuardV2`
5. Paper execution path for autonomous bot cycles
6. Fail-closed live execution gate for manual live endpoints
7. Hash-chained live order audit records

## Trading Strategy

The bot implements a multi-factor scaffold:

1. Market regime classification
2. Signal generation
3. Allocation
4. Risk checks
5. Paper execution
6. Portfolio state updates

---

**Status:** paper/simulation prototype with manually gated live-execution plumbing. Not ready for live autonomous trading.
