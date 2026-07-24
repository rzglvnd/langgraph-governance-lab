# Contributing

Follow the global constitution and document ADRs for architecture-impacting changes.

## Development workflow

1. Create a feature branch from `main`.
2. Keep governance logic deterministic and testable.
3. Update docs when API behavior, policy semantics, or runtime settings change.

## Quality gates

- `pytest -q`
- `flake8 .`

All checks must pass before merge.

## Documentation standards

- Include request/response examples for API changes.
- Document operational impacts in `docs/operations.md`.
- Document deployment impacts in `docs/deployment.md`.
