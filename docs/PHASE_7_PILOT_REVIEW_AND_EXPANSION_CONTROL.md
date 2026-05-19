# Phase 7 Pilot Result Review and Expansion Control

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 7 adds the review and expansion-control layer after a tiny manual pilot. It does not submit orders and does not enable autonomous live trading.

## Objective

Prevent repeated manual pilot attempts until the prior pilot has been reconciled, reported, reviewed, and signed off by an operator.

## Added in this phase

### Manual live pilot review service

Added `ManualLivePilotReviewServiceV2`.

It supports:

- expansion status checks;
- unsigned completed report detection;
- unresolved reconciliation detection;
- operator signoff records;
- signoff listing;
- unresolved reconciliation alert emission.

### API endpoints

Added:

- `GET /api/live-trading/pilot/expansion-status`
- `POST /api/live-trading/pilot/signoff`
- `GET /api/live-trading/pilot/signoffs`
- `POST /api/live-trading/pilot/unresolved-reconciliation-alerts`

### Expansion control

The system blocks repeated pilot expansion when:

- any post-submit reconciliation requirement is still pending;
- any completed pilot report has no operator signoff.

### Operator signoff records

A signoff record includes:

- user id;
- live order id;
- operator id;
- decision;
- notes;
- report hash;
- signed timestamp;
- signoff hash.

Valid decisions:

- `approved_for_next_tiny_pilot`
- `hold`
- `reject`
- `manual_investigation_required`

### Unresolved reconciliation alerts

The review service can emit deduplicated critical alerts when post-submit reconciliation remains unresolved.

### Indexes

Added indexes for:

- pilot signoffs by user and signed timestamp;
- unique signoff per user/live order id;
- unique sparse signoff hash.

## Operator workflow

### 1. Resolve post-submit reconciliation

Before signoff, the operator must resolve any pending post-submit reconciliation requirement.

### 2. Generate a pilot report

The pilot report must be complete and hashed.

### 3. Review the report

Review:

- lifecycle transitions;
- audit records;
- audit chain verification;
- latest live-readonly state;
- latest reconciliation report;
- report hash;
- operator notes.

### 4. Sign off or hold

Use the signoff endpoint to record one of the allowed decisions.

`approved_for_next_tiny_pilot` means the prior tiny pilot was reviewed and the operator may consider the next tiny pilot if readiness checks also pass.

`hold`, `reject`, and `manual_investigation_required` keep expansion blocked operationally.

### 5. Check expansion status

Call the expansion-status endpoint before any repeated pilot.

Do not proceed if:

- `allowed_to_repeat_pilot` is false;
- any blockers are present.

## Stop conditions

Stop immediately if:

- reconciliation is pending;
- pilot report is incomplete;
- report hash is missing;
- audit chain fails verification;
- operator cannot explain the result;
- signoff decision is `hold`, `reject`, or `manual_investigation_required`;
- expansion status reports blockers.

## Test note

The GitHub connector safety filter blocked the Phase 7 test file write twice. The intended tests should cover:

- unsigned completed report blocks expansion;
- pending reconciliation blocks signoff;
- resolved reconciliation permits signoff;
- signoff clears unsigned-report blocker;
- unresolved reconciliation alerts are deduplicated;
- invalid signoff decisions are rejected.

These should be added locally or through a later connector-safe patch.

## Phase 7 acceptance checklist

| Requirement | Status |
|---|---:|
| Pilot review service exists | Complete |
| Expansion status endpoint exists | Complete |
| Operator signoff endpoint exists | Complete |
| Signoff listing endpoint exists | Complete |
| Unresolved reconciliation alert endpoint exists | Complete |
| Signoff indexes exist | Complete |
| Repeated pilot blocked without signoff | Complete |
| Pending reconciliation blocks expansion | Complete |
| No automatic live order is submitted | Complete |
| No autonomous live trading is introduced | Complete |
| Phase 7 tests | Blocked by connector filter; follow-up required |

## Next phase

Phase 8 should add dashboard UI for pilot reports, expansion status, signoff records, and unresolved reconciliation alerts.
