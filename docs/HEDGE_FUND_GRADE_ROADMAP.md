# Hedge Fund-Grade Upgrade Roadmap

## Objective
Transform the current autonomous trading bot from a prototype into a production-grade systematic trading platform with strict separation of concerns, deterministic accounting, realistic execution modeling, strong controls, observability, and research-quality experimentation.

## Target Architecture

### 1. Layered system
- `strategy/`: signal generation, model interfaces, feature engineering, regime models
- `risk/`: pre-trade checks, portfolio constraints, exposure, factor risk, kill switches
- `execution/`: order router, execution algorithms, reconciliation, venue adapters
- `portfolio/`: positions, cash ledger, fills, PnL, NAV, corporate actions abstraction
- `data/`: live market data, historical bars, order book snapshots, event streams
- `research/`: backtests, walk-forward, Monte Carlo, experiment tracking
- `ops/`: monitoring, secrets, deployment, health checks, incident tooling

### 2. Core principles
- event-driven, not polling-driven
- append-only ledger for trades, fills, cash movements, and portfolio state transitions
- deterministic signal snapshots for every decision
- exchange reconciliation as a first-class process
- strict live/sim/backtest mode isolation
- no direct LLM authority over order placement

## Immediate Code Changes

### Trading engine
- split `BotEngine` into orchestrator + strategy + execution + accounting services
- replace implicit position math with explicit base units, quote notional, average fill price, fees, realized/unrealized PnL
- add idempotent order handling with `client_order_id`
- add retry and reconciliation flow for partial fills and stale order states

### Risk
- separate pre-trade risk from portfolio monitoring
- enforce max gross exposure, max net exposure, per-symbol cap, per-sector/factor cap, concentration limits
- add kill switches for API failure, stale data, price gaps, latency spikes, and reconciliation mismatch
- use daily baseline and rolling drawdown windows

### Market data
- websocket ingestion for live tick/quote updates
- persistent bar store and feature cache
- strict stale-data detection
- unified data adapters for simulation/live/backtest

### Strategy
- define strategy interface:
  - `prepare_features(data)`
  - `generate_signal(state)`
  - `size_order(signal, portfolio, risk)`
- move LLM usage to commentary/regime annotation only
- add deterministic technical/rule-based baseline strategy for benchmarking

### Accounting
- append-only fills ledger
- realized/unrealized PnL split
- fee/slippage accounting
- end-of-day NAV snapshots
- reconciliation against venue balances and fills

### Security and ops
- enforce env validation at boot
- remove insecure defaults
- rotate secrets, scoped API keys, and deployment-specific CORS rules
- structured JSON logging
- metrics and tracing
- audit trail for decisions and parameter changes

## Research Stack
- backtesting engine with event-driven bar replay
- walk-forward validation
- slippage/fee model by venue and symbol
- parameter registry and experiment tracking
- benchmark comparison and risk-adjusted metrics

## Monitoring
- Prometheus-style metrics: latency, orders, fills, rejects, slippage, PnL, drawdown, stale data
- alerting for drawdown, kill switch activation, missed heartbeats, reconciliation mismatches
- dashboards for positions, exposure, execution quality, signal attribution

## Testing
- unit tests for position accounting and sizing
- property tests for ledger invariants
- integration tests for simulated order lifecycle
- regression tests for risk limits and kill-switch behavior
- paper-trading soak tests before live enablement

## Rollout Plan
1. refactor accounting and execution primitives
2. isolate strategy interface and migrate current logic
3. add event-driven data ingestion and stale-data guards
4. implement ledger + reconciliation
5. add backtester and experiment harness
6. add observability, alerts, CI quality gates
7. run prolonged paper trading
8. enable live trading with hard caps and human override

## Definition of Done
- deterministic accounting under all fills and position transitions
- full audit trail for every order decision
- no live order on stale data or invalid state
- reproducible research to production path
- portfolio/risk controls enforced before every execution
- clear rollback and kill-switch procedures
