# P1 Platform Baseline

This document describes the first productionization batch for the Autonomous Trading Bot.

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

## What this baseline adds

- GitHub Actions CI for backend tests, backend security checks, and frontend build.
- Backend development tooling: pytest coverage, ruff, bandit, pip-audit.
- Root `.env.example` with safe paper-trading defaults.
- `Makefile` operator commands.
- Backend Dockerfile.
- Frontend Dockerfile and nginx runtime config.
- Docker Compose stack with MongoDB, backend, and frontend.

## Local quickstart

```bash
cp .env.example .env
make dev-up
```

Then open:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/healthz
- Backend readiness: http://localhost:8000/readyz

## Backend commands

```bash
make setup-backend
make test-backend
make lint-backend
make audit-backend
make run-backend
```

## Frontend commands

```bash
make setup-frontend
make build-frontend
```

## CI gates

The CI workflow has three jobs:

1. `backend-tests`
   - Installs backend runtime and dev dependencies.
   - Runs pytest with coverage.
   - Enforces a starting coverage floor of 65%.

2. `backend-security`
   - Runs ruff.
   - Runs bandit.
   - Runs pip-audit.

3. `frontend-build`
   - Installs frontend dependencies.
   - Builds the React app.

## Safety posture

The Docker Compose stack preserves the current safety boundary:

- `TRADING_MODE=paper`
- `SIMULATION_MODE=True`
- `COINBASE_LIVE_ORDER_KILL_SWITCH=True`
- live trading disabled by default

The autonomous bot path remains paper-only.

## Next productionization slices

1. Worker separation.
2. Typed settings with redacted configuration report.
3. Scoped authorization and MFA foundation.
4. Signed live approval challenge.
5. Live-readonly adapter hardening.
