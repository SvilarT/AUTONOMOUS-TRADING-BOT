# API Error Contract

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

The API now emits a stable error envelope and an `X-Request-ID` response header for every request.

## Request ID

Clients may send a request ID:

```http
X-Request-ID: client-generated-id
```

Accepted request IDs must match:

```text
[A-Za-z0-9_.:-]{1,128}
```

Invalid or missing request IDs are replaced with a generated ID. The final request ID is returned in every response:

```http
X-Request-ID: 6f5d0c0c31d84ad59ef3ab7d8dcf25d1
```

## Error envelope

All handled API errors return:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "validation-error-123",
    "details": {}
  }
}
```

## Common codes

| HTTP status | Code |
|---:|---|
| 400 | `BAD_REQUEST` |
| 401 | `UNAUTHORIZED` |
| 403 | `FORBIDDEN` |
| 404 | `NOT_FOUND` |
| 409 | `CONFLICT` |
| 422 | `VALIDATION_ERROR` |
| 429 | `RATE_LIMITED` |
| 500 | `INTERNAL_SERVER_ERROR` |
| 503 | `SERVICE_UNAVAILABLE` |

## Validation errors

Validation failures include Pydantic/FastAPI validation details:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "request_id": "validation-error-123",
    "details": {
      "errors": []
    }
  }
}
```

## Logging

Structured logs include the active `request_id` when emitted inside a request context. This allows correlating:

- API request
- validation/auth errors
- execution errors
- readiness failures
- future frontend reports

## Frontend/client guidance

Clients should:

1. Generate and send `X-Request-ID` for every request.
2. Display `error.message` to users when safe.
3. Include `error.request_id` in support/debug reports.
4. Use `error.code` for programmatic handling.
5. Treat unknown error shapes as fatal/degraded API behavior.
