# Live Order Safety Gate A

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

This document defines the minimum controls required before any non-dry-run live order may proceed.

## Implemented controls

### 1. Signed approval challenge

Non-dry-run live market orders require a signed, payload-bound, single-use approval challenge.

### 2. Live order state machine

`LiveOrderStateServiceV2` records hash-chained order transitions:

```text
requested -> gate_checked -> risk_checked -> approval_required -> approved -> submitted -> acknowledged -> filled/partially_filled/rejected/canceled -> reconciliation_pending -> reconciled/failed/halted
```

Invalid transitions are rejected and transition chains can be verified.

### 3. Pre-submit safety blocker

`LivePreSubmitSafetyServiceV2` blocks non-dry-run live order submission when:

- a global or user live halt is active;
- the user has an unresolved live order;
- fresh live-readonly reconciliation is required and stale/missing.

### 4. Persisted live risk decision

`LiveRiskDecisionServiceV2` persists allow/block decisions and check details for live order preflight.

### 5. No-blind-submit policy

`LiveSubmitPolicyV2` documents and enforces the rule that ambiguous live submit results must be recovered through readonly exchange lookup and reconciliation before any new submit attempt.

## Environment flags

```bash
LIVE_SIGNED_APPROVAL_REQUIRED=True
LIVE_REQUIRE_FRESH_RECONCILIATION=True
LIVE_MAX_RECONCILIATION_AGE_SECONDS=300
```

## Operational rule

A live order is not eligible to submit unless all of the following are true:

```text
trading:live-execute scope present
signed approval challenge valid and unused
no active halt
no unresolved live order
fresh reconciliation exists
risk decision allows order
kill switch disabled only during approved execution window
```

## Next work

The remaining production-live work is to integrate the state machine transitions deeper into the adapter response lifecycle, add broker response normalization, and run a manual live pilot under tiny notional caps.
