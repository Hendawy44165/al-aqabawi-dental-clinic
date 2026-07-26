from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from database import (
    get_services, 
    get_available_slots, 
    create_appointment, 
    get_appointments, 
    update_appointment_status,
    update_ticket_status,
    create_ticket,
    update_service_price,
    get_conversations,
    get_conversation_messages,
    add_chat_message,
    set_ai_enabled,
    get_conversation,
    db
)

from pydantic import BaseModel
from core_agent.clinic_bot import ClinicBot

app = FastAPI(title="Al-Aqabawi Dental Clinic API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

bot = ClinicBot()


class AppointmentRequest(BaseModel):
    patient_name: str
    patient_phone: str
    slot_id: int
    notes: Optional[str] = ""

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "thread-1"

class StatusUpdateRequest(BaseModel):
    status: str

class PriceUpdateRequest(BaseModel):
    price: str

class ManualReplyRequest(BaseModel):
    message: str

class AiToggleRequest(BaseModel):
    enabled: int

@app.get("/api/services")
def api_get_services():
    return get_services()

@app.get("/api/slots")
def api_get_slots(doctor_name: Optional[str] = None, date: Optional[str] = None):
    return get_available_slots(doctor_name, date)

@app.get("/api/appointments")
def api_get_appointments():
    return get_appointments()

@app.post("/api/appointments")
def api_create_appointment(req: AppointmentRequest):
    res = create_appointment(req.patient_name, req.patient_phone, req.slot_id, req.notes)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.put("/api/appointments/{id}/status")
def api_update_appointment_status(id: int, req: StatusUpdateRequest):
    return update_appointment_status(id, req.status)

@app.get("/api/tickets")
def api_get_tickets():
    return {"tickets": db.get_tickets()}

@app.put("/api/tickets/{id}/status")
def api_update_ticket_status(id: int, req: StatusUpdateRequest):
    return update_ticket_status(id, req.status)

@app.put("/api/services/{id}/price")
def api_update_service_price(id: int, req: PriceUpdateRequest):
    return update_service_price(id, req.price)

# Conversation & Human Takeover API Routes
@app.get("/api/conversations")
def api_get_conversations():
    return {"conversations": get_conversations()}

@app.get("/api/conversations/{thread_id}/messages")
def api_get_conversation_messages(thread_id: str):
    return {"messages": get_conversation_messages(thread_id)}

@app.put("/api/conversations/{thread_id}/toggle_ai")
def api_toggle_ai(thread_id: str, req: AiToggleRequest):
    return set_ai_enabled(thread_id, req.enabled)

@app.post("/api/reset")
def api_reset():
    bot.clear_memory()
    return db.reset_demo()


@app.post("/api/conversations/{thread_id}/manual_reply")
def api_manual_reply(thread_id: str, req: ManualReplyRequest):
    add_chat_message(thread_id, "human", req.message)
    return {"success": True}


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        thread_id = req.thread_id or "thread-1"
        conv = get_conversation(thread_id)
        
        # Log user message into chat database
        add_chat_message(thread_id, "user", req.message)
        
        # Check if Human Agent has taken over or AI is disabled
        if conv and (conv.get("ai_enabled") == 0 or conv.get("status") in ["escalated", "claimed", "manual"]):
            return {
                "reply": "تم استلام رسالتك، والمحادثة في انتظار الرد البشري حالياً 📱",
                "sentiment": "تحكم بشري",
                "intent": "escalated_human",
                "type": "human_takeover",
                "ai_paused": True
            }

        # Run AI Bot Engine
        res = bot.send_message(req.message, thread_id=thread_id)
        bot_reply = res.get("message", "")
        
        # Log AI bot response into chat database
        add_chat_message(thread_id, "bot", bot_reply)
        
        # Auto-escalate and create ticket if AI detected urgent pain / emergency / complaint
        if (res.get("intent") in ["emergency", "pain_escalation", "escalation"] or 
            res.get("type") == "escalation_ticket" or 
            "طوارئ" in bot_reply or "شكوى" in req.message or "تحويل" in bot_reply):
            create_ticket(thread_id, phone="01012345678", summary=f"طوارئ/شكوى مريض: {req.message}", urgency=0.95)
            set_ai_enabled(thread_id, 0)

            
        return {
            "reply": bot_reply,
            "sentiment": res.get("sentiment"),
            "intent": res.get("intent"),
            "type": res.get("type"),
            "ai_paused": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
