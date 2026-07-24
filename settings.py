from dataclasses import dataclass
import os
from typing import List


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_list(value: str) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    log_level: str
    api_key: str
    request_logging: bool
    rate_limit_enabled: bool
    rate_limit_requests_per_minute: int
    rate_limit_window_seconds: int
    rate_limit_exempt_paths: List[str]
    llm_url: str
    llm_timeout_seconds: int
    llm_retries: int
    max_steps_cap: int


def load_settings() -> Settings:
    return Settings(
        host=os.environ.get("GOV_API_HOST", "0.0.0.0"),
        port=_as_int(os.environ.get("GOV_API_PORT"), 8003),
        log_level=os.environ.get("GOV_API_LOG_LEVEL", "INFO"),
        api_key=os.environ.get("GOV_API_KEY", "").strip(),
        request_logging=_as_bool(os.environ.get("GOV_REQUEST_LOGGING"), True),
        rate_limit_enabled=_as_bool(os.environ.get("GOV_RATE_LIMIT_ENABLED"), False),
        rate_limit_requests_per_minute=max(
            1,
            _as_int(os.environ.get("GOV_RATE_LIMIT_REQUESTS_PER_MINUTE"), 120),
        ),
        rate_limit_window_seconds=max(
            1,
            _as_int(os.environ.get("GOV_RATE_LIMIT_WINDOW_SECONDS"), 60),
        ),
        rate_limit_exempt_paths=_as_list(
            os.environ.get("GOV_RATE_LIMIT_EXEMPT_PATHS", "/health,/ready"),
        ),
        llm_url=os.environ.get("GOV_LLM_URL", "").strip(),
        llm_timeout_seconds=max(1, _as_int(os.environ.get("GOV_LLM_TIMEOUT_SECONDS"), 10)),
        llm_retries=max(0, _as_int(os.environ.get("GOV_LLM_RETRIES"), 2)),
        max_steps_cap=max(1, _as_int(os.environ.get("GOV_MAX_STEPS_CAP"), 2000)),
    )
