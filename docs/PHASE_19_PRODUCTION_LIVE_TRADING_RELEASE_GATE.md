# Phase 19 Production Live Trading Release Gate

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 19 defines the final production release gate. It does not submit orders and does not enable execution by itself.

## Objective

Evaluate whether the project is eligible for a controlled production-live release decision after all prior readiness layers are complete.

Production release requires evidence from:

- controlled manual live trading readiness;
- autonomous shadow-mode review;
- autonomous canary review;
- production operations readiness;
- CI and supply-chain checks;
- backup/restore and rollback validation;
- incident response readiness;
- risk controls;
- monitoring and alerting;
- unresolved-state checks;
- explicit release approval.

## Added in this phase

### Production release gate service

Added `Phase19ProductionLiveReleaseServiceV2`.

It evaluates a final release configuration and produces:

- `production_release_ready` or `blocked`;
- release blockers;
- full checklist output;
- release policy.

The service does not submit orders.

## Required release modes

Every mode must remain separately gated:

- `paper`
- `live_readonly`
- `controlled_manual_live`
- `autonomous_shadow`
- `autonomous_canary`
- `production_live`

## Required runbooks

Production release requires:

- deployment runbook;
- rollback runbook;
- backup/restore runbook;
- incident-response runbook;
- secret-rotation runbook;
- manual-live reconciliation runbook;
- autonomous shadow review runbook;
- autonomous canary review runbook;
- production-live release runbook.

## Required monitoring

Production release requires monitoring for:

- backend health;
- frontend health;
- worker heartbeat;
- database connectivity;
- market data freshness;
- exchange connectivity;
- unresolved reconciliation;
- unsigned report;
- active halt;
- daily loss;
- drawdown;
- open orders;
- order rejection rate.

## Required alerts

Production release requires alerts for:

- critical operations;
- reconciliation blockers;
- stale market data;
- degraded exchange connectivity;
- risk-limit breach;
- live halt trigger.

## Default release limits

| Control | Default |
|---|---:|
| Max order notional | 10 USD |
| Max daily notional | 50 USD |
| Max daily loss | 10 USD |
| Max drawdown | 2% |
| Max open orders | 1 |

## Blocking conditions

Production release is blocked if:

- Phase 15 controlled manual readiness is not approved;
- Phase 17 shadow review is not passed;
- Phase 18 canary review is not passed;
- Phase 14 operations readiness is not approved;
- release modes are not separately gated;
- runbooks are incomplete;
- monitoring is incomplete;
- alerting is incomplete;
- CI is not green;
- dependency audit is not green;
- security scan is not green;
- backup/restore is not validated;
- rollback is not validated;
- incident response is not ready;
- incident commander is missing;
- risk limits exceed defaults;
- kill switch, automatic halt, or manual override is not ready;
- post-order reconciliation/report/signoff is not locked;
- pending reconciliation exists;
- unsigned report exists;
- active halt exists;
- stale worker exists;
- open orders exceed cap;
- production release approval is missing;
- release approver is missing.

## Tests

Added `backend/tests/test_phase19_production_release_gate.py` covering:

- policy is final gate and does not submit orders;
- valid configuration is release-ready;
- missing phase prerequisites block release;
- missing modes/runbooks/monitors/alerts block release;
- CI/backup/rollback/incident failures block release;
- risk/halt/post-order failures block release;
- unresolved live state and missing approval block release.

## Operator workflow

### 1. Confirm phase evidence

Do not evaluate production release unless:

- Phase 15 controlled manual release gate is ready;
- Phase 17 shadow review passed;
- Phase 18 canary review passed;
- Phase 14 operations readiness is approved.

### 2. Confirm release mode separation

Verify every mode remains separately gated and cannot accidentally activate another mode.

### 3. Confirm operational readiness

Verify all runbooks, monitors, alerts, rollback, backup/restore, incident response, and ownership requirements are complete.

### 4. Confirm risk lock

Verify production release limits remain locked:

- max order notional;
- max daily notional;
- max daily loss;
- max drawdown;
- max open orders.

### 5. Confirm no unresolved state

Before release:

- no pending reconciliation;
- no unsigned reports;
- no active halt;
- no stale workers;
- no excess open orders.

### 6. Record release approval

Production release requires explicit approval and an approver identity.

## Stop conditions

Stop immediately if:

- any prerequisite phase is not approved;
- any runbook is missing;
- any monitor or alert channel is missing;
- rollback is untested;
- backup/restore is untested;
- CI/security/audit is failing;
- incident response is unclear;
- unresolved live state exists;
- risk limits are not locked;
- halt or override controls are uncertain;
- production approval is missing.

## Local validation

Run:

    cd backend
    python -m pytest tests/test_phase19_production_release_gate.py -q

## Phase 19 acceptance checklist

| Requirement | Status |
|---|---:|
| Production release gate service exists | Complete |
| Final release policy exists | Complete |
| Service does not submit orders | Complete |
| Phase 15 readiness is required | Complete |
| Phase 17 shadow review is required | Complete |
| Phase 18 canary review is required | Complete |
| Phase 14 operations readiness is required | Complete |
| Separate release modes are required | Complete |
| Complete runbooks are required | Complete |
| Complete monitoring is required | Complete |
| Complete alerting is required | Complete |
| CI/supply-chain checks are required | Complete |
| Backup/restore validation is required | Complete |
| Rollback validation is required | Complete |
| Incident response readiness is required | Complete |
| Risk limits are locked | Complete |
| Kill switch/halt/override readiness is required | Complete |
| Post-order reconciliation/report/signoff is required | Complete |
| Unresolved live state blocks release | Complete |
| Explicit release approval is required | Complete |
| Phase 19 tests exist | Complete |
| Live order submission added by this service | No |

## Final status

After Phase 19, the repository has a complete staged path from paper trading through controlled production release gates.

A real production release still requires actually satisfying the evidence represented by these gates in the deployment environment, not merely having the code present.
