# Phase 6 Tiny Manual Live Pilot Execution Workflow

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 6 adds the operator workflow around a tiny manually approved live pilot. It does not place live orders automatically.

## Objective

Make the first human-triggered manual live pilot auditable, reconcilable, and reportable before any broader live rollout.

## Added in this phase

### Manual live pilot workflow service

Added `ManualLivePilotWorkflowServiceV2`.

It supports:

- listing pending post-submit reconciliation requirements;
- resolving a post-submit reconciliation requirement;
- building an immutable pilot report;
- listing previous pilot reports.

The service does not submit orders.

### API endpoints

Added:

- `GET /api/live-trading/pilot/pending-reconciliation`
- `POST /api/live-trading/pilot/resolve-reconciliation`
- `POST /api/live-trading/pilot/report`
- `GET /api/live-trading/pilot/reports`

### Pilot report contents

A pilot report includes:

- user id;
- live order id;
- generated timestamp;
- lifecycle transition count;
- lifecycle transitions;
- post-submit reconciliation requirement;
- audit count;
- live audit records;
- latest live-readonly status;
- latest live-readonly reconciliation report;
- live audit chain verification;
- report hash.

### Indexes

Added indexes for:

- pilot reports by user and generated timestamp;
- unique report per user/live order id;
- unique sparse report hash.

### Tests

Added tests for:

- pending reconciliation requirement visibility;
- resolving pending reconciliation requirements;
- missing reconciliation requirement resolution;
- pilot report generation and hashing;
- pilot report listing.

## Operator workflow

### 1. Confirm pilot readiness

Call:

- `GET /api/live-trading/pilot-readiness`

Proceed only if:

- `ready` is true;
- `blockers` is empty.

### 2. Dry-run the exact intended order

Submit a dry-run order through the manual live endpoint.

Review:

- symbol;
- side;
- notional/base units;
- gate result;
- risk decision;
- live order id;
- lifecycle state;
- audit record.

### 3. Submit tiny non-dry-run order only if approved

The non-dry-run step must remain human-triggered.

Pilot constraints:

- 1 to 5 USD notional preferred;
- BTC-USD or ETH-USD only;
- signed approval required;
- adapter kill switch open only during the submit window;
- immediately verify exchange state after submit.

### 4. Check pending reconciliation

Call:

- `GET /api/live-trading/pilot/pending-reconciliation`

A non-dry-run accepted/acknowledged/filled order should create a pending requirement.

### 5. Run live-readonly verification

Call:

- `POST /api/live-readonly/snapshot`
- `GET /api/live-readonly/orders`
- `GET /api/live-readonly/fills`
- `POST /api/live-readonly/reconcile`

Operator must verify:

- exchange order exists or was safely absent;
- fills match expectation;
- internal and exchange state reconcile;
- no ambiguous pending state remains.

### 6. Resolve the reconciliation requirement

Call:

- `POST /api/live-trading/pilot/resolve-reconciliation`

Use notes that explain the verification outcome.

Example resolution values:

- `verified_filled_and_reconciled`
- `verified_rejected_no_position_change`
- `verified_canceled_no_position_change`
- `verified_not_received_no_position_change`
- `manual_investigation_required`

If the outcome is ambiguous, use `manual_investigation_required` and stop.

### 7. Build pilot report

Call:

- `POST /api/live-trading/pilot/report`

Store the report hash in the operator notes.

### 8. Stop until reviewed

After a pilot order, stop and review:

- report hash;
- audit chain verification;
- lifecycle transitions;
- broker status;
- reconciliation result;
- fees and fill size;
- any operator notes.

Do not run repeated live pilots until the first report is reviewed.

## Stop conditions

Stop immediately if:

- readiness says `not_ready`;
- dry run output differs from the intended order;
- signed approval fails;
- exchange response is ambiguous;
- live-readonly order/fill lookup is stale or unavailable;
- reconciliation is stale or mismatched;
- post-submit requirement cannot be resolved confidently;
- audit chain verification fails;
- pilot report cannot be generated.

## Phase 6 acceptance checklist

| Requirement | Status |
|---|---:|
| Pending post-submit reconciliation visibility exists | Complete |
| Reconciliation resolution endpoint exists | Complete |
| Pilot report generation exists | Complete |
| Pilot report listing exists | Complete |
| Pilot report hash exists | Complete |
| Pilot report indexes exist | Complete |
| Workflow tests exist | Complete |
| No autonomous live trading is introduced | Complete |
| No automatic live order is submitted | Complete |

## Next phase

Phase 7 should focus on pilot result review and expansion control:

- dashboard pilot report UI;
- operator signoff records;
- repeated pilot prevention until signoff;
- expanded end-to-end dry-run tests;
- optional alerting for unresolved reconciliation requirements.
