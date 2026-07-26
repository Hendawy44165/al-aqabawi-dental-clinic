import json
from typing import Dict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langsmith import traceable
from dotenv import load_dotenv

from .state import ServiceBotState
from .nodes import (
    router_node,
    simple_qa_node,
    # analyzer_node,
    # need_qa_node,
    escalation_node,
    blocker_node,
)

load_dotenv()

import logging

logger = logging.getLogger("clinic_bot")



class ClinicBot:

    """
    High-level wrapper around the compiled LangGraph.
    Manages model instance, checkpointer, and message dispatch.
    """

    def __init__(self):
        self.memory = MemorySaver()
        self.graph = self.compile_graph(checkpointer=self.memory)

    @traceable(name="send_message")
    def send_message(self, message: str, thread_id: str = "default") -> dict:
        """
        Send a user message through the graph pipeline.

        Args:
            message: The user's message text.
            thread_id: UUID session ID for thread persistence.

        Returns:
            A structured dict describing the agent's output. Shape:
            - {"type": "ai_reply",         "message": str, "sentiment": str, "intent": str}
            - {"type": "escalation_ticket", "message": str, "summary": str, "sentiment": str, "intent": str}
            - {"type": "blocked",           "message": str}
            - {"type": "error",             "message": str, "error": str}
        """
        config = {"configurable": {"thread_id": thread_id}}
        input_data = {"messages": [HumanMessage(content=message)]}

        try:
            response = self.graph.invoke(input=input_data, config=config)
            raw_content = response["messages"][-1].content

            # CRM Update Subroutine: Sync profile details when turn finishes
            # final_state = self.graph.get_state(config).values
            # phone = ""
            # extracted_params = final_state.get("extracted_parameters") or {}
            # gathered_params = final_state.get("gathered_parameters") or {}
            # if extracted_params.get("phone"):
            #     phone = extracted_params["phone"]
            # elif gathered_params.get("phone"):
            #     phone = gathered_params["phone"]
            #
            # metadata = final_state.get("analyzer_metadata")
            # if phone and metadata and metadata.get("knowledge_graph"):
            #     from .tools import update_crm_profile
            #     update_crm_profile(
            #         phone,
            #         {
            #             "knowledge_graph": metadata["knowledge_graph"],
            #             "evidence": metadata.get("evidence", ""),
            #             "directive": metadata.get("directive", ""),
            #         },
            #     )

            # --- Try to parse raw_content as JSON first (future-proof) ---
            try:
                parsed = json.loads(raw_content)
                if isinstance(parsed, dict) and "type" in parsed:
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass

            # --- Inspect final graph state to determine response type ---
            final_state = self.graph.get_state(config).values
            is_handoff = final_state.get("is_handoff", False)
            handoff_summary = final_state.get("handoff_summary", "")
            sentiment = final_state.get("sentiment", "neutral")
            next_agent = final_state.get("next_agent", "")

            # Detect escalation: explicit flag OR last routed node was escalator
            escalation_report = final_state.get("escalation_report")
            if is_handoff or next_agent in ("escalate", "escalator") or escalation_report:
                # Ensure conversation exists in DB
                from database import db
                conv = db.get_conversation(thread_id)
                if not conv:
                    conv = db.create_conversation(thread_id, customer_phone=thread_id)

                summary = handoff_summary or (escalation_report.get("summary") if escalation_report else raw_content)
                reason = escalation_report.get("reason") if escalation_report else None
                urgency = escalation_report.get("urgency") if escalation_report else None
                rec_action = escalation_report.get("recommended_action") if escalation_report else None
                metadata = escalation_report.get("metadata") if escalation_report else None

                # Check if ticket already exists
                existing_tickets = db.get_tickets()
                has_open_ticket = any(
                    t["conversation_id"] == thread_id and t["status"] == "open"
                    for t in existing_tickets
                )
                if not has_open_ticket:
                    db.add_to_tickets(
                        conversation_id=thread_id,
                        customer_phone=conv["customer_phone"],
                        summary=summary,
                        reason=reason,
                        urgency=urgency,
                        recommended_action=rec_action,
                        metadata=metadata,
                    )

                # Update conversation status to escalated
                db.update_conversation(
                    thread_id,
                    {
                        "status": "escalated",
                        "handoff_summary": summary,
                    }
                )

                return {
                    "type": "escalation_ticket",
                    "message": raw_content or "ألف سلامة على حضرتك يا فندم، حقك علينا جداً! تم تحويل طلبك وتأكيد حالتك فوراً لمسؤول الاستقبال وطبيب الطوارئ بالعيادة وسيتم التواصل معك مباشرة عبر الهاتف 📱",
                    "summary": summary,
                    "sentiment": sentiment,
                    "intent": "escalation",
                    "escalation_report": escalation_report,
                }

            # Detect blocker node output via known constant text prefix
            if raw_content.startswith("Thank you for reaching out. I am Al-Aqabawi Dental Clinic"):
                return {
                    "type": "blocked",
                    "message": "عفواً، لا يمكن معالجة هذا الطلب حالياً.",
                }

            return {
                "type": "ai_reply",
                "message": raw_content,
                "sentiment": sentiment,
                "intent": "general",
            }

        except Exception as e:
            if isinstance(e, ValueError) and "rate limit" in str(e).lower():
                return {
                    "type": "blocked",
                    "message": "عفواً، يرجى الانتظار لحظة قبل إرسال المزيد من الرسائل."
                }
            try:
                from .tools import add_to_escalation_queue
                error_summary = f"طوارئ / استئاء مريض: {message}"
                report = {
                    "reason": "customer_dissatisfaction",
                    "summary": error_summary,
                    "urgency": 0.95,
                    "metadata": {
                        "failed_query": message,
                        "exception_details": str(e),
                    },
                }
                add_to_escalation_queue(report)

                from database import create_ticket, set_ai_enabled
                create_ticket(thread_id, phone="01012345678", summary=error_summary, urgency=0.95)
                set_ai_enabled(thread_id, 0)
            except Exception:
                report = None

            return {
                "type": "escalation_ticket",
                "message": "ألف سلامة على حضرتك يا فندم، حقك علينا جداً! تم تحويل شكواك وتأكيد حالتك فوراً لمسؤول الاستقبال وطبيب الطوارئ بالعيادة وسيتم التواصل معك مباشرة عبر الهاتف 📱",
                "summary": f"طوارئ / استئاء مريض: {message}",
                "sentiment": "urgent",
                "intent": "escalation",
                "escalation_report": report,
            }


    def get_thread_state(self, thread_id: str) -> Dict:
        """Retrieve the current state of a conversation thread."""
        config = {"configurable": {"thread_id": thread_id}}
        return self.graph.get_state(config).values

    def reset_thread(self, thread_id: str) -> None:
        """Clear graph checkpointer memory for a thread."""
        try:
            if hasattr(self.memory, "storage") and isinstance(self.memory.storage, dict):
                keys_to_delete = [
                    k for k in list(self.memory.storage.keys())
                    if k == thread_id or (isinstance(k, tuple) and len(k) > 0 and k[0] == thread_id)
                ]
                for k in keys_to_delete:
                    del self.memory.storage[k]
                logger.info("Reset memory saver state for thread_id", thread_id=thread_id)
        except Exception as e:
            logger.error("Failed to reset thread state in memory saver", error=str(e))

    def compile_graph(self, checkpointer=None):
        """
        Build and compile the Nuit Bot v2 LangGraph.

        Returns a compiled CompiledGraph ready for invocation.
        """
        if checkpointer is None:
            checkpointer = MemorySaver()

        workflow = StateGraph(ServiceBotState)

        # Register nodes
        workflow.add_node("router", router_node)
        workflow.add_node("simple_qa", simple_qa_node)
        # workflow.add_node("analyzer", analyzer_node)
        # workflow.add_node("need_qa", need_qa_node)
        workflow.add_node("escalator", escalation_node)
        workflow.add_node("blocker", blocker_node)

        # Entry point
        workflow.set_entry_point("router")

        # Router routes to simple_qa, escalator, or blocker
        workflow.add_conditional_edges(
            "router",
            self._route,
            {
                "simple_qa": "simple_qa",
                "analyzer": "simple_qa",
                "escalate": "escalator",
                "blocker": "blocker",
            },
        )

        # Simple QA node always ends the turn (formerly went to analyzer)
        workflow.add_edge("simple_qa", END)

        # Analyzer routes conditionally (Commented out)
        # workflow.add_conditional_edges(
        #     "analyzer",
        #     self._route,
        #     {
        #         "need_qa": "need_qa",
        #         "escalate": "escalator",
        #         "end": END,
        #     },
        # )

        # Need QA node always ends the turn (Commented out)
        # workflow.add_edge("need_qa", END)
        workflow.add_edge("blocker", END)
        workflow.add_edge("escalator", END)

        return workflow.compile(checkpointer=checkpointer)

    def _route(self, state: ServiceBotState) -> str:
        """
        Determine the next node to route to based on the current state.

        Returns:
            The name of the next node to invoke.
        """
        next_agent = state["next_agent"]

        if next_agent is None:
            raise ValueError("Router output is None; cannot determine next node.")

        if next_agent == "simple_qa":
            return "simple_qa"
        elif next_agent == "analyzer":
            # Redirect to simple_qa since analyzer is disconnected
            return "simple_qa"
        elif next_agent == "need_qa":
            return "simple_qa"
        elif next_agent == "escalate" or next_agent == "escalator":
            return "escalate"
        elif next_agent == "blocker" or next_agent == "block":
            return "blocker"
        elif next_agent == "end":
            return "end"
        else:
            raise ValueError(
                f"Router output does not specify a valid route: {next_agent}"
            )

    def clear_memory(self):
        """Wipe all graph checkpointer memory."""
        try:
            self.memory = MemorySaver()
            self.graph = self._build_graph(checkpointer=self.memory)
        except Exception:
            pass

