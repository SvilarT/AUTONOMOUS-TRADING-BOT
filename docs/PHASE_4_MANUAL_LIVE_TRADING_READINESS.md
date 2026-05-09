# Phase 4 Manual Live Trading Readiness

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 4 prepares the project for a tightly controlled manual live pilot. It does not enable autonomous live trading and it does not loosen any existing live-trading gates.

## Objective

Move the platform from live-readonly reliability toward manual live execution readiness by strengthening broker response normalization, documenting the required live-order lifecycle, and defining the manual live pilot runbook.

## Completed in this phase

### Broker response normalization

`CoinbaseLiveExecutionAdapterV2.normalize_order_response` now maps Coinbase broker statuses into internal lifecycle-friendly statuses.

Normalized examples:

- Coinbase `open`, `pending`, `active`, or `received` becomes internal `acknowledged`.
- Coinbase `done` with filled size greater than zero becomes internal `filled`.
- Coinbase `done` with no filled size becomes internal `canceled`.
- Coinbase `settled` or `filled` becomes internal `filled`.
- Coinbase `cancelled` becomes internal `canceled`.
- Coinbase `rejected` remains internal `rejected`.
- Coinbase `failed` remains internal `failed`.

The normalized response keeps the original broker status in `broker_status` so operators can see both the internal lifecycle state and the raw exchange status.

### Live safety boundary tests

Added Phase 4 tests covering:

- filled-order normalization;
- canceled-order normalization;
- acknowledged-order normalization;
- rejected-order normalization;
- adapter-level kill switch behavior;
- risk decision blocking for symbols outside the manual live pilot allowlist.

### Manual live pilot readiness documentation

This document defines the control boundary for manual live pilot work and the required operator sequence before any real-money order is attempted.

## Manual live readiness boundary

Phase 4 readiness means the system is prepared for a future tiny manual live pilot only when every condition below is true:

| Condition | Required state |
|---|---:|
| Autonomous live trading | Disabled |
| Paper autonomous trading | Still paper-only |
| Live-readonly status | Fresh |
| Live-readonly reconciliation | Fresh and reviewed |
| Live execution path | Manual only |
| Live order size | Tiny pilot cap only |
| Symbol set | Small allowlist only |
| Signed approval challenge | Required for non-dry-run live order where configured |
| Adapter kill switch | Verified before pilot |
| Audit trail | Verified |
| Emergency halt | Verified |
| Post-submit reconciliation | Required after any real live order |

## Required manual live order lifecycle

A non-dry-run manual live order should follow this lifecycle:

1. Operator confirms trading mode and configuration.
2. Operator confirms live-readonly status is fresh.
3. Operator confirms latest reconciliation is fresh and acceptable.
4. Operator confirms emergency halt path is available.
5. Operator confirms the live adapter kill switch is understood and currently in the intended state.
6. Operator prepares a tiny order inside the symbol allowlist and notional cap.
7. System performs live gate checks.
8. System persists a live risk decision.
9. System requires manual approval where configured.
10. System submits the live order through the gated live service only.
11. System normalizes the broker response.
12. System records live audit data.
13. System requires post-submit live-readonly reconciliation.
14. Operator verifies exchange state against internal state.
15. Operator documents the pilot result.

## First manual live pilot constraints

Recommended first-pilot constraints:

| Control | Value |
|---|---:|
| Order notional | 1 to 5 USD |
| Daily live notional | 10 to 25 USD |
| Symbols | BTC-USD and/or ETH-USD only |
| Leverage | Disabled |
| Margin | Disabled |
| Derivatives | Disabled |
| Autonomous live | Disabled |
| Approval | Required for every non-dry-run order |
| Reconciliation | Required after every non-dry-run order |
| Kill switch | Verified immediately before and after pilot |

## Manual live pilot runbook

### 1. Preflight environment check

Confirm:

- backend is running in the intended environment;
- database connection is healthy;
- worker is healthy if needed for paper flows;
- live-readonly credentials are configured as readonly-capable;
- live execution credentials are restricted as much as the exchange supports;
- raw credentials are never printed in logs;
- dashboard mode and readiness panels are visible.

### 2. Verify live-readonly freshness

Run or trigger live-readonly snapshot and reconciliation.

Accept only if:

- latest live-readonly status is `fresh`;
- reconciliation report is fresh;
- account state is expected;
- no unexplained position drift exists.

### 3. Confirm live execution boundaries

Confirm:

- autonomous live trading is disabled;
- manual live execution is gated;
- live symbol allowlist is tiny;
- max live notional is tiny;
- signed approval requirement is configured as intended;
- emergency halt works;
- adapter kill switch works.

### 4. Dry-run first

Run the exact intended order as dry-run first.

Review:

- symbol;
- side;
- notional or base units;
- generated client order id;
- Coinbase payload preview;
- gate result;
- audit record;
- risk decision if applicable.

Do not continue if any field is unexpected.

### 5. Non-dry-run tiny manual order

Only after dry-run review:

- use the smallest acceptable notional;
- use an allowlisted symbol;
- supply the required approval token/challenge;
- ensure no unresolved live order exists;
- ensure fresh reconciliation requirements are satisfied;
- submit through `LiveTradingServiceV2` only.

### 6. Immediate post-submit verification

Immediately after submission:

- capture broker response;
- confirm normalized internal status;
- fetch recent readonly orders;
- fetch recent readonly fills;
- run live-readonly reconciliation;
- verify internal and exchange state agree;
- document fees, fill size, and final status.

### 7. Stop criteria

Stop immediately if any of the following occur:

- broker response is ambiguous;
- network error occurs after submit attempt;
- exchange order state cannot be verified;
- reconciliation is stale or mismatched;
- duplicate or unresolved order is detected;
- dashboard or API status is inconsistent;
- live kill switch fails to block when expected;
- any audit record is missing.

## No-blind-submit rule

If a live submit attempt has an ambiguous result, do not retry blindly.

Required recovery path:

1. Use live-readonly order lookup.
2. Use live-readonly fills lookup.
3. Reconcile exchange state against internal state.
4. Decide whether the exchange accepted, rejected, filled, or never received the order.
5. Only then decide the next action.

## Phase 4 acceptance checklist

| Requirement | Status |
|---|---:|
| Broker response normalization exists | Complete |
| Broker status is preserved separately | Complete |
| Adapter kill switch remains final guard | Complete |
| Manual live pilot constraints documented | Complete |
| Manual live pilot runbook documented | Complete |
| No-blind-submit policy documented | Complete |
| Live-readonly freshness remains required for pilot readiness | Complete |
| Autonomous live trading remains unavailable | Complete |
| Safety-boundary tests added | Complete |

## Remaining implementation follow-ups before Phase 5

Before the first real manual live pilot, the next implementation batch should complete the deeper live lifecycle integration that was intentionally left as the next controlled step:

- wire `LiveOrderStateServiceV2` transitions directly into `LiveTradingServiceV2` submit flow;
- persist risk decision identifiers in every live order response;
- persist post-submit reconciliation requirements for every non-dry-run live order;
- add an operator-facing live pilot checklist endpoint;
- add dashboard display for live pilot readiness.

## Next phase

Phase 5: Manual Live Pilot.

Phase 5 should execute only tiny human-approved live orders under strict operator control, with immediate post-submit readonly verification and reconciliation.
