# Phase 8 Dashboard Pilot Review UI

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 8 adds frontend operator visibility for the manual live pilot review workflow. It does not submit live orders and does not enable autonomous live trading.

## Objective

Expose the Phase 5, Phase 6, and Phase 7 backend controls in the frontend so an operator can review readiness, reconciliation, pilot reports, signoffs, and expansion blockers without using raw API calls.

## Added in this phase

### Pilot review API helpers

Added frontend helpers for:

- pilot readiness;
- pilot expansion status;
- pending post-submit reconciliation;
- pilot reports;
- pilot signoffs;
- reconciliation resolution;
- pilot report generation;
- pilot signoff;
- unresolved reconciliation alert emission.

### Pilot review panel

Added `PilotReviewPanel`.

It displays:

- readiness status;
- expansion status;
- pending reconciliation count;
- readiness blockers;
- expansion blockers;
- pending reconciliation records;
- pilot reports;
- pilot signoffs.

It supports operator actions for:

- resolving reconciliation requirement records;
- building pilot reports;
- signing off pilot reports;
- emitting unresolved reconciliation alerts.

### Pilot review page

Added `PilotReviewPage` and authenticated route:

- `/pilot-review`

The page wraps the pilot review panel and provides navigation back to the dashboard.

## Safety boundary

Phase 8 does not:

- place live orders;
- enable autonomous live trading;
- loosen live gates;
- bypass readiness checks;
- bypass reconciliation requirements;
- bypass operator signoff.

## Operator workflow

1. Open `/pilot-review`.
2. Check readiness and expansion status.
3. Resolve any pending reconciliation only after live-readonly verification.
4. Build the pilot report for the selected live order id.
5. Review report hash and lifecycle state.
6. Record operator signoff with the correct decision.
7. Confirm expansion status is clear before considering another tiny pilot.

## Phase 8 acceptance checklist

| Requirement | Status |
|---|---:|
| Pilot review API helpers exist | Complete |
| Pilot review panel exists | Complete |
| Authenticated pilot review page exists | Complete |
| Readiness blockers are visible | Complete |
| Expansion blockers are visible | Complete |
| Pending reconciliation records are visible | Complete |
| Pilot reports are visible | Complete |
| Pilot signoffs are visible | Complete |
| Reconciliation resolution action exists | Complete |
| Pilot report generation action exists | Complete |
| Pilot signoff action exists | Complete |
| Unresolved reconciliation alert action exists | Complete |
| No automatic live order is submitted | Complete |
| No autonomous live trading is introduced | Complete |

## Note

The large dashboard-tab integration was not used because the connector rejected the large `Dashboard.js` rewrite. The safer integration is a dedicated authenticated `/pilot-review` page. A later frontend polish pass can add a navigation link or tab in the main dashboard header.

## Next phase

Phase 9 should focus on full regression, CI, route import validation, and frontend build verification.
