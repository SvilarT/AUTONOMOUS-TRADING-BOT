# Phase 11 Full Dry-Run Dress Rehearsal

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 11 validates the complete manual live pilot workflow without placing a real order. It is the final rehearsal before any tiny human-approved live pilot.

## Objective

Prove that the manual live pilot flow works end-to-end in dry-run mode before the project touches real funds.

The rehearsal validates:

- backend startup;
- frontend build;
- configuration and secret hardening posture;
- live-readonly snapshot readiness;
- live-readonly reconciliation readiness;
- pilot readiness;
- exact dry-run manual order response shape;
- lifecycle metadata;
- risk decision metadata;
- audit metadata;
- dry-run reconciliation behavior;
- pilot report generation;
- operator signoff;
- expansion status.

## Added in this phase

### Dry-run rehearsal validation service

Added `Phase11DryRunRehearsalServiceV2`.

It does not place orders. It validates the artifacts produced by the existing Phase 5 through Phase 8 workflow.

The service exposes:

- rehearsal plan;
- readiness artifact validation;
- dry-run order artifact validation;
- pilot report/signoff artifact validation;
- final pass/fail status.

### Required dry-run order metadata

The exact manual dry-run order response must include:

- `live_order_id`;
- `gate`;
- `risk_decision`;
- `audit`;
- `reconciliation_requirement`.

### Fail-closed validation checks

The rehearsal fails if:

- pilot readiness is not ready;
- readiness blockers exist;
- dry-run response is missing lifecycle/risk/audit/reconciliation metadata;
- order status is not `dry_run`;
- any response indicates real live execution;
- gate did not allow the dry-run;
- risk decision did not allow the exact dry-run order;
- dry-run created a pending reconciliation requirement;
- pilot report hash is missing;
- expansion status remains blocked after signoff.

### Tests

Added `backend/tests/test_phase11_dry_run_rehearsal.py` covering:

- rehearsal plan contents;
- valid artifact pass state;
- missing metadata failure;
- accidental live-execution signal failure;
- readiness blocker failure;
- uncleared expansion-status failure.

### CI

Updated CI to run:

- `tests/test_phase11_dry_run_rehearsal.py`

## Operator workflow

### 1. Start from safe defaults

Recommended baseline before rehearsal:

- `TRADING_MODE=live-trading` only if intentionally testing the live-gated dry-run path;
- `LIVE_TRADING_ENABLED=true` only for the rehearsal window;
- `LIVE_EXECUTION_ADAPTER=coinbase_exchange_v2`;
- `LIVE_MANUAL_APPROVAL_REQUIRED=true`;
- `LIVE_MAX_ORDER_NOTIONAL_USD=5` preferred;
- `COINBASE_LIVE_ORDER_KILL_SWITCH=true` is acceptable for dry-run because no live submit should occur.

The dry-run path must not submit an exchange order.

### 2. Run backend and frontend checks

Backend:

    cd backend
    python -m pytest tests/test_phase11_dry_run_rehearsal.py -q

Frontend:

    cd frontend
    npm run build

### 3. Run configuration hardening checks

Run the Phase 10 hardening tests:

    cd backend
    python -m pytest \
      tests/test_phase10_config_hardening.py \
      tests/test_phase10_hardening_fail_closed.py \
      -q

### 4. Run live-readonly snapshot and reconciliation

Before dry-running the exact manual order, verify exchange state through readonly endpoints:

- `POST /api/live-readonly/snapshot`
- `POST /api/live-readonly/reconcile`
- `GET /api/live-readonly/status`

Proceed only if status is fresh and reconciliation is issue-free.

### 5. Check pilot readiness

Call:

- `GET /api/live-trading/pilot-readiness`

Proceed only if:

- `ready=true`;
- `status=ready`;
- `blockers=[]`.

### 6. Submit exact manual dry-run order

Use the same symbol, side, and notional intended for the future tiny live pilot, but set:

- `dry_run=true`

The response must include:

- `live_order_id`;
- `gate`;
- `risk_decision`;
- `audit`;
- `reconciliation_requirement`;
- nested `order.status=dry_run` or response `status=dry_run`;
- no real live execution flag.

### 7. Generate pilot report

Call:

- `POST /api/live-trading/pilot/report`

Use the dry-run `live_order_id`.

A report hash must be produced.

### 8. Sign off the rehearsal report

Call:

- `POST /api/live-trading/pilot/signoff`

Use a conservative decision such as:

- `hold` for rehearsal-only signoff; or
- `approved_for_next_tiny_pilot` only if the operator has reviewed every artifact and intends to proceed toward Phase 12.

### 9. Confirm expansion status

Call:

- `GET /api/live-trading/pilot/expansion-status`

The rehearsal is clean only when blockers are empty after report/signoff.

## Stop conditions

Stop immediately if:

- pilot readiness says `not_ready`;
- live-readonly data is missing or stale;
- reconciliation reports issues;
- dry-run response lacks required metadata;
- dry-run response indicates live execution;
- gate is denied;
- risk decision is denied;
- a pending post-submit reconciliation requirement is created for a dry-run;
- pilot report hash is missing;
- signoff fails;
- expansion status remains blocked.

## Phase 11 acceptance checklist

| Requirement | Status |
|---|---:|
| Dry-run rehearsal validation service exists | Complete |
| Rehearsal plan exists | Complete |
| Required dry-run metadata is enforced | Complete |
| Accidental live-execution signal is blocked | Complete |
| Readiness blockers fail rehearsal | Complete |
| Risk/gate metadata is validated | Complete |
| Dry-run reconciliation behavior is validated | Complete |
| Report/signoff/expansion artifacts are validated | Complete |
| Phase 11 tests exist | Complete |
| CI runs Phase 11 tests | Complete |
| No automatic live order is submitted | Complete |
| No autonomous live trading is introduced | Complete |

## Next phase

Phase 12 should be the first tiny human-approved manual live pilot.

Phase 12 must remain:

- one order only;
- tiny notional, preferably 1 to 5 USD;
- manually triggered;
- signed approval required;
- immediately reconciled;
- reported;
- signed off;
- stopped after completion.
