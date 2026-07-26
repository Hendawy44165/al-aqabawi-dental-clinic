from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from langchain.agents import AgentState


from typing import TypedDict, List


# class AnalyzerMetadata(TypedDict):
#     notes: str
#     directive: Literal[
#         "answer_directly",
#         "ask_clarifying_question",
#         "recommend_solution",
#         "confirm_execution",
#         "escalate",
#     ]


class ServiceBotState(AgentState):
    """Shared state passed through all nodes in the LangGraph."""

    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: Literal[
        "router",
        "simple_qa",
        "executer",
        "escalate",
        "blocker",
        "end",
        "analyzer",
        "need_qa",
    ]
    sentiment: str
    # notes: str | None
    # directive: str | None

    # QA & Profiler variables
    # simple_qa_response: str | None

    # Private executer state
    gathered_parameters: dict
    gathered_information: list
    extracted_parameters: dict
    escalation_report: Optional[dict]
