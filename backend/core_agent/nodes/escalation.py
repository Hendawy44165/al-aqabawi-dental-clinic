from dataclasses import dataclass
from typing import Dict, Literal
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage
from langsmith import traceable
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, after_agent, ModelRequest

from ..state import ServiceBotState
from ..config import get_model, load_prompt
from ..tools import add_to_escalation_queue

HANDOFF_MESSAGE = (
    "ألف سلامة على حضرتك يا فندم. عشان نطمنك وتأخد الرعاية المناسبة، "
    "أنا بحول محادثتك دلوقتي للمتخصص وهيرد عليك فوراً. خليك معانا دقيقة واحدة."
)


@dataclass
class EscalationContext:
    sentiment: str
    gathered_parameters: dict
    gathered_information: list


class EscalationResponse(BaseModel):
    model_config = {"extra": "forbid"}
    reason: Literal[
        "customer_anger",
        "react_failure",
        "direct_request",
        "user_stalling",
        "repeated_failure",
    ] = Field(description="Reason for escalation.")
    summary: str = Field(
        description="A concise summary of the customer's request and state."
    )
    urgency: float = Field(description="Urgency score from 0.0 (low) to 1.0 (high).")
    recommended_action: str = Field(
        description="Suggested solution for the human agent."
    )
    ticket_response: str = Field(
        description="The handoff confirmation message to send back to the user."
    )


@dynamic_prompt
def inject_escalation_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("escalation.md")
    return f"""{base}

    <escalation_context>
    User Sentiment: {ctx.sentiment}
    Gathered Parameters: {ctx.gathered_parameters}
    Gathered Information: {ctx.gathered_information}
    </escalation_context>
    """


@traceable(name="escalation_node")
def escalation_node(state: ServiceBotState) -> Dict:
    """
    Generates a structured escalation report from the conversation history,
    triggers the after-agent middleware to queue it, and returns the response message.
    """
    model = get_model()
    escalation_agent = create_agent(
        model=model,
        checkpointer=InMemorySaver(),
        response_format=EscalationResponse,
        middleware=[inject_escalation_context],
        context_schema=EscalationContext,
    )

    context = EscalationContext(
        sentiment=state.get("sentiment", "neutral"),
        gathered_parameters=state.get("gathered_parameters", {}),
        gathered_information=state.get("gathered_information", []),
    )

    response = escalation_agent.invoke(
        {"messages": state["messages"]},
        context=context,
    )

    escalation_output = response["structured_response"]

    # Queue the escalation report directly
    report = {
        "reason": escalation_output.reason,
        "summary": escalation_output.summary,
        "urgency": escalation_output.urgency,
        "recommended_action": escalation_output.recommended_action,
        "metadata": {
            "sentiment": state.get("sentiment"),
            "gathered_parameters": state.get("gathered_parameters"),
            "gathered_information": state.get("gathered_information"),
        },
    }
    add_to_escalation_queue(report)

    return {
        "next_agent": "end",
        "messages": [
            AIMessage(content=escalation_output.ticket_response or HANDOFF_MESSAGE)
        ],
        "escalation_report": report,
    }
