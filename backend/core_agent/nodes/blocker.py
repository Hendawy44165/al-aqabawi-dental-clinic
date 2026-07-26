from typing import Dict
from langchain_core.messages import AIMessage
from langsmith import traceable
from ..state import AgentState, ServiceBotState

BLOCK_RESPONSE = (
    "Thank you for reaching out. I am Al-Aqabawi Dental Clinic's dedicated assistant "
    "and can only assist with questions about our dental services, clinic hours, and appointments. "
    "Is there anything dental-related I can help you with today?"
)


@traceable
def blocker_node(state: ServiceBotState) -> Dict:
    """
    Returns a polite refusal for unrelated or harmful content.
    Deterministic — no LLM call.
    """
    return {
        "next_agent": "end",
        "messages": [AIMessage(content=BLOCK_RESPONSE)],
    }
