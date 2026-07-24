from governance import evaluate_policy, validate_policy


def test_validate_policy_warns_when_controls_missing() -> None:
    policy = {
        "name": "open-policy",
        "max_steps": 30,
        "blocked_tools": [],
        "approval_required_tools": [],
        "allowed_models": [],
        "max_total_cost_usd": None,
        "fail_on_missing_model": False,
    }
    result = validate_policy(policy, max_steps_cap=200)
    assert result["valid"] is True
    assert any(item["code"] == "weak_policy" for item in result["warnings"])


def test_evaluate_policy_blocked_tool_violation() -> None:
    policy = {
        "max_steps": 10,
        "blocked_tools": ["sql.exec"],
        "approval_required_tools": [],
        "allowed_models": [],
        "max_total_cost_usd": None,
        "fail_on_missing_model": False,
    }
    run = {
        "steps": [
            {"node": "planner", "model": "gpt-4o-mini"},
            {"node": "executor", "tool": "sql.exec", "model": "gpt-4o-mini"},
        ]
    }

    result = evaluate_policy(policy=policy, run=run)
    assert result["status"] == "fail"
    assert any(item["code"] == "blocked_tool" for item in result["violations"])


def test_evaluate_policy_missing_approval_violation() -> None:
    policy = {
        "max_steps": 10,
        "blocked_tools": [],
        "approval_required_tools": ["wire_transfer"],
        "allowed_models": [],
        "max_total_cost_usd": None,
        "fail_on_missing_model": False,
    }
    run = {
        "steps": [
            {
                "node": "payment",
                "tool": "wire_transfer",
                "model": "gpt-4o-mini",
                "requires_human_approval": True,
            }
        ]
    }

    result = evaluate_policy(policy=policy, run=run)
    assert result["status"] == "fail"
    assert any(item["code"] == "missing_human_approval" for item in result["violations"])


def test_evaluate_policy_pass_case() -> None:
    policy = {
        "max_steps": 10,
        "blocked_tools": ["shell.exec"],
        "approval_required_tools": ["wire_transfer"],
        "allowed_models": ["gpt-4o-mini"],
        "max_total_cost_usd": 0.5,
        "fail_on_missing_model": True,
    }
    run = {
        "total_cost_usd": 0.02,
        "steps": [
            {
                "node": "planner",
                "model": "gpt-4o-mini",
                "input_tokens": 60,
                "output_tokens": 40,
                "cost_usd": 0.01,
            },
            {
                "node": "validator",
                "tool": "vector.search",
                "model": "gpt-4o-mini",
                "input_tokens": 55,
                "output_tokens": 35,
                "cost_usd": 0.01,
            },
        ],
    }

    result = evaluate_policy(policy=policy, run=run)
    assert result["status"] == "pass"
    assert result["violation_count"] == 0


def test_evaluate_policy_cost_violation() -> None:
    policy = {
        "max_steps": 10,
        "blocked_tools": [],
        "approval_required_tools": [],
        "allowed_models": [],
        "max_total_cost_usd": 0.02,
        "fail_on_missing_model": False,
    }
    run = {
        "steps": [
            {"node": "planner", "cost_usd": 0.02},
            {"node": "executor", "cost_usd": 0.03},
        ]
    }

    result = evaluate_policy(policy=policy, run=run)
    assert result["status"] == "fail"
    assert any(item["code"] == "max_total_cost_exceeded" for item in result["violations"])
