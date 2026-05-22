# Phase 16 Autonomous Live Trading Gate Design

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 16 designs a separate gate for any future autonomous live mode. It does not enable autonomous execution and does not submit orders.

## Objective

Keep manual live trading and autonomous live trading strictly separated.

Phase 16 defines the minimum design controls required before later phases may test autonomous behavior in shadow mode or canary mode.

## Added in this phase

### Autonomous gate design service

Added `Phase16AutonomousGateServiceV2`.

It evaluates whether an autonomous candidate design is sufficiently controlled for later shadow-mode review.

The service always returns:

- `autonomous_execution_enabled=false`

### Design-only scope

Allowed:

- design review;
- evidence evaluation;
- shadow-mode readiness evaluation.

Not allowed:

- autonomous live execution;
- autonomous canary execution;
- unattended order submission;
- bypassing manual-live controls.

## Required controls

The autonomous gate requires:

- explicit `autonomous_live_candidate` mode;
- autonomous execution disabled during design phase;
- strategy allowlist;
- symbol allowlist;
- per-strategy operator approval;
- manual override;
- emergency halt;
- market data freshness gate;
- exchange connectivity gate;
- tiny risk limits;
- signal confidence threshold;
- backtest evidence;
- walk-forward evidence;
- shadow mode completion before canary;
- cooldown after loss;
- cooldown after exchange error;
- post-order reconciliation requirement;
- audit-chain requirement.

## Default limits

| Control | Default |
|---|---:|
| Allowed strategy | `ma_cross_risk_managed_v1` |
| Allowed symbols | BTC-USD, ETH-USD |
| Max order notional | 5 USD |
| Max daily notional | 25 USD |
| Max daily loss | 10 USD |
| Max drawdown | 2% |
| Max open positions | 1 |
| Minimum backtest trades | 30 |
| Minimum walk-forward windows | 3 |
| Minimum shadow days before canary | 14 |
| Max market data age | 30 seconds |
| Max reconciliation interval | 15 minutes |
| Loss cooldown | 1440 minutes |
| Exchange-error cooldown | 60 minutes |

## Evidence requirements

### Backtest evidence

The strategy must pass backtest validation and have enough trades to avoid a meaningless sample.

### Walk-forward evidence

The strategy must pass walk-forward validation across multiple windows.

### Shadow-mode evidence

The strategy must complete shadow mode before canary consideration. Shadow mode means the system makes decisions against live conditions without placing live orders.

## Stop conditions

Stop immediately if:

- autonomous execution is enabled during Phase 16;
- mode is not `autonomous_live_candidate`;
- strategy is not allowlisted;
- symbol is not allowlisted;
- operator has not approved the strategy;
- manual override is missing;
- emergency halt is missing;
- market data freshness gate is weak or missing;
- exchange connectivity gate is missing;
- risk limits exceed defaults;
- signal confidence threshold is missing or too low;
- backtest evidence is weak;
- walk-forward evidence is weak;
- shadow mode is incomplete;
- cooldowns are missing;
- reconciliation or audit-chain requirements are missing.

## Local validation

Run:

    cd backend
    python -m pytest tests/test_phase16_gate_design.py -q

## Phase 16 acceptance checklist

| Requirement | Status |
|---|---:|
| Autonomous gate design service exists | Complete |
| Design-only policy exists | Complete |
| Autonomous execution remains disabled | Complete |
| Explicit candidate mode is required | Complete |
| Strategy allowlist is enforced | Complete |
| Symbol allowlist is enforced | Complete |
| Operator strategy approval is required | Complete |
| Manual override is required | Complete |
| Emergency halt is required | Complete |
| Market data freshness gate is required | Complete |
| Exchange connectivity gate is required | Complete |
| Tiny risk limits are enforced | Complete |
| Signal confidence threshold is required | Complete |
| Backtest evidence is required | Complete |
| Walk-forward evidence is required | Complete |
| Shadow mode before canary is required | Complete |
| Cooldowns are required | Complete |
| Reconciliation and audit-chain controls are required | Complete |
| Phase 16 tests exist | Complete |
| Autonomous live execution added | No |
| Live order submission added | No |

## Next phase

Phase 17 should implement autonomous live shadow mode.

Shadow mode must make live-condition decisions without placing orders and must produce measurable would-have-traded evidence before any canary can be considered.
