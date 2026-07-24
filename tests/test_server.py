from fastapi.testclient import TestClient

from langgraph_governance_lab.server import app
from rate_limit import InMemoryRateLimiter


client = TestClient(app)


def _strict_policy():
    return {
        "name": "strict-default",
        "max_steps": 30,
        "blocked_tools": ["shell.exec"],
        "approval_required_tools": ["wire_transfer"],
        "allowed_models": ["gpt-4o-mini"],
        "max_total_cost_usd": 0.5,
        "fail_on_missing_model": True,
    }


def test_health_and_ready() -> None:
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    ready_resp = client.get("/ready")
    assert ready_resp.status_code == 200
    data = ready_resp.json()
    assert data["status"] == "ok"
    assert "runtime" in data


def test_policies_validate() -> None:
    resp = client.post("/policies/validate", json={"policy": _strict_policy()})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["errors"] == []


def test_governance_evaluate_fail() -> None:
    payload = {
        "policy": _strict_policy(),
        "run": {
            "run_id": "run-1",
            "workflow_name": "demo",
            "steps": [
                {
                    "node": "executor",
                    "tool": "shell.exec",
                    "model": "gpt-4o-mini",
                    "cost_usd": 0.01,
                }
            ],
        },
        "include_advice": False,
    }
    resp = client.post("/governance/evaluate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "fail"
    assert data["violation_count"] >= 1


def test_governance_evaluate_batch_counts() -> None:
    payload = {
        "policy": _strict_policy(),
        "runs": [
            {
                "run_id": "run-pass",
                "steps": [
                    {
                        "node": "planner",
                        "model": "gpt-4o-mini",
                        "cost_usd": 0.01,
                    }
                ],
            },
            {
                "run_id": "run-fail",
                "steps": [
                    {
                        "node": "executor",
                        "tool": "shell.exec",
                        "model": "gpt-4o-mini",
                        "cost_usd": 0.01,
                    }
                ],
            },
        ],
        "include_advice": False,
    }
    resp = client.post("/governance/evaluate_batch", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert data["passed"] == 1
    assert data["failed"] == 1


def test_rate_limit_enforced_on_evaluate_route() -> None:
    original_limiter = app.state.rate_limiter
    original_exempt = app.state.rate_limit_exempt_paths

    app.state.rate_limiter = InMemoryRateLimiter(limit=1, window_seconds=60, enabled=True)
    app.state.rate_limit_exempt_paths = {"/health", "/ready"}

    payload = {
        "policy": _strict_policy(),
        "run": {
            "run_id": "run-rl",
            "steps": [{"node": "planner", "model": "gpt-4o-mini", "cost_usd": 0.01}],
        },
        "include_advice": False,
    }

    try:
        first = client.post("/governance/evaluate", json=payload)
        assert first.status_code == 200

        second = client.post("/governance/evaluate", json=payload)
        assert second.status_code == 429
        assert second.json()["detail"] == "Rate limit exceeded"

        health = client.get("/health")
        assert health.status_code == 200
    finally:
        app.state.rate_limiter = original_limiter
        app.state.rate_limit_exempt_paths = original_exempt
