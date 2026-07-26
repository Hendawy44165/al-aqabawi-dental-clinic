import re
import time
from typing import Any, Callable, Dict, List
import logging

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse

logger = logging.getLogger("guardrails")

# In-memory store for rate limiting: thread_id -> list of timestamps
_RATE_LIMIT_STORE: Dict[str, List[float]] = {}
RATE_LIMIT_MAX_REQUESTS = 20
RATE_LIMIT_WINDOW_SECONDS = 30.0

# Detection patterns for prompt leakage and placeholders
SYSTEM_TAGS_PATTERN = re.compile(
    r"(<system_prompt>|<role>|<routing_directives>|<knowledge_base>|<guidelines>|<brand_voice>)",
    re.IGNORECASE,
)
JSON_METRICS_PATTERN = re.compile(
    r"(session_summary_report|ticket_classification_matrix|captured_intake_form_state)",
    re.IGNORECASE,
)
PLACEHOLDER_PATTERN = re.compile(
    r"(\[Insert\s+[^\]]+\]|\[[^\]]*(Placeholder|insert|TBD)[^\]]*\])",
    re.IGNORECASE,
)


def is_rate_limited(thread_id: str) -> bool:
    """
    Check if a session thread exceeds the rate limit of 20 requests per 30 seconds.
    Uses a sliding window algorithm.
    """
    now = time.time()
    if thread_id not in _RATE_LIMIT_STORE:
        _RATE_LIMIT_STORE[thread_id] = [now]
        return False

    # Filter out timestamps older than the sliding window
    history = [
        ts
        for ts in _RATE_LIMIT_STORE[thread_id]
        if now - ts <= RATE_LIMIT_WINDOW_SECONDS
    ]
    _RATE_LIMIT_STORE[thread_id] = history

    if len(history) >= RATE_LIMIT_MAX_REQUESTS:
        return True

    _RATE_LIMIT_STORE[thread_id].append(now)
    return False


def sanitize_output(text: str) -> str:
    """
    Scan the generated response for severe leakages of internal system details.

    If system tags or JSON metric payloads are found, raises a ValueError
    to trigger immediate escalation.

    Also sanitizes/removes common placeholder brackets.
    """
    if not text:
        return text

    # 1. Check for prompt leakage or raw JSON metadata block leak
    if SYSTEM_TAGS_PATTERN.search(text) or JSON_METRICS_PATTERN.search(text):
        raise ValueError(
            "Severe safety warning: Generated response contained internal system tokens or JSON metrics."
        )

    # 2. Check for unresolved placeholders or TBD patterns
    if PLACEHOLDER_PATTERN.search(text):
        raise ValueError(
            "Safety check failure: Generated response contained unresolved placeholder brackets."
        )

    return text


class NuitRateLimitingMiddleware(AgentMiddleware):
    """
    LangChain agent middleware that checks rate limits before agent starts execution.
    Raises a ValueError if the rate limit is exceeded.
    """

    def before_agent(self, state: Any, runtime: Any) -> Any:
        from langgraph.config import get_config

        try:
            config = get_config()
            thread_id = config.get("configurable", {}).get("thread_id", "default")
        except RuntimeError:
            thread_id = "default"

        if is_rate_limited(thread_id):
            logger.warning(
                "Rate limit exceeded for thread in middleware", thread_id=thread_id
            )
            raise ValueError("Rate limit exceeded")


class NuitOutputSanitizerMiddleware(AgentMiddleware):
    """
    LangChain agent middleware that scans model responses for prompt leaks,
    placeholders, or JSON leakages. Raises ValueError if validation fails.
    """

    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelResponse:
        response = handler(request)
        if response.result:
            ai_msg = response.result[0]
            # Will raise ValueError if system leak or placeholder is detected
            sanitize_output(ai_msg.content)
        return response
