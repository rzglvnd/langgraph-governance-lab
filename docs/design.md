# Design

This service is designed as a governance control plane for LangGraph and agentic workflows.

Architecture

- `server.py`:
  - Request validation and endpoint orchestration.
  - Policy validation and run evaluation entrypoints.
  - Readiness/liveness endpoints.
  - In-memory request rate limiting.
- `governance.py`:
  - Deterministic policy validation rules.
  - Deterministic run evaluation engine.
  - Rule-based recommendations.
- `llm_advice_client.py`:
  - Optional remediation advice from an upstream LLM endpoint.
  - Retry-capable HTTP behavior for transient failures.
- `settings.py`:
  - Environment-driven runtime configuration.

Design principles

- Keep policy evaluation deterministic and auditable.
- Make LLM remediation advice optional, never required for enforcement.
- Enforce bounded inputs (step limits and batch sizes).
- Provide operational reliability with health checks and request IDs.
- Keep controls explicit: blocked tools, approvals, model allow-list, and cost caps.
