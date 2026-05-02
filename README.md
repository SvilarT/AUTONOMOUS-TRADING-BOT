# Autonomous Trading Bot

An AI-powered cryptocurrency trading bot prototype with market analysis, risk-management scaffolding, and a dashboard for simulated cryptocurrency trading.

> **Current execution status:** the inspected V2 bot execution path is simulation-only. It generates synthetic fills and does not place live Coinbase orders. Do not assume that setting Coinbase credentials or disabling `SIMULATION_MODE` enables live trading.

## Features

### AI-Powered Analysis
- Market/regime analysis scaffolding
- Signal-generation pipeline with confidence scores
- Risk-assessment scaffolding for trade decisions

### Risk Management
- Configurable capital floor and daily-loss settings in the API model
- V2 risk guard for max position notional, total exposure, open-position count, daily-loss, drawdown, and cooldown checks
- Simulation-first operating model

### Execution
- **Simulation Mode:** test strategy/control flow without real funds
- **V2 Execution:** currently returns simulated fills only
- **Live Trading:** not production-ready and not wired through the inspected V2 execution path

### Dashboard
- Portfolio, P&L, positions, trades, risk, and analysis views

## Tech Stack

**Backend:**
- FastAPI (Python)
- MongoDB
- JWT authentication
- Coinbase package dependency present, but V2 execution is currently simulated

**Frontend:**
- React
- Tailwind CSS + shadcn/ui
- Recharts
- Axios

## Getting Started

### 1. Environment Setup

The application runs in **simulation mode** by default.

Recommended local-development environment:

```bash
DEBUG=True
JWT_SECRET=replace-with-a-long-random-local-secret
SIMULATION_MODE=True
CORS_ORIGINS=http://localhost:3000
MONGO_URL=mongodb://localhost:27017
DB_NAME=trading_bot
```

Production-like deployments should set:

```bash
DEBUG=False
JWT_SECRET=<long-random-secret-from-a-secret-manager>
SIMULATION_MODE=True
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
3. Start the bot to begin simulation-mode autonomous trading

## Simulation Mode

**Current supported mode:** Simulation

- Uses generated market data for strategy flow
- Executes paper trades with simulated slippage
- No real funds are used
- Suitable for UI, orchestration, and risk-control development

## Live Trading Status

Live trading is **not currently enabled through the inspected V2 execution path**.

The V2 execution path uses `TradingServiceV2`, which returns simulated fills. Before connecting real funds, the project needs a dedicated live-execution adapter, real historical market-data integration, stronger state/audit logging, and enforced risk kill-switch behavior.

Required work before live trading:

1. Implement a Coinbase execution adapter behind an explicit `LIVE_TRADING_ENABLED=True` gate.
2. Keep `SIMULATION_MODE=True` as the default.
3. Fail closed when live market data is unavailable.
4. Add a canonical append-only trade ledger.
5. Enforce risk kill switches before every order.
6. Add tests for auth, market data, execution, accounting, and risk halts.

## Phase 1 Safety Remediation

This branch includes first-pass safety hardening:

1. Market data fails closed in non-simulation mode instead of silently returning simulated prices.
2. Historical data refuses to return generated history when simulation mode is disabled.
3. Runtime configuration guard module validates JWT and CORS posture.
4. Documentation now accurately states that the current V2 bot is simulation-only.

## Safety Features

The codebase includes safety scaffolding, but several controls still need full integration before production use:

1. Capital floor configuration
2. Daily-loss configuration
3. Position and exposure checks in `RiskGuardV2`
4. Cooldown checks in `RiskGuardV2`
5. Simulation-mode execution path

## Trading Strategy

The bot implements a multi-factor scaffold:

1. Market regime classification
2. Signal generation
3. Allocation
4. Risk checks
5. Simulated execution
6. Portfolio state updates

---

**Status:** simulation prototype. Not ready for live autonomous trading.
