# Phase 4.5 Live Lifecycle Integration Follow-Up

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 4.5 closes the major implementation gap identified after Phase 4 by adding a dedicated manual live lifecycle coordinator. This prepares the project for the final service-level call-site wiring needed before a tiny manual live pilot.

## Objective

Add a controlled lifecycle layer for manually gated live orders without enabling autonomous live trading and without loosening any live gate.

## Completed in this phase

### Manual live lifecycle coordinator

Added `LiveManualOrderLifecycleServiceV2`.

It coordinates the already-existing safety primitives:

- `LiveOrderStateServiceV2`
- `LiveRiskDecisionServiceV2`
- `LivePreSubmitSafetyServiceV2`
- post-submit reconciliation requirement records

The coordinator does not place orders. It is intentionally separate from the exchange adapter and the live trading API entrypoint.

### Lifecycle responsibilities

The coordinator supports:

- beginning a live order lifecycle record;
- recording gate-checked state;
- persisting live risk decisions;
- recording approval state;
- running pre-submit safety checks;
- recording submitted state;
- mapping dry-run finalization to reconciled state;
- mapping filled live order finalization to reconciliation-pending state;
- mapping rejected/canceled responses to terminal states;
- recording adapter errors;
- creating post-submit reconciliation requirement records.

### Reconciliation requirement indexes

Added indexes for `live_post_submit_reconciliation_requirements`:

- by user/status/created time;
- unique sparse index by live order id.

### Tests

Added tests for:

- dry-run lifecycle completing to reconciled without a reconciliation requirement;
- filled non-dry-run lifecycle creating a pending reconciliation requirement;
- risk blocking for symbols outside the manual pilot allowlist;
- pre-submit active-halt blocking and moving the order to halted.

## Safety boundary

Phase 4.5 does not:

- enable autonomous live trading;
- loosen manual live gates;
- bypass signed approval requirements;
- place live orders directly;
- change exchange credentials;
- remove the adapter kill switch.

## Remaining pre-Phase-5 follow-up

The remaining step before a tiny real manual live pilot is to wire `LiveManualOrderLifecycleServiceV2` into `LiveTradingServiceV2` call-sites.

That wiring should be done as a small patch that:

- creates a lifecycle record before gate preflight;
- records gate-checked transition;
- persists risk decision;
- blocks when gate or risk denies;
- records approval state;
- runs pre-submit safety for non-dry-run orders;
- records submitted state after adapter call;
- records final state from normalized broker response;
- stores post-submit reconciliation requirement for every non-dry-run filled/acknowledged order;
- returns `live_order_id`, `risk_decision`, and `reconciliation_requirement` in the API response.

The GitHub connector rejected the direct `LiveTradingServiceV2` rewrite twice, so this phase lands the coordinator and tests first. The final call-site wiring should be performed in a narrower local patch or connector-safe micro-patch.

## Acceptance checklist

| Requirement | Status |
|---|---:|
| Dedicated lifecycle coordinator exists | Complete |
| Coordinator uses live order state machine | Complete |
| Coordinator persists live risk decisions | Complete |
| Coordinator runs pre-submit safety checks | Complete |
| Coordinator creates post-submit reconciliation requirements | Complete |
| Reconciliation requirement indexes exist | Complete |
| Dry-run lifecycle test exists | Complete |
| Non-dry-run filled lifecycle test exists | Complete |
| Risk block lifecycle test exists | Complete |
| Active halt lifecycle test exists | Complete |
| Autonomous live remains unavailable | Complete |

## Next step

Complete the final `LiveTradingServiceV2` call-site wiring, then proceed to Phase 5: Manual Live Pilot.
