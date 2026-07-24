#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict

from governance import evaluate_policy


DEFAULT_POLICY: Dict[str, Any] = {
    "name": "default-policy",
    "max_steps": 50,
    "blocked_tools": ["shell.exec"],
    "approval_required_tools": ["wire_transfer"],
    "allowed_models": [],
    "max_total_cost_usd": None,
    "fail_on_missing_model": False,
}


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    data = json.loads(path.read_text(encoding="utf8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="LangGraph Governance Lab CLI")
    parser.add_argument("run_file", type=Path, help="Path to agent run JSON payload")
    parser.add_argument(
        "--policy",
        type=Path,
        default=None,
        help="Optional path to governance policy JSON payload",
    )
    args = parser.parse_args()

    run_payload = _read_json(args.run_file)
    policy_payload = DEFAULT_POLICY if args.policy is None else _read_json(args.policy)

    evaluation = evaluate_policy(policy=policy_payload, run=run_payload)
    print(json.dumps(evaluation, indent=2))


if __name__ == "__main__":
    main()
