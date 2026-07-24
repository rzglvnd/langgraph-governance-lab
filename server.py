import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from governance import evaluate_policy, validate_policy
from llm_advice_client import build_advice
from rate_limit import InMemoryRateLimiter
from settings import load_settings

settings = load_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("langgraph_governance_lab")

app = FastAPI(title="LangGraph Governance Lab")
app.state.rate_limiter = InMemoryRateLimiter(
    limit=settings.rate_limit_requests_per_minute,
    window_seconds=settings.rate_limit_window_seconds,
    enabled=settings.rate_limit_enabled,
)
rate_limit_exempt_paths = set(settings.rate_limit_exempt_paths or [])
rate_limit_exempt_paths.update({"/health", "/ready"})
app.state.rate_limit_exempt_paths = rate_limit_exempt_paths


def _model_dump(model_obj: BaseModel) -> Dict[str, Any]:
    if hasattr(model_obj, "model_dump"):
        return model_obj.model_dump(exclude_none=True)
    return model_obj.dict(exclude_none=True)


class RunStep(BaseModel):
    node: str = Field(min_length=1)
    tool: Optional[str] = None
    model: Optional[str] = None
    input_tokens: Optional[int] = Field(default=None, ge=0)
    output_tokens: Optional[int] = Field(default=None, ge=0)
    cost_usd: Optional[float] = Field(default=None, ge=0)
    requires_human_approval: bool = False
    approved_by: Optional[str] = None


class AgentRun(BaseModel):
    run_id: Optional[str] = None
    workflow_name: Optional[str] = None
    steps: List[RunStep] = Field(min_length=1, max_length=2000)
    total_cost_usd: Optional[float] = Field(default=None, ge=0)


class GovernancePolicy(BaseModel):
    name: str = "default-policy"
    max_steps: int = Field(default=50, ge=1)
    blocked_tools: List[str] = Field(default_factory=list)
    approval_required_tools: List[str] = Field(default_factory=list)
    allowed_models: List[str] = Field(default_factory=list)
    max_total_cost_usd: Optional[float] = Field(default=None, ge=0)
    fail_on_missing_model: bool = False


class PolicyValidationRequest(BaseModel):
    policy: GovernancePolicy


class EvaluateRequest(BaseModel):
    policy: GovernancePolicy
    run: AgentRun
    include_advice: bool = False


class BatchEvaluateRequest(BaseModel):
    policy: GovernancePolicy
    runs: List[AgentRun] = Field(min_length=1, max_length=100)
    include_advice: bool = False


def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _validate_steps_cap(run_payload: Dict[str, Any]) -> None:
    step_count = len(run_payload.get("steps") or [])
    if step_count > settings.max_steps_cap:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Run has {step_count} steps, exceeding GOV_MAX_STEPS_CAP={settings.max_steps_cap}."
            ),
        )


def _evaluate_with_optional_advice(
    policy_payload: Dict[str, Any],
    run_payload: Dict[str, Any],
    include_advice: bool,
) -> Dict[str, Any]:
    evaluation = evaluate_policy(policy=policy_payload, run=run_payload)
    if include_advice:
        evaluation["advice"] = build_advice(
            llm_url=settings.llm_url,
            evaluation=evaluation,
            timeout_seconds=settings.llm_timeout_seconds,
            retries=settings.llm_retries,
        )
    return evaluation


@app.middleware("http")
async def attach_request_id_and_log(request: Request, call_next):
    request_id = request.headers.get("x-request-id", uuid4().hex)
    start = time.perf_counter()

    rate_decision = None
    response = None

    limiter = app.state.rate_limiter
    exempt_paths = app.state.rate_limit_exempt_paths
    should_rate_limit = (
        limiter.enabled
        and request.method != "OPTIONS"
        and request.url.path not in exempt_paths
    )

    if should_rate_limit:
        client_host = request.client.host if request.client else "unknown"
        rate_decision = limiter.check(client_host)
        if not rate_decision.allowed:
            response = JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
            response.headers["retry-after"] = str(rate_decision.reset_after_seconds)

    try:
        if response is None:
            response = await call_next(request)
    except Exception:
        logger.exception(
            "request_id=%s path=%s method=%s unhandled_error",
            request_id,
            request.url.path,
            request.method,
        )
        raise

    elapsed_ms = (time.perf_counter() - start) * 1000

    if should_rate_limit and rate_decision is not None:
        response.headers["x-ratelimit-limit"] = str(limiter.limit)
        response.headers["x-ratelimit-remaining"] = str(rate_decision.remaining)
        response.headers["x-ratelimit-reset"] = str(rate_decision.reset_after_seconds)

    response.headers["x-request-id"] = request_id
    if settings.request_logging:
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
    return response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {
        "status": "ok",
        "runtime": {
            "max_steps_cap": settings.max_steps_cap,
            "rate_limit": {
                "enabled": app.state.rate_limiter.enabled,
                "requests_per_minute": app.state.rate_limiter.limit,
                "window_seconds": app.state.rate_limiter.window_seconds,
                "exempt_paths": sorted(app.state.rate_limit_exempt_paths),
            },
            "llm_advice": {
                "enabled": bool(settings.llm_url),
                "url": settings.llm_url or None,
                "timeout_seconds": settings.llm_timeout_seconds,
            },
        },
    }


@app.get("/policies/sample")
async def policies_sample():
    return {
        "policy": {
            "name": "strict-default",
            "max_steps": 30,
            "blocked_tools": ["shell.exec"],
            "approval_required_tools": ["wire_transfer"],
            "allowed_models": ["gpt-4o-mini"],
            "max_total_cost_usd": 0.5,
            "fail_on_missing_model": True,
        }
    }


@app.post("/policies/validate")
async def policies_validate(
    payload: PolicyValidationRequest,
    _: None = Depends(require_api_key),
):
    policy_payload = _model_dump(payload.policy)
    result = validate_policy(policy_payload, max_steps_cap=settings.max_steps_cap)
    return result


@app.post("/governance/evaluate")
async def governance_evaluate(payload: EvaluateRequest, _: None = Depends(require_api_key)):
    policy_payload = _model_dump(payload.policy)
    run_payload = _model_dump(payload.run)
    _validate_steps_cap(run_payload)

    validation = validate_policy(policy_payload, max_steps_cap=settings.max_steps_cap)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation)

    evaluation = _evaluate_with_optional_advice(
        policy_payload=policy_payload,
        run_payload=run_payload,
        include_advice=payload.include_advice,
    )
    return evaluation


@app.post("/governance/evaluate_batch")
async def governance_evaluate_batch(
    payload: BatchEvaluateRequest,
    _: None = Depends(require_api_key),
):
    policy_payload = _model_dump(payload.policy)
    validation = validate_policy(policy_payload, max_steps_cap=settings.max_steps_cap)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation)

    results = []
    passed = 0
    failed = 0

    for index, run in enumerate(payload.runs, start=1):
        run_payload = _model_dump(run)
        _validate_steps_cap(run_payload)
        evaluation = _evaluate_with_optional_advice(
            policy_payload=policy_payload,
            run_payload=run_payload,
            include_advice=payload.include_advice,
        )
        if evaluation["status"] == "pass":
            passed += 1
        else:
            failed += 1
        results.append(
            {
                "run_id": run_payload.get("run_id") or f"run-{index}",
                **evaluation,
            }
        )

    return {
        "count": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
