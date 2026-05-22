# Phase 18 Autonomous Live Canary Controls

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 18 defines the control gate for a future tiny autonomous canary. It does not submit orders and does not enable autonomous execution.

## Objective

Allow a future autonomous canary to be considered only after Phase 16 design review and Phase 17 shadow-mode review have passed.

The canary remains:

- one strategy;
- one symbol;
- one tiny order per day;
- one open order maximum;
- tiny notional;
- auto-halted on anomaly;
- reconciled immediately;
- alerted to operator;
- reported and signed off;
- blocked from scale-up until separate review.

## Added in this phase

### Canary control service

Added `Phase18AutonomousCanaryServiceV2`.

It evaluates:

- canary candidate eligibility;
- post-canary review evidence.

The service does not submit orders.

### Candidate requirements

A canary candidate requires:

- Phase 16 design gate satisfied;
- Phase 17 shadow review passed;
- explicit `autonomous_canary_candidate` mode;
- one allowlisted strategy;
- one allowlisted symbol;
- operator canary approval;
- max order notional no more than 2 USD;
- max daily notional no more than 2 USD;
- max daily loss no more than 2 USD;
- max one order per day;
- max one open order;
- global kill switch available;
- auto-halt after any anomaly;
- post-order reconciliation required;
- operator alert required;
- canary report required;
- canary signoff required;
- scale-up blocked until review;
- no pending reconciliation;
- no unresolved canary report;
- no active halt.

### Post-canary review requirements

A post-canary review requires:

- no more than one attempted order;
- no more than one filled order;
- no anomalies;
- no reconciliation issues;
- operator alert recorded;
- operator signoff recorded;
- realized loss within the tiny limit;
- scale-up still blocked.

### Default limits

| Control | Default |
|---|---:|
| Allowed strategy | `ma_cross_risk_managed_v1` |
| Allowed symbol | BTC-USD |
| Max order notional | 2 USD |
| Max daily notional | 2 USD |
| Max daily loss | 2 USD |
| Max orders per day | 1 |
| Max open orders | 1 |

### Tests

Added `backend/tests/test_phase18_canary_controls.py` covering:

- canary policy is single tiny candidate only;
- valid candidate passes review gate without submission;
- Phase 16, Phase 17, and explicit mode are required;
- bad strategy, symbol, and missing operator approval are blocked;
- bad limits and open orders are blocked;
- missing halt/post-order controls and unresolved state are blocked;
- valid post-canary summary passes;
- post-canary anomalies and scale-up failures are blocked.

## Operator workflow

### 1. Confirm Phase 16 and Phase 17 passed

Do not consider a canary unless:

- Phase 16 design gate is satisfied;
- Phase 17 shadow review passed.

### 2. Configure a one-order canary candidate

Use only:

- strategy: `ma_cross_risk_managed_v1`;
- symbol: BTC-USD;
- max order notional: 2 USD;
- max daily notional: 2 USD;
- max daily loss: 2 USD;
- max orders per day: 1;
- max open orders: 1.

### 3. Confirm operator approval

A human operator must explicitly approve the canary window before any future execution path is considered.

### 4. Confirm halt and post-order controls

Before canary consideration:

- global kill switch must be available;
- auto-halt after any anomaly must be enabled;
- post-order reconciliation must be required;
- operator alerting must be required;
- canary report must be required;
- canary signoff must be required;
- scale-up must remain blocked.

### 5. Review after canary

After any future canary attempt:

- confirm only one attempt occurred;
- confirm only one fill occurred;
- confirm no anomalies;
- confirm no reconciliation issues;
- confirm operator alert and signoff;
- confirm loss remained within tiny limit;
- confirm scale-up remains blocked.

## Stop conditions

Stop immediately if:

- Phase 16 did not pass;
- Phase 17 did not pass;
- mode is not explicit canary candidate mode;
- strategy is not allowlisted;
- symbol is not BTC-USD;
- operator approval is missing;
- notional/loss/order caps exceed defaults;
- kill switch availability is unclear;
- auto-halt is unavailable;
- post-order reconciliation is not mandatory;
- operator alerting is not mandatory;
- canary report/signoff is not mandatory;
- pending reconciliation exists;
- unresolved canary report exists;
- active halt exists;
- scale-up is not blocked.

## Local validation

Run:

    cd backend
    python -m pytest tests/test_phase18_canary_controls.py -q

## Phase 18 acceptance checklist

| Requirement | Status |
|---|---:|
| Canary control service exists | Complete |
| Candidate eligibility gate exists | Complete |
| Post-canary review gate exists | Complete |
| Phase 16 gate is required | Complete |
| Phase 17 review is required | Complete |
| Explicit canary candidate mode is required | Complete |
| One allowlisted strategy is required | Complete |
| One allowlisted symbol is required | Complete |
| Operator canary approval is required | Complete |
| Tiny notional/loss caps are enforced | Complete |
| One order per day is enforced | Complete |
| One open order maximum is enforced | Complete |
| Kill switch availability is required | Complete |
| Auto-halt after anomaly is required | Complete |
| Post-order reconciliation is required | Complete |
| Operator alert is required | Complete |
| Canary report/signoff is required | Complete |
| Scale-up remains blocked | Complete |
| Phase 18 tests exist | Complete |
| Live order submission added by this service | No |
| Autonomous execution enabled | No |

## Next phase

Phase 19 should define the final production live trading release gate.

Production release must require successful manual operation, successful shadow review, successful canary review, hardened operations, documented risk limits, incident response readiness, and separate gates for every live mode.
