# Live-Trading Security Hardening

The live execution path is intentionally fail-closed. Paper trading remains the default runtime mode. A production live-trading process must satisfy every startup invariant and every per-order security check before the Coinbase adapter is reached.

## Security boundary

The browser dashboard uses an HttpOnly `atb_session` cookie and a readable `atb_csrf` double-submit token. Browser JavaScript no longer stores JWT credentials in `localStorage`. Bearer-token API clients remain supported for controlled scripts and tests.

Every non-dry-run live order requires:

1. A user with `trading:live-execute` scope.
2. A short-lived live-execution session created by password reauthentication and TOTP MFA.
3. An `Idempotency-Key` header.
4. Mongo-backed per-user, per-IP, and global rate limits.
5. A nonce-bound, payload-bound, expiring, single-use signed approval challenge.
6. A verified hash-chained live audit log.
7. No active persistent live halt.
8. No unresolved previous live order.
9. Fresh live-readonly reconciliation.
10. The existing live gate, risk decision, and final adapter kill switch.

## Required live-trading startup configuration

`TRADING_MODE=live-trading` refuses to boot unless all of the following conditions are true:

- `DEBUG=False`
- `RUNTIME_ROLE=api`
- `API_EMBED_BOT_MANAGER=False`
- `LIVE_TRADING_ENABLED=True`
- `LIVE_EXECUTION_ADAPTER=coinbase_exchange_v2`
- `LIVE_MFA_REQUIRED=True`
- `LIVE_TOTP_SECRET` or `LIVE_TOTP_SECRET_FILE` configured
- `LIVE_RATE_LIMITING_ENABLED=True`
- `LIVE_IDEMPOTENCY_REQUIRED=True`
- `OPS_ADMIN_ENABLED=True`
- `OPS_ADMIN_EMAILS` configured
- `LIVE_OPERATOR_ATTESTATION_ACCEPTED=True`
- `LIVE_CREDENTIALS_WITHDRAWALS_DISABLED_CONFIRMED=True`
- `LIVE_CREDENTIALS_TRANSFERS_DISABLED_CONFIRMED=True`
- `LIVE_CREDENTIALS_IP_ALLOWLIST_CONFIRMED=True`

Keep `COINBASE_LIVE_ORDER_KILL_SWITCH=True` except during an explicitly supervised execution window.

## Mounted secret files

Sensitive configuration accepts a `_FILE` alternative. This supports Vault Agent templates, Docker secrets, Kubernetes CSI mounts, and cloud secret-manager sidecars without storing plaintext credentials in `.env` files.

Examples:

- `JWT_SECRET_FILE=/run/secrets/jwt_secret`
- `COINBASE_EXCHANGE_API_KEY_FILE=/run/secrets/coinbase_api_key`
- `COINBASE_EXCHANGE_API_SECRET_FILE=/run/secrets/coinbase_api_secret`
- `COINBASE_EXCHANGE_PASSPHRASE_FILE=/run/secrets/coinbase_passphrase`
- `LIVE_TOTP_SECRET_FILE=/run/secrets/live_totp_secret`
- `OPS_ALERT_WEBHOOK_URL_FILE=/run/secrets/ops_alert_webhook`

When both forms are present, the mounted `_FILE` value takes precedence.

## Live-session elevation

Create a short-lived live execution session before requesting an approval challenge:

1. `POST /api/live-auth/elevate` with password and TOTP code.
2. Pass the returned token in `X-Live-Session-Token` when creating a signed approval challenge.
3. Pass the same token when submitting the live order.
4. Revoke it with `POST /api/live-auth/revoke` when the supervised window closes.

Sessions are hashed at rest, bound to the originating IP address, expire automatically, and can be revoked.

## Idempotency and replay protection

Every non-dry-run live order requires an `Idempotency-Key` header. The key is unique per user and retained for seven days by default.

- Exact retries return the stored response.
- Payload changes under an existing key are rejected.
- Concurrent duplicate submissions fail closed.
- Signed approval challenges remain single-use.

## Persistent circuit breaker

Security anomalies are persisted as live-execution events. The circuit breaker automatically creates a persistent live halt for critical integrity failures and configurable anomaly bursts. Restarting the API does not clear the halt.

Critical examples:

- Hash-chain verification failure
- Credential-boundary failure
- Repeated adapter errors
- Broker rejection bursts
- Rate-limit violations
- Approval replay attempts
- Idempotency violations
- MFA elevation failures

Use the ops-admin endpoints to inspect, trigger, or reset halts:

- `GET /api/ops/live-halts`
- `POST /api/ops/live-halts/emergency`
- `POST /api/ops/live-halts/reset`

## Alerts

Alerts are inserted into MongoDB before webhook delivery is attempted. Configure `OPS_ALERT_WEBHOOK_URL` or `OPS_ALERT_WEBHOOK_URL_FILE` to forward operational alerts. A webhook outage is recorded but cannot suppress a safety halt.

## Process separation

The HTTP API and autonomous paper worker are separate processes. Live-trading startup rejects embedded `BotManager` execution. The dedicated worker does not expose HTTP and does not autonomously submit live orders.

## Exchange credential boundary

Use a dedicated Coinbase API key and a deliberately capped funded account. Confirm withdrawals and transfers are disabled and apply an API-key IP allowlist before setting the operator-attestation flags. These exchange-side permissions require operator verification in Coinbase account controls.
