import os
from enum import Enum
from dataclasses import dataclass
from typing import Literal, Optional
from langsmith import traceable
from langchain.agents import create_agent
from langchain.tools import tool
from pydantic import BaseModel, Field
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import dynamic_prompt, ModelRequest
from langchain_core.messages import AIMessage

from ..state import ServiceBotState
from ..config import get_model, load_prompt

# Import clinic tools and wrap them
from ..tools.clinic_tools import (
    get_clinic_services_and_prices as _get_clinic_services_and_prices,
    check_available_slots as _check_available_slots,
    book_appointment_request as _book_appointment_request,
    lookup_patient_appointment as _lookup_patient_appointment
)

class DoctorNameEnum(str, Enum):
    DR_MOHAMED = "Dr. Mohamed Al-Aqabawi"
    DR_IBRAHIM = "Dr. Ibrahim Gamal"
    ALL = "ALL"

class TargetDateEnum(str, Enum):
    TODAY = "today"
    TOMORROW = "tomorrow"
    ALL = "ALL"

class CheckAvailableSlotsInput(BaseModel):
    doctor_name: Optional[DoctorNameEnum] = Field(
        default=DoctorNameEnum.ALL,
        description="Filter by doctor: 'Dr. Mohamed Al-Aqabawi' (د. محمد العقباوي), 'Dr. Ibrahim Gamal' (د. إبراهيم جمال), or 'ALL' for any available doctor."
    )
    target_date: Optional[TargetDateEnum] = Field(
        default=TargetDateEnum.ALL,
        description="Filter by date: 'today' (النهاردة), 'tomorrow' (بكرة), or 'ALL' for all upcoming slots."
    )

class BookAppointmentInput(BaseModel):
    patient_name: str = Field(description="Full name of the patient (اسم المريض).")
    patient_phone: str = Field(description="Contact phone number of the patient (رقم التليفون).")
    slot_id: int = Field(description="The numeric integer ID of the selected slot from check_available_slots.")
    notes: str = Field(default="", description="Optional additional treatment notes.")

class LookupAppointmentInput(BaseModel):
    patient_phone: str = Field(description="Patient phone number to look up existing appointments.")

@tool
def get_clinic_services_and_prices() -> list:
    """Returns a list of all services provided by the clinic with their prices."""
    return _get_clinic_services_and_prices()

@tool(args_schema=CheckAvailableSlotsInput)
def check_available_slots(doctor_name: DoctorNameEnum = DoctorNameEnum.ALL, target_date: TargetDateEnum = TargetDateEnum.ALL) -> list:
    """Check open clinic slots filtered by doctor ('Dr. Mohamed Al-Aqabawi' / 'Dr. Ibrahim Gamal' / 'ALL') and target_date ('today' / 'tomorrow' / 'ALL')."""
    doc_val = None if (doctor_name is None or doctor_name == DoctorNameEnum.ALL) else doctor_name.value
    date_val = None if (target_date is None or target_date == TargetDateEnum.ALL) else target_date.value
    return _check_available_slots(doc_val, date_val)

@tool(args_schema=BookAppointmentInput)
def book_appointment_request(patient_name: str, patient_phone: str, slot_id: int, notes: str = "") -> dict:
    """Book an appointment for a patient given a specific numeric slot_id."""
    return _book_appointment_request(patient_name, patient_phone, slot_id, notes)

@tool(args_schema=LookupAppointmentInput)
def lookup_patient_appointment(patient_phone: str) -> list:
    """Looks up appointments for a given patient phone number."""
    return _lookup_patient_appointment(patient_phone)



@dataclass
class QaContext:
    sentiment: str
    kb_context: str = ""


def load_all_documents() -> str:
    """Read and combine all clinic documents."""
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")
    filenames = ["clinic_info.md", "dental_services_faq.md", "tone_and_brand_voice_eg.md", "receptionist_skill_guide.md"]
    combined = []

    for filename in filenames:
        doc_path = os.path.join(docs_dir, filename)
        if os.path.exists(doc_path):
            try:
                with open(doc_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2]
                content = content.strip()
                combined.append(f'<document name="{filename}">\n{content}\n</document>')
            except Exception as e:
                combined.append(f'<document name="{filename}">\nFailed to load: {e}\n</document>')

    return "\n\n".join(combined)


class QaResponse(BaseModel):
    model_config = {"extra": "forbid"}
    user_response: str = Field(description="The response message to send to the customer on WhatsApp.")
    next_agent: Literal["end"] = Field(description="Always set to end.")


@dynamic_prompt
def inject_context(request: ModelRequest) -> str:
    ctx = request.runtime.context
    base = load_prompt("simple_qa.md")

    injected = f"{base}\n\n    <context>\n    Sentiment: {ctx.sentiment}\n    </context>\n    "

    if getattr(ctx, "kb_context", None):
        injected += f"\n    <retrieved_document>\n    {ctx.kb_context}\n    </retrieved_document>\n    "
    return injected


@traceable
def simple_qa_node(state: ServiceBotState) -> dict:
    import logging
    logger = logging.getLogger("simple_qa_node")

    kb_context = load_all_documents()
    model = get_model()

    try:
        from ..guardrails import NuitRateLimitingMiddleware, NuitOutputSanitizerMiddleware
        from langchain.agents.middleware import ModelRetryMiddleware

        qa_agent = create_agent(
            model=model,
            tools=[get_clinic_services_and_prices, check_available_slots, book_appointment_request, lookup_patient_appointment],
            checkpointer=InMemorySaver(),
            middleware=[
                NuitRateLimitingMiddleware(),
                inject_context,
                ModelRetryMiddleware(max_retries=3, on_failure="error"),
                NuitOutputSanitizerMiddleware(),
            ],
            response_format=QaResponse,
            context_schema=QaContext,
        )

        context = QaContext(
            sentiment=state.get("sentiment", "neutral"),
            kb_context=kb_context,
        )

        response = qa_agent.invoke(
            {"messages": state["messages"]},
            context=context,
        )

        qa_output = response["structured_response"]

        return {
            "messages": [AIMessage(content=qa_output.user_response or "")],
            "next_agent": "end",
        }
    except Exception as e:
        if isinstance(e, ValueError) and "rate limit" in str(e).lower():
            raise

        logger.error("Simple QA node failure", error=str(e))
        try:
            from database import db
            db.add_system_log("simple_qa_node", "ERROR", f"QA node failed: {str(e)}")
        except Exception:
            pass

        return {
            "next_agent": "escalate",
            "is_handoff": True,
            "handoff_summary": f"System error in simple_qa node: {str(e)}",
            "messages": [AIMessage(content="Connecting you to a support specialist...")],
        }
