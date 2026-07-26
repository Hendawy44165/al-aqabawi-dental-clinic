from typing import Literal

from langsmith import traceable
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from ..state import ServiceBotState
from ..config import get_model, load_prompt


class RouterResponse(BaseModel):
    next_agent: Literal[
        "simple_qa",
        "escalate",
        "blocker",
    ]
    sentiment: str


@traceable
def router_node(state: ServiceBotState) -> dict:
    import logging
    logger = logging.getLogger("router_node")

    model = get_model()
    system_prompt = load_prompt("router.md")

    try:
        from ..guardrails import NuitRateLimitingMiddleware, NuitOutputSanitizerMiddleware
        from langchain.agents.middleware import ModelRetryMiddleware

        router_agent = create_agent(
            model=model,
            system_prompt=system_prompt,
            checkpointer=InMemorySaver(),
            response_format=RouterResponse,
            middleware=[
                NuitRateLimitingMiddleware(),
                ModelRetryMiddleware(max_retries=3, on_failure="error"),
                NuitOutputSanitizerMiddleware(),
            ],
        )

        response = router_agent.invoke({"messages": state["messages"]})
        router_output = response["structured_response"]

        return {
            "next_agent": router_output.next_agent,
            "sentiment": router_output.sentiment,
        }
    except Exception as e:
        if isinstance(e, ValueError) and "rate limit" in str(e).lower():
            raise

        logger.error(
            "Router node failure: unable to classify user input or parse response",
            error=str(e),
            messages=[getattr(m, "content", str(m)) for m in state["messages"][-3:]],
        )
        try:
            from database import db
            db.add_system_log(
                "router_node",
                "ERROR",
                f"Router node execution failed: {str(e)}"
            )
        except Exception:
            pass

        return {
            "next_agent": "escalate",
            "sentiment": "neutral",
        }
