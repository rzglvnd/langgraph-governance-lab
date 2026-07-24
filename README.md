# LangGraph Governance Lab

Mission
> Build production-ready governance controls for LangGraph and multi-agent workflows.

## What this service provides

- Governance policy validation endpoint.
- Agent run evaluation endpoint with deterministic policy checks.
- Batch run evaluation endpoint for experiment suites.
- Optional LLM-generated remediation advice.
- Optional API key protection and configurable rate limiting.

## Quick start

Run locally:

```bash
cd langgraph-governance-lab
python -m pip install -r requirements.txt
uvicorn server:app --reload --port 8003
```

Evaluate a sample run:

```bash
curl -s -X POST "http://127.0.0.1:8003/governance/evaluate" \
  -H "Content-Type: application/json" \
  -d @examples/sample_run.json
```

Validate a policy:

```bash
curl -s -X POST "http://127.0.0.1:8003/policies/validate" \
  -H "Content-Type: application/json" \
  -d '{"policy":{"name":"strict","max_steps":30,"blocked_tools":["shell.exec"],"approval_required_tools":["wire_transfer"],"allowed_models":["gpt-4o-mini"],"max_total_cost_usd":0.5}}'
```

## Configuration

Environment variables:

You can start from `.env.example` and override values per environment.

- `GOV_API_HOST` (default: `0.0.0.0`)
- `GOV_API_PORT` (default: `8003`)
- `GOV_API_LOG_LEVEL` (default: `INFO`)
- `GOV_API_KEY` (optional; if set, required via `X-API-Key`)
- `GOV_REQUEST_LOGGING` (default: `true`)
- `GOV_RATE_LIMIT_ENABLED` (default: `false`)
- `GOV_RATE_LIMIT_REQUESTS_PER_MINUTE` (default: `120`)
- `GOV_RATE_LIMIT_WINDOW_SECONDS` (default: `60`)
- `GOV_RATE_LIMIT_EXEMPT_PATHS` (default: `/health,/ready`)
- `GOV_LLM_URL` (optional; enables LLM remediation advice)
- `GOV_LLM_TIMEOUT_SECONDS` (default: `10`)
- `GOV_LLM_RETRIES` (default: `2`)
- `GOV_MAX_STEPS_CAP` (default: `2000`)

## Docs

- Design: `docs/design.md`
- API: `docs/api.md`
- Operations: `docs/operations.md`
- Deployment: `docs/deployment.md`
- Security: `docs/security.md`
- Evaluation: `docs/evaluation.md`

## Testing and quality

```bash
pytest -q
flake8 .
```

CI runs on push/PR and executes lint + tests on Python 3.10 and 3.11.
