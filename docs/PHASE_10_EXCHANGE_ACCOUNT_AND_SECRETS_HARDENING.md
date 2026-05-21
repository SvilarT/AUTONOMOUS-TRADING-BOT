# Phase 10 Exchange Account and Secrets Hardening

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 10 hardens local configuration and operator process before the project moves into full dry-run rehearsal with live exchange credentials. It does not place live orders and does not enable autonomous live trading.

## Objective

Make the system safe enough to hold live exchange credentials by adding fail-closed configuration checks, redaction helpers, CI validation, and an operator runbook for exchange key setup.

## Added in this phase

### Secret hardening service

Added `SecretHardeningServiceV2`.

It provides:

- sensitive setting name detection;
- deterministic secret fingerprinting;
- value redaction;
- mapping redaction;
- text redaction;
- live credential posture evaluation;
- redacted settings diagnostics;
- fail-closed checks for unsafe live configuration.

### Hardening checks

The service evaluates:

- exchange credentials are present when `TRADING_MODE` is `live-readonly` or `live-trading`;
- configured exchange credential values are not obvious placeholders;
- production `JWT_SECRET` strength;
- `LIVE_TRADING_ENABLED` only runs with `TRADING_MODE=live-trading`;
- live execution adapter is locked to `coinbase_exchange_v2` in live-trading mode;
- manual live approval token exists when manual approval is required;
- live order notional cap remains tiny before expansion;
- Coinbase live order kill switch stays closed outside the exact submit window;
- wildcard CORS is not used outside debug mode;
- frontend-prefixed environment variables do not look like secrets.

### Tests

Added Phase 10 tests for:

- import/report smoke coverage;
- text redaction;
- live-readonly fail-closed behavior without exchange configuration;
- kill-switch fail-closed behavior outside live-trading mode;
- max-notional fail-closed behavior.

### CI

Updated CI to explicitly run Phase 10 hardening tests:

- `tests/test_phase10_config_hardening.py`
- `tests/test_phase10_hardening_fail_closed.py`

## Exchange key policy

Before any live dry-run rehearsal or tiny manual live pilot, create separate exchange API keys.

### Readonly key

Use the readonly key for:

- account snapshots;
- balances;
- positions;
- orders/fills lookup;
- reconciliation.

Required policy:

- read permission only;
- no trade permission;
- no withdrawal permission;
- no transfer permission if configurable;
- no margin/futures/derivatives permission;
- IP restriction if available;
- unique label such as `autonomous-trading-bot-readonly`.

### Execution key

Use the execution key only for gated manual live execution.

Required policy:

- trade permission only if required for spot orders;
- no withdrawal permission;
- no transfer permission if configurable;
- no margin/futures/derivatives permission;
- IP restriction if available;
- unique label such as `autonomous-trading-bot-manual-execution`;
- rotate immediately after any suspected exposure.

## Environment variable policy

### Required safe defaults

Default non-pilot posture:

- `TRADING_MODE=paper`
- `LIVE_TRADING_ENABLED=false`
- `LIVE_EXECUTION_ADAPTER=disabled`
- `COINBASE_LIVE_ORDER_KILL_SWITCH=true`
- `LIVE_MANUAL_APPROVAL_REQUIRED=true`
- `LIVE_MAX_ORDER_NOTIONAL_USD=25` or lower

### Live-readonly posture

Use for exchange observation and reconciliation:

- `TRADING_MODE=live-readonly`
- `LIVE_TRADING_ENABLED=false`
- `LIVE_EXECUTION_ADAPTER=disabled`
- `COINBASE_LIVE_ORDER_KILL_SWITCH=true`

### Tiny manual live submit-window posture

Use only during the exact manually approved pilot submit window:

- `TRADING_MODE=live-trading`
- `LIVE_TRADING_ENABLED=true`
- `LIVE_EXECUTION_ADAPTER=coinbase_exchange_v2`
- `LIVE_MANUAL_APPROVAL_REQUIRED=true`
- `LIVE_SIGNED_APPROVAL_REQUIRED=true` if supported by the active gate path
- `LIVE_MAX_ORDER_NOTIONAL_USD=5` preferred
- `COINBASE_LIVE_ORDER_KILL_SWITCH=false` only during submit window

Immediately restore:

- `COINBASE_LIVE_ORDER_KILL_SWITCH=true`

## Secret storage policy

Do not store secrets in:

- frontend code;
- `REACT_APP_*` variables;
- committed `.env` files;
- README examples with real values;
- logs;
- issue comments;
- screenshots;
- test fixtures;
- CI output.

Use environment-specific secret storage:

- local `.env` ignored by git;
- GitHub Actions secrets for CI if needed;
- platform secrets for deployment;
- separate values per environment.

## Rotation runbook

Rotate credentials immediately if:

- a key was pasted into chat, issue, PR, log, screenshot, terminal history, or frontend build variable;
- an unauthorized request is suspected;
- a developer machine is compromised;
- a dependency compromise affects runtime integrity;
- a pilot behaves unexpectedly and key compromise cannot be ruled out.

Rotation sequence:

1. Disable the old key in the exchange UI.
2. Confirm no withdrawals/transfers occurred.
3. Create a new key with least privilege.
4. Update deployment secret store.
5. Restart the backend.
6. Run live-readonly snapshot.
7. Run live-readonly reconciliation.
8. Confirm pilot readiness remains blocked until operator review is complete.

## Operator checklist before Phase 11

Do not proceed to Phase 11 until:

- readonly key exists and is least privilege;
- execution key exists and has no withdrawal/transfer/margin/futures permissions;
- `.env` is ignored and not committed;
- no secret exists under `REACT_APP_*`;
- `JWT_SECRET` is production-strength outside debug;
- CORS is explicit and production-safe;
- kill switch default is closed;
- max live notional is tiny;
- Phase 10 CI checks pass.

## Phase 10 acceptance checklist

| Requirement | Status |
|---|---:|
| Secret hardening service exists | Complete |
| Redaction helpers exist | Complete |
| Live credential posture evaluation exists | Complete |
| Fail-closed hardening checks exist | Complete |
| Phase 10 hardening tests exist | Complete |
| CI runs Phase 10 hardening tests | Complete |
| Exchange key least-privilege runbook exists | Complete |
| Secret rotation runbook exists | Complete |
| No automatic live order is submitted | Complete |
| No autonomous live trading is introduced | Complete |

## Note

A read-only API endpoint for the hardening report was intentionally left out of this connector patch because the large route-file update was blocked by the connector safety filter. The service and tests are merged first. A later narrow local patch can expose an admin-only diagnostics endpoint if desired.

## Next phase

Phase 11 should run the full dry-run dress rehearsal:

- backend startup;
- frontend build;
- live-readonly snapshot;
- live-readonly reconciliation;
- pilot readiness;
- exact dry-run order;
- pilot report generation;
- operator signoff;
- expansion status clear.
