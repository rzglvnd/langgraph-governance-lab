# Deployment Guide

## Container

Build and run:

```bash
docker build -t langgraph-governance-lab .
docker run --rm -p 8003:8003 langgraph-governance-lab
```

## Recommended production environment variables

- `GOV_API_KEY`
- `GOV_RATE_LIMIT_ENABLED=true`
- `GOV_RATE_LIMIT_REQUESTS_PER_MINUTE`
- `GOV_LLM_URL` (optional)
- `GOV_LLM_TIMEOUT_SECONDS`
- `GOV_LLM_RETRIES`
- `GOV_API_LOG_LEVEL=INFO`

## Release checklist

1. PR merged with passing lint/tests.
2. Tag release from `main`.
3. Build and push container image.
4. Deploy with health probes wired to `/health` and `/ready`.
