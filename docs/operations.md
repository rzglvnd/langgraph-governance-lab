# Operations Runbook

Run command:

```bash
uvicorn server:app --host 0.0.0.0 --port 8003
```

Health checks

- `GET /health` should return `status=ok`.
- `GET /ready` should return `status=ok` and runtime control settings.

Rate limiting

- Enable with `GOV_RATE_LIMIT_ENABLED=true`.
- Tune with `GOV_RATE_LIMIT_REQUESTS_PER_MINUTE` and `GOV_RATE_LIMIT_WINDOW_SECONDS`.
- Keep `/health` and `/ready` exempt for probes.

On-call checklist

- Elevated `5xx`:
  - Check env configuration and API key settings.
  - Verify request payload shape and policy validation errors.
  - Disable optional LLM advice by clearing `GOV_LLM_URL`.
- `429` spike:
  - Verify caller burst behavior.
  - Increase limits for trusted callers if needed.
  - Confirm probes and internal paths are exempt.
- Unexpected false positives:
  - Inspect policy normalization warnings from `/policies/validate`.
  - Reduce overly strict controls and retest with known-good runs.
