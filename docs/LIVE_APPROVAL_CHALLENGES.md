# Live Approval Challenges

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Signed approval challenges are the authorization bridge between a dry-run preview and a non-dry-run live order.

## Why this exists

A broad static approval token is not precise enough for real-money actions. Live execution must be approved for a specific order intent.

A challenge binds:

- user id
- side
- symbol
- notional/base amount
- reference price for sells
- `dry_run=false`
- nonce
- expiration
- payload hash

## Create a challenge

```http
POST /api/live-approvals/challenge
Authorization: Bearer <token with trading:live-execute>
Content-Type: application/json

{
  "side": "BUY",
  "symbol": "BTC-USD",
  "notional_usd": 5,
  "expires_in_seconds": 300
}
```

Response:

```json
{
  "challenge_id": "...",
  "approval_token": "challenge.signature",
  "intent": {
    "user_id": "...",
    "side": "BUY",
    "symbol": "BTC-USD",
    "dry_run": false,
    "notional_usd": 5
  },
  "expires_at": "...",
  "status": "pending"
}
```

## Submit the approved live order

```http
POST /api/live-trading/market-buy
Authorization: Bearer <token with trading:live-execute>
Content-Type: application/json

{
  "symbol": "BTC-USD",
  "notional_usd": 5,
  "dry_run": false,
  "approval_token": "challenge.signature"
}
```

## Enforcement

`ScopeEnforcementMiddlewareV2` verifies the signed approval challenge before non-dry-run live requests reach the live trading route. The live trading gate also requires a token in signed-approval mode.

## Replay protection

A challenge transitions from `pending` to `used` during verification. Reusing the same token is rejected.

## Expiration

Challenge expiration is capped between 30 and 900 seconds. Expired challenges are rejected and marked expired.

## Required scope

Creating and using a live approval challenge requires:

```text
trading:live-execute
```

Default users do not have this scope.
