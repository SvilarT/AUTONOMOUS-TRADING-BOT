# Phase 13 Pilot Review and Limited Manual Live Release Criteria

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 13 defines the review gate between a one-order tiny manual pilot and limited repeated manual live trading. It does not place live orders and does not enable autonomous live trading.

## Objective

Decide, from recorded evidence, whether the system may move from a single tiny pilot attempt to limited repeated manual live trading under strict controls.

## Added in this phase

### Pilot release criteria service

Added `Phase13PilotReleaseServiceV2`.

It evaluates:

- pilot reports;
- operator signoffs;
- post-submit reconciliation requirements;
- requested release notional;
- requested release symbols.

The service records a deterministic release decision but does not submit orders.

### Release scope

The only release scope is:

- limited repeated manual live trading.

Autonomous live trading remains explicitly disallowed.

### Required evidence

A limited manual release requires:

- at least one complete pilot report;
- a report hash;
- a valid operator signoff;
- resolved post-submit reconciliation;
- no pending reconciliation requirements;
- no unsigned completed pilot reports;
- no blocking operator decision;
- requested notional remains limited;
- requested symbols remain allowlisted.

### Blocking decisions

Any of these block release:

- `hold`
- `reject`
- `manual_investigation_required`

### Approving decisions

These may count as reviewed evidence:

- `approved_for_next_tiny_pilot`
- `approved_for_limited_manual_live`

### Limits

Default limited-release constraints:

- max release notional: 10 USD;
- allowed symbols: BTC-USD and ETH-USD only;
- manual live only;
- no autonomous live trading.

### Tests

Added `backend/tests/test_phase13_pilot_release_criteria.py` covering:

- policy explicitly blocks autonomous live trading;
- approved pilot evidence allows limited manual release;
- missing reviewed pilot blocks release;
- pending reconciliation blocks release;
- unsigned complete report blocks release;
- hold/reject/investigation decisions block release;
- large requested release notional blocks release;
- non-allowlisted symbols block release.

## Operator workflow

### 1. Complete Phase 12

Do not evaluate limited manual release until a one-order tiny manual pilot has been completed and stopped.

### 2. Confirm post-submit reconciliation is resolved

The pilot order must have a resolved post-submit reconciliation requirement.

### 3. Build the pilot report

The pilot report must be complete and must include a report hash.

### 4. Record operator signoff

The signoff must be explicit. If the operator is uncertain, use `manual_investigation_required` and stop.

### 5. Evaluate Phase 13 release criteria

Limited release is allowed only when:

- `approved_for_limited_manual_live=true`;
- `status=approved_for_limited_manual_live`;
- `blockers=[]`.

### 6. Keep limited manual release conservative

Even after approval:

- keep BTC-USD and ETH-USD only;
- keep max notional no higher than 10 USD;
- keep every order manually approved;
- reconcile after every order;
- stop on any anomaly.

## Stop conditions

Stop immediately if:

- no reviewed pilot exists;
- any reconciliation requirement is pending;
- a complete report lacks signoff;
- a signoff says hold, reject, or manual investigation required;
- report hash is missing;
- requested notional exceeds the limited-release cap;
- requested symbol is not allowlisted;
- operator cannot explain the pilot outcome.

## Local validation

Run:

    cd backend
    python -m pytest tests/test_phase13_pilot_release_criteria.py -q

## Phase 13 acceptance checklist

| Requirement | Status |
|---|---:|
| Pilot release criteria service exists | Complete |
| Release policy exists | Complete |
| Autonomous live is explicitly disallowed | Complete |
| Complete pilot report is required | Complete |
| Operator signoff is required | Complete |
| Resolved reconciliation is required | Complete |
| Pending reconciliation blocks release | Complete |
| Unsigned complete report blocks release | Complete |
| Blocking operator decisions block release | Complete |
| Limited notional cap is enforced | Complete |
| Symbol allowlist is enforced | Complete |
| Phase 13 tests exist | Complete |
| Automatic live order submission added | No |
| Autonomous live trading introduced | No |

## Next phase

Phase 14 should harden production operations:

- deployment runbook;
- rollback plan;
- monitoring and alerting;
- log redaction checks;
- backup/restore strategy;
- incident response checklist;
- unresolved reconciliation and unsigned report alerts;
- production CORS and secret verification.
