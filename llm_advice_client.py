import json
from typing import Any, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def build_session(retries: int) -> requests.Session:
    retry = Retry(
        total=max(0, retries),
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _fallback_advice(evaluation: Dict[str, Any]) -> str:
    recommendations = evaluation.get("recommendations") or []
    if recommendations:
        return " ".join(recommendations[:3])
    if evaluation.get("status") == "pass":
        return "Governance checks passed. Continue tracking step count and cost trends."
    return (
        "Review violations and tighten policy controls "
        "for blocked tools, approvals, and model allow-list."
    )


def generate_llm_advice(
    llm_url: str,
    evaluation: Dict[str, Any],
    timeout_seconds: int,
    retries: int,
) -> Optional[str]:
    if not llm_url:
        return None

    session = build_session(retries=retries)
    summary_payload = {
        "status": evaluation.get("status"),
        "violation_count": evaluation.get("violation_count"),
        "violations": evaluation.get("violations", [])[:6],
        "stats": evaluation.get("stats", {}),
    }
    prompt = (
        "You are reviewing a LangGraph governance report. "
        "Provide up to 3 concise remediation steps "
        "for production operations. Report JSON: "
        + json.dumps(summary_payload, ensure_ascii=True)
    )

    response = session.post(
        f"{llm_url.rstrip('/')}/chat",
        json={"message": prompt, "k": 1, "model": "echo"},
        timeout=timeout_seconds,
    )
    if response.status_code != 200:
        return None

    body = response.json()
    return body.get("response")


def build_advice(
    llm_url: str,
    evaluation: Dict[str, Any],
    timeout_seconds: int,
    retries: int,
) -> Dict[str, str]:
    llm_advice = generate_llm_advice(
        llm_url=llm_url,
        evaluation=evaluation,
        timeout_seconds=timeout_seconds,
        retries=retries,
    )
    if llm_advice:
        return {"source": "llm", "text": llm_advice}

    return {"source": "rule-based", "text": _fallback_advice(evaluation)}
