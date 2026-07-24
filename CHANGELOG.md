# Changelog

All notable changes to this repository will be documented in this file.

## [0.1.0] - 2026-07-24

### Added

- FastAPI governance service with policy validation and run evaluation endpoints.
- Deterministic governance rules for blocked tools, required approvals, model allow-list, and cost/step limits.
- Optional LLM-backed remediation advice with retry-aware client.
- Request-id middleware, health/readiness routes, and configurable in-memory rate limiting.
- CI workflow (lint + pytest), Docker runtime, and runbooks for API, operations, deployment, and security.
- Test coverage for governance core logic, API behavior, and throttling behavior.
