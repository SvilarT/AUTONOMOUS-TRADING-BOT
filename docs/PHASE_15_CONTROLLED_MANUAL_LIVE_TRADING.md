# Phase 15 Controlled Manual Live Trading Release Gate

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 15 defines the final release gate for controlled repeated manual live trading. It does not place orders and does not enable autonomous live trading.

## Objective

Allow the system to enter a limited manual-live operating window only after reviewed pilot evidence and production operations readiness are both approved.

This phase is the first limited form of live-trading readiness, but it is still manual-only, low-notional, allowlisted, reconciled, and operator-controlled.

## Added in this phase

### Controlled manual live release service

Added `Phase15ControlledManualLiveServiceV2`.

It evaluates whether the system may enter controlled repeated manual live trading.

The service does not submit orders.

### Release scope

Allowed:

- limited repeated manual live trading only.

Not allowed:

- autonomous live trading;
- strategy-driven live execution;
- unattended live execution;
- unbounded manual execution;
- non-allowlisted symbols;
- unreconciled repeated trading.

### Default limits

| Control | Default |
|---|---:|
| Max order notional | 10 USD |
| Max daily notional | 50 USD |
| Max orders per day | 5 |
| Max open live orders | 1 |
| Symbols | BTC-USD, ETH-USD |

### Required controls

Controlled manual live trading requires:

- Phase 13 limited manual release approved;
- Phase 14 operations readiness approved;
- explicit `controlled_manual_live` mode;
- autonomous live disabled;
- manual approval required for every order;
- signed approval required for every order;
- exact dry run required before every order;
- post-order reconciliation required;
- pilot/order report required after every order;
- operator signoff required after every order;
- kill switch closed when idle;
- symbol allowlist enforced;
- per-order notional cap enforced;
- daily notional cap enforced;
- daily order count cap enforced;
- only one live order open at a time;
- no pending reconciliation;
- no unsigned completed report;
- no active halt.

### Tests

Added `backend/tests/test_phase15_manual_release_gate.py` covering:

- manual-only limited policy;
- valid configuration readiness;
- Phase 13 and Phase 14 prerequisites;
- autonomous mode blocking;
- missing human controls blocking;
- missing post-order controls blocking;
- bad symbol/notional/frequency/open-order limits blocking;
- unresolved live-state blocking.

## Operator workflow

### 1. Confirm prerequisites

Do not enter controlled manual live mode unless:

- Phase 13 approved limited manual release;
- Phase 14 reports operations ready;
- no pending reconciliation exists;
- no unsigned completed report exists;
- no active live halt exists.

### 2. Configure a manual-only operating window

Use only:

- `controlled_manual_live` mode;
- BTC-USD and ETH-USD;
- max order notional no more than 10 USD;
- max daily notional no more than 50 USD;
- max 5 orders per day;
- max 1 open live order.

### 3. Require dry run before every order

Every intended live order must first be rehearsed with the exact:

- symbol;
- side;
- notional or base amount;
- order path.

### 4. Require manual and signed approval

Every order must be explicitly approved by the operator.

### 5. Reconcile after every order

After every order:

- restore kill switch;
- fetch live-readonly orders;
- fetch live-readonly fills;
- run reconciliation;
- resolve post-submit requirement;
- build report;
- sign off;
- re-check release gate before continuing.

## Stop conditions

Stop immediately if:

- any reconciliation requirement remains pending;
- a report is unsigned;
- a halt is active;
- dry run does not match intended order;
- manual approval is missing;
- signed approval is missing;
- kill switch posture is unclear;
- max notional or daily limits would be exceeded;
- more than one live order would be open;
- operator cannot explain the current account state;
- any monitoring or alerting control fails.

## Local validation

Run:

    cd backend
    python -m pytest tests/test_phase15_manual_release_gate.py -q

## Phase 15 acceptance checklist

| Requirement | Status |
|---|---:|
| Controlled manual release service exists | Complete |
| Manual-only policy exists | Complete |
| Autonomous live is explicitly disallowed | Complete |
| Phase 13 approval is required | Complete |
| Phase 14 operations readiness is required | Complete |
| Explicit controlled manual mode is required | Complete |
| Manual approval is required for every order | Complete |
| Signed approval is required for every order | Complete |
| Dry-run-before-every-order is required | Complete |
| Reconciliation-after-every-order is required | Complete |
| Report/signoff-after-every-order is required | Complete |
| Kill switch closed when idle is required | Complete |
| Symbol allowlist is enforced | Complete |
| Per-order notional cap is enforced | Complete |
| Daily notional cap is enforced | Complete |
| Daily order count cap is enforced | Complete |
| Max open live orders is enforced | Complete |
| Unresolved live state blocks readiness | Complete |
| Phase 15 tests exist | Complete |
| Automatic live order submission added | No |
| Autonomous live trading introduced | No |

## Next phase

Phase 16 should design the autonomous live trading gate separately from manual live trading.

Autonomous live trading must remain impossible until its own independent design, shadow mode, canary release, and risk controls are complete.
