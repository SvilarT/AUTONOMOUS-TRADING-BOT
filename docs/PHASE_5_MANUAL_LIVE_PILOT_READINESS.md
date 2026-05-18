# Phase 5 Manual Live Pilot Readiness

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 5 does not place live orders automatically. It adds the final readiness gate and operator checklist required before a tiny human-approved manual live pilot.

## Objective

Expose a deterministic ready/not-ready gate for the first manual live pilot, based on live-readonly freshness, reconciliation state, active halt state, pending post-submit reconciliation requirements, live gate configuration, and adapter kill-switch posture.

## Added in this phase

### Manual live pilot readiness service

Added `ManualLivePilotReadinessServiceV2`.

It evaluates whether a user is ready for a tiny manual live pilot. It does not place orders.

### Readiness API endpoint

Added:

- `GET /api/live-trading/pilot-readiness`

The endpoint returns:

- `ready`
- `status`
- `blockers`
- full check list
- trading mode metadata
- live gate metadata
- live-readonly snapshot status
- latest reconciliation status
- pending post-submit reconciliation requirements
- active live halts

### Pilot readiness checks

The readiness service checks:

- autonomous live remains disabled by design;
- trading mode is `live-trading` for the pilot window;
- global live gate is enabled;
- execution adapter matches the required adapter;
- manual approval remains required;
- signed approval remains required;
- live-readonly snapshot is fresh;
- live-readonly reconciliation is fresh, ok, and issue-free;
- no previous post-submit reconciliation requirement is pending;
- no active global/user halt exists;
- adapter kill switch is open only for the intentional submit window;
- max live order notional remains tiny.

### Tests

Added tests for:

- missing snapshot/reconciliation blockers;
- pending reconciliation and active halt blockers;
- fully ready checklist state;
- stale reconciliation blocker.

## Operator workflow

### 1. Keep live trading disabled by default

Default posture should remain:

- autonomous bot: paper-only;
- manual live execution: gated;
- adapter kill switch: enabled except during the exact pilot submit window.

### 2. Run live-readonly snapshot

Call the live-readonly snapshot endpoint and verify account state is expected.

### 3. Run live-readonly reconciliation

Call the live-readonly reconciliation endpoint and confirm:

- status is `ok`;
- issue count is zero;
- snapshot hash is present;
- checked timestamp is fresh.

### 4. Check pilot readiness

Call:

- `GET /api/live-trading/pilot-readiness`

Do not proceed unless `ready` is `true` and `blockers` is empty.

### 5. Dry-run the exact intended order

Use the exact symbol, side, and size intended for the pilot, but keep `dry_run=true`.

Review:

- gate result;
- risk decision;
- live order id;
- lifecycle metadata;
- payload preview;
- audit entry.

### 6. Non-dry-run tiny pilot order

Only after a clean dry run and ready checklist:

- use a tiny notional, preferably 1 to 5 USD;
- use BTC-USD or ETH-USD only;
- use signed approval;
- keep the submit window short;
- immediately restore kill-switch posture after the submit attempt.

### 7. Immediate post-submit reconciliation

After any non-dry-run submit attempt:

- fetch live-readonly orders;
- fetch live-readonly fills;
- run live-readonly reconciliation;
- resolve the post-submit reconciliation requirement;
- do not place another live order while any requirement is pending.

## Stop conditions

Stop immediately if:

- readiness returns `not_ready`;
- live-readonly snapshot is stale or missing;
- reconciliation is stale, missing, or mismatched;
- any previous post-submit reconciliation remains pending;
- any active halt exists;
- broker response is ambiguous;
- adapter kill switch behavior is not exactly understood;
- the dashboard/API status disagrees with exchange state.

## Phase 5 acceptance checklist

| Requirement | Status |
|---|---:|
| Manual live pilot readiness service exists | Complete |
| Readiness API endpoint exists | Complete |
| Fresh live-readonly snapshot is required | Complete |
| Fresh issue-free reconciliation is required | Complete |
| Pending post-submit reconciliation blocks readiness | Complete |
| Active halt blocks readiness | Complete |
| Tiny notional cap is checked | Complete |
| Manual/signed approval requirements are checked | Complete |
| Adapter kill-switch posture is checked | Complete |
| Tests cover ready and blocked states | Complete |
| No autonomous live trading is introduced | Complete |

## Next phase

Phase 6 should be the first manual live pilot execution workflow. It should remain human-triggered and tiny. The system should record the pilot result, resolve post-submit reconciliation, and produce a pilot report before any further live work.
