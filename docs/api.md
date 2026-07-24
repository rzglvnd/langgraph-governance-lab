# API Reference

Base URL: `http://127.0.0.1:8003`

Authentication

- If `GOV_API_KEY` is set, include `X-API-Key` on governance endpoints.
- If rate limiting is enabled, non-exempt routes may return `429`.

Health

- `GET /health` -> liveness check.
- `GET /ready` -> runtime readiness and active controls.

Rate limit headers (when enabled)

- `x-ratelimit-limit`
- `x-ratelimit-remaining`
- `x-ratelimit-reset`
- `retry-after` (on `429`)

Policy endpoints

- `GET /policies/sample`
- `POST /policies/validate`

Request JSON (`POST /policies/validate`):

```json
{
  "policy": {
    "name": "strict-default",
    "max_steps": 30,
    "blocked_tools": ["shell.exec"],
    "approval_required_tools": ["wire_transfer"],
    "allowed_models": ["gpt-4o-mini"],
    "max_total_cost_usd": 0.5,
    "fail_on_missing_model": true
  }
}
```

Evaluation endpoints

- `POST /governance/evaluate`
- `POST /governance/evaluate_batch`

Request JSON (`POST /governance/evaluate`):

```json
{
  "policy": {
    "name": "strict-default",
    "max_steps": 30,
    "blocked_tools": ["shell.exec"],
    "approval_required_tools": ["wire_transfer"],
    "allowed_models": ["gpt-4o-mini"],
    "max_total_cost_usd": 0.5,
    "fail_on_missing_model": true
  },
  "run": {
    "run_id": "run-42",
    "workflow_name": "invoice-review",
    "steps": [
      {
        "node": "planner",
        "model": "gpt-4o-mini",
        "input_tokens": 120,
        "output_tokens": 90,
        "cost_usd": 0.01
      }
    ]
  },
  "include_advice": false
}
```

Response highlights:

- `status`: `pass` or `fail`
- `violation_count`: number of policy violations
- `violations`: list of policy findings
- `stats`: step count, tool call count, token totals, and cost
- `recommendations`: deterministic remediation guidance
