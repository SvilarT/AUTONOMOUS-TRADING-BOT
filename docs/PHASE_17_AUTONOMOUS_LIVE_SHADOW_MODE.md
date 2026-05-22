# Phase 17 Autonomous Live Shadow Mode

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 17 adds autonomous live shadow mode. Shadow mode evaluates autonomous decisions against live-condition inputs but does not place orders and does not enable autonomous execution.

## Objective

Prove autonomous decision quality in live market conditions without touching real funds.

The system records what it would have done, why it would have done it, what risk controls decided, and what the simulated outcome would have been.

## Added in this phase

### Shadow mode service

Added `Phase17AutonomousShadowModeServiceV2`.

It supports:

- shadow input validation;
- would-have-traded decision construction;
- simulated fill assumptions;
- simulated quantity calculation;
- risk decision capture;
- halt assumption capture;
- reconciliation assumption capture;
- tamper-evident decision hash;
- shadow window review.

The service never submits live orders.

### Shadow decision requirements

Every shadow decision requires:

- explicit `shadow` mode;
- no live order submission flag;
- autonomous execution disabled;
- allowlisted strategy;
- allowlisted symbol;
- supported side: BUY, SELL, or HOLD;
- minimum confidence for BUY/SELL;
- fresh live-condition market data;
- capped shadow notional;
- risk decision artifact;
- halt assumption artifact;
- reconciliation assumption artifact.

### Shadow window review

A shadow window must satisfy:

- at least 14 shadow days;
- at least 50 decisions;
- at least one would-trade decision;
- simulated drawdown within limit;
- operational error rate within limit;
- no halt issues;
- no reconciliation issues;
- simulated P/L recorded.

### Default limits

| Control | Default |
|---|---:|
| Allowed strategies | `ma_cross_risk_managed_v1` |
| Allowed symbols | BTC-USD, ETH-USD |
| Minimum confidence for BUY/SELL | 0.70 |
| Max market data age | 30 seconds |
| Max shadow notional | 5 USD |
| Required shadow duration | 14 days |
| Minimum shadow decisions | 50 |
| Max simulated drawdown | 2% |
| Max error rate | 2% |

### Tests

Added `backend/tests/test_phase17_shadow_mode.py` covering:

- policy is shadow-only;
- valid shadow decision creates would-trade evidence without submission;
- HOLD can be valid below confidence threshold;
- live-submission flags and bad identity inputs are blocked;
- weak signal/stale data/bad size/missing artifacts are blocked;
- valid shadow window passes review;
- insufficient shadow evidence and operational issues block review.

## Operator workflow

### 1. Confirm Phase 16 gate design passed

Do not start shadow mode until the autonomous gate design is satisfied.

### 2. Run strategy decisions in shadow mode only

For every live-condition decision:

- use `mode=shadow`;
- keep autonomous execution disabled;
- record decision input;
- record risk decision;
- record simulated fill assumptions;
- record halt and reconciliation assumptions;
- record decision hash.

### 3. Review the shadow window

After the shadow window, evaluate:

- number of days;
- number of decisions;
- number of would-trade decisions;
- simulated P/L;
- max simulated drawdown;
- error rate;
- halt issues;
- reconciliation issues.

### 4. Stop if evidence is weak

Do not move to canary review unless:

- `ready_for_autonomous_canary_review=true`;
- `status=shadow_review_passed`;
- `blockers=[]`.

## Stop conditions

Stop immediately if:

- any live submission flag appears;
- autonomous execution is enabled;
- strategy is not allowlisted;
- symbol is not allowlisted;
- data is stale;
- risk decision artifact is missing;
- halt assumption is missing;
- reconciliation assumption is missing;
- error rate exceeds limit;
- simulated drawdown exceeds limit;
- halt or reconciliation issue occurs.

## Local validation

Run:

    cd backend
    python -m pytest tests/test_phase17_shadow_mode.py -q

## Phase 17 acceptance checklist

| Requirement | Status |
|---|---:|
| Shadow mode service exists | Complete |
| Shadow-only policy exists | Complete |
| Live order submission remains disallowed | Complete |
| Autonomous execution remains disabled | Complete |
| Strategy allowlist is enforced | Complete |
| Symbol allowlist is enforced | Complete |
| Confidence threshold is enforced for BUY/SELL | Complete |
| Fresh market data is required | Complete |
| Shadow notional cap is enforced | Complete |
| Risk decision artifact is required | Complete |
| Halt assumption artifact is required | Complete |
| Reconciliation assumption artifact is required | Complete |
| Decision hash is produced | Complete |
| Shadow window review exists | Complete |
| Shadow duration requirement exists | Complete |
| Shadow decision-count requirement exists | Complete |
| Simulated drawdown limit exists | Complete |
| Error-rate limit exists | Complete |
| Halt/reconciliation issue blockers exist | Complete |
| Phase 17 tests exist | Complete |
| Live order submission added | No |
| Autonomous live execution enabled | No |

## Next phase

Phase 18 should define autonomous live canary controls.

Canary must remain tiny, one strategy, one symbol, capped, auto-halted on anomaly, reconciled immediately, and reviewed before any scale-up.
