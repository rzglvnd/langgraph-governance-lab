from typing import Any, Dict, List, Set


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_values(values: List[str]) -> List[str]:
    seen: Set[str] = set()
    normalized: List[str] = []
    for value in values or []:
        text = str(value).strip().lower()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _derive_total_cost(run: Dict[str, Any], steps: List[Dict[str, Any]]) -> float:
    explicit_total = run.get("total_cost_usd")
    if explicit_total is not None:
        return _as_float(explicit_total, default=0.0)
    return sum(_as_float(step.get("cost_usd"), default=0.0) for step in steps)


def _recommendations(violation_codes: Set[str]) -> List[str]:
    if not violation_codes:
        return [
            (
                "Run passed all active governance checks. "
                "Keep monitoring policy drift and model behavior."
            ),
        ]

    mapping = {
        "max_steps_exceeded": (
            "Add explicit graph termination conditions and reduce recursion depth."
        ),
        "blocked_tool": (
            "Replace blocked tools with approved alternatives or update policy exceptions."
        ),
        "missing_human_approval": (
            "Route approval-required actions through a human approval queue."
        ),
        "disallowed_model": "Restrict runtime to the policy-approved model allow-list.",
        "missing_model_metadata": "Populate model metadata for each step before execution.",
        "max_total_cost_exceeded": (
            "Set tighter token or step budgets and enforce pre-execution cost checks."
        ),
    }

    ordered_codes = sorted(violation_codes)
    return [mapping[code] for code in ordered_codes if code in mapping]


def validate_policy(policy: Dict[str, Any], max_steps_cap: int) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    warnings: List[Dict[str, str]] = []

    max_steps = _as_int(policy.get("max_steps"), default=0)
    if max_steps < 1:
        errors.append(
            {
                "code": "invalid_max_steps",
                "message": "max_steps must be an integer greater than or equal to 1.",
            }
        )
    if max_steps > max_steps_cap:
        errors.append(
            {
                "code": "max_steps_cap_exceeded",
                "message": f"max_steps exceeds GOV_MAX_STEPS_CAP ({max_steps_cap}).",
            }
        )

    blocked_tools_raw = policy.get("blocked_tools") or []
    approval_tools_raw = policy.get("approval_required_tools") or []
    allowed_models_raw = policy.get("allowed_models") or []
    max_total_cost = policy.get("max_total_cost_usd")

    blocked_tools = _normalize_values(blocked_tools_raw)
    approval_tools = _normalize_values(approval_tools_raw)
    allowed_models = _normalize_values(allowed_models_raw)

    if len(blocked_tools_raw) != len(blocked_tools):
        warnings.append(
            {
                "code": "duplicate_or_empty_blocked_tools",
                "message": (
                    "blocked_tools contained duplicates or empty entries "
                    "that were normalized."
                ),
            }
        )
    if len(approval_tools_raw) != len(approval_tools):
        warnings.append(
            {
                "code": "duplicate_or_empty_approval_tools",
                "message": (
                    "approval_required_tools contained duplicates or empty entries "
                    "that were normalized."
                ),
            }
        )
    if len(allowed_models_raw) != len(allowed_models):
        warnings.append(
            {
                "code": "duplicate_or_empty_allowed_models",
                "message": (
                    "allowed_models contained duplicates or empty entries "
                    "that were normalized."
                ),
            }
        )

    if max_total_cost is not None and _as_float(max_total_cost, default=-1.0) < 0:
        errors.append(
            {
                "code": "invalid_max_total_cost",
                "message": "max_total_cost_usd must be greater than or equal to 0 when provided.",
            }
        )

    if (
        not blocked_tools
        and not approval_tools
        and not allowed_models
        and max_total_cost is None
    ):
        warnings.append(
            {
                "code": "weak_policy",
                "message": (
                    "Policy has no active controls. "
                    "Add at least one control before production use."
                ),
            }
        )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def evaluate_policy(policy: Dict[str, Any], run: Dict[str, Any]) -> Dict[str, Any]:
    steps = run.get("steps") or []

    blocked_tools = set(_normalize_values(policy.get("blocked_tools") or []))
    approval_required_tools = set(
        _normalize_values(policy.get("approval_required_tools") or [])
    )
    allowed_models = set(_normalize_values(policy.get("allowed_models") or []))
    fail_on_missing_model = bool(policy.get("fail_on_missing_model"))
    max_steps = _as_int(policy.get("max_steps"), default=0)
    max_total_cost = policy.get("max_total_cost_usd")

    violations: List[Dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0

    for step_index, step in enumerate(steps, start=1):
        tool = str(step.get("tool") or "").strip().lower()
        model = str(step.get("model") or "").strip().lower()
        approved_by = str(step.get("approved_by") or "").strip()
        node = step.get("node") or f"step-{step_index}"

        total_input_tokens += _as_int(step.get("input_tokens"), default=0)
        total_output_tokens += _as_int(step.get("output_tokens"), default=0)

        if tool and tool in blocked_tools:
            violations.append(
                {
                    "code": "blocked_tool",
                    "severity": "high",
                    "message": f"Blocked tool '{tool}' was used.",
                    "step_index": step_index,
                    "step_node": node,
                }
            )

        approval_needed = bool(step.get("requires_human_approval")) or (
            bool(tool) and tool in approval_required_tools
        )
        if approval_needed and not approved_by:
            violations.append(
                {
                    "code": "missing_human_approval",
                    "severity": "high",
                    "message": (
                        "An approval-required action executed "
                        "without human approval."
                    ),
                    "step_index": step_index,
                    "step_node": node,
                }
            )

        if allowed_models:
            if model and model not in allowed_models:
                violations.append(
                    {
                        "code": "disallowed_model",
                        "severity": "high",
                        "message": f"Model '{model}' is not in the allowed model list.",
                        "step_index": step_index,
                        "step_node": node,
                    }
                )
            if not model and fail_on_missing_model:
                violations.append(
                    {
                        "code": "missing_model_metadata",
                        "severity": "medium",
                        "message": (
                            "Model metadata is missing for a step "
                            "while policy requires it."
                        ),
                        "step_index": step_index,
                        "step_node": node,
                    }
                )

    if max_steps > 0 and len(steps) > max_steps:
        violations.append(
            {
                "code": "max_steps_exceeded",
                "severity": "high",
                "message": f"Run has {len(steps)} steps, exceeding policy max_steps={max_steps}.",
            }
        )

    total_cost = _derive_total_cost(run=run, steps=steps)
    if max_total_cost is not None and total_cost > _as_float(max_total_cost):
        violations.append(
            {
                "code": "max_total_cost_exceeded",
                "severity": "high",
                "message": (
                    f"Run cost {total_cost:.6f} USD exceeded policy max_total_cost_usd="
                    f"{_as_float(max_total_cost):.6f}."
                ),
            }
        )

    violation_codes = {v["code"] for v in violations}
    status = "pass" if not violations else "fail"

    return {
        "status": status,
        "violation_count": len(violations),
        "violations": violations,
        "stats": {
            "step_count": len(steps),
            "tool_call_count": sum(1 for step in steps if step.get("tool")),
            "total_input_tokens": total_input_tokens,
            "total_output_tokens": total_output_tokens,
            "total_cost_usd": round(total_cost, 6),
        },
        "recommendations": _recommendations(violation_codes),
    }
