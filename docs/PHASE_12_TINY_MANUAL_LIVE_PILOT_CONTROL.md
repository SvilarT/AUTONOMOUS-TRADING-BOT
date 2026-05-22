# Phase 12 Tiny Manual Live Pilot Control

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 12 adds the software control layer for the first tiny human-approved manual live pilot. It does not place a real trade and does not enable autonomous live trading.

## Objective

Before any real tiny manual order is attempted by a human operator, the system must prove that the candidate pilot order is eligible and that prior pilot/reconciliation state is clear.

## Added in this phase

### Tiny manual pilot control service

Added `Phase12TinyManualLivePilotServiceV2`.

The service does not submit orders. It validates whether an operator may proceed to the existing manually gated order endpoint for exactly one tiny pilot attempt.

### Eligibility checks

The service verifies:

- operator provides the exact acknowledgement text;
- first pilot symbol is restricted to BTC-USD or ETH-USD;
- side is BUY or SELL;
- notional is positive and capped at the tiny pilot limit;
- Phase 5 pilot readiness is clear;
- Phase 7 expansion status is clear;
- no pending reconciliation exists;
- no unsigned completed pilot report exists;
- a successful dry-run artifact exists;
- the dry-run artifact does not indicate live execution;
- the dry-run artifact exactly matches the candidate symbol, side, and notional.

### Pilot plan

The plan enforces:

- one order only;
- human-triggered only;
- tiny notional, preferred 1 to 5 USD;
- BTC-USD or ETH-USD only;
- immediate post-submit reconciliation;
- report generation;
- operator signoff;
- stop after one order.

### Tests

Added `backend/tests/test_phase12_tiny_manual_live_pilot_control.py` covering:

- one-order human-triggered plan;
- valid candidate eligibility;
- exact acknowledgement requirement;
- symbol allowlist blocking;
- notional cap blocking;
- readiness failure blocking;
- pending reconciliation blocking;
- dry-run mismatch blocking;
- accidental live-execution signal blocking.

## Operator workflow

### 1. Confirm Phase 11 rehearsal passed

Do not proceed unless the full dry-run dress rehearsal passed.

### 2. Use one intended order only

Choose one tiny candidate:

- BTC-USD or ETH-USD;
- BUY or SELL;
- 1 to 5 USD preferred.

### 3. Run exact dry-run first

The exact intended live pilot order must first be submitted with `dry_run=true`.

The dry-run artifact must match:

- symbol;
- side;
- notional.

### 4. Evaluate Phase 12 eligibility

The candidate is eligible only if the service returns:

- `eligible_for_one_tiny_manual_live_pilot=true`;
- `status=eligible`;
- `blockers=[]`.

### 5. Human operator may proceed manually

Only after eligibility passes, the human operator may use the existing manual live endpoint for the single tiny pilot attempt.

The service added in this phase does not submit that order.

### 6. Immediately after submit

After the human-triggered pilot attempt:

- restore kill switch;
- fetch readonly orders;
- fetch readonly fills;
- run readonly reconciliation;
- resolve post-submit reconciliation requirement;
- build pilot report;
- sign off;
- stop.

## Stop conditions

Stop immediately if:

- acknowledgement is missing or not exact;
- symbol is not BTC-USD or ETH-USD;
- notional exceeds tiny cap;
- readiness is not clear;
- expansion status is blocked;
- any pending reconciliation exists;
- any unsigned completed pilot report exists;
- dry-run artifact is missing;
- dry-run artifact does not exactly match the intended candidate;
- dry-run artifact indicates real execution;
- operator cannot explain every artifact.

## Local validation

Run:

    cd backend
    python -m pytest tests/test_phase12_tiny_manual_live_pilot_control.py -q

## CI note

The connector blocked a workflow-file patch that added this Phase 12 test to CI. The test exists and should be added to CI later as a narrow local patch.

## Phase 12 acceptance checklist

| Requirement | Status |
|---|---:|
| Tiny pilot control service exists | Complete |
| One-order plan exists | Complete |
| Exact acknowledgement is required | Complete |
| Symbol allowlist is enforced | Complete |
| Tiny notional cap is enforced | Complete |
| Readiness must be clear | Complete |
| Expansion status must be clear | Complete |
| Pending reconciliation blocks eligibility | Complete |
| Unsigned completed report blocks eligibility | Complete |
| Dry-run-first behavior is enforced | Complete |
| Dry-run must match exact candidate | Complete |
| Accidental live-execution signal blocks eligibility | Complete |
| Phase 12 tests exist | Complete |
| Automatic live order submission added | No |
| Autonomous live trading introduced | No |

## Next phase

Phase 13 should review the first pilot result and define limited manual live release criteria.
