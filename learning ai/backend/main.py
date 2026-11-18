"""FastAPI server for BrightSmile Dental Clinic automation."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.gemini_client import generate_reply
from backend.store import reset_state
from backend.workflow import (
    checkup_reminders,
    complete_appointment,
    dashboard,
    mark_notification_read,
    missed_call,
    post_visit_followups,
    reactivate_leads,
    send_reminders,
)

app = FastAPI(
    title="BrightSmile Dental Clinic",
    description="AI patient communication, booking, reminders, and follow-ups.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8501", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatTurn(BaseModel):
    role: str = Field(description="user or assistant")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    history: list[ChatTurn] = Field(default_factory=list)
    channel: str = Field(default="website")


class ChatResponse(BaseModel):
    reply: str


class MissedCallRequest(BaseModel):
    phone: str = Field(min_length=6)
    name: str = "there"


class AppointmentIdRequest(BaseModel):
    appointment_id: str


class NotificationIdRequest(BaseModel):
    notification_id: str


@app.get("/")
def health() -> dict:
    return {
        "app": "BrightSmile Dental Clinic",
        "workflow": "inquiry → agent → booking → reminders → follow-up → checkups",
        "status": "ok",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        history = [turn.model_dump() for turn in request.history]
        reply = generate_reply(request.message.strip(), history, request.channel)
        return ChatResponse(reply=reply)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini request failed: {exc}",
        ) from exc


@app.get("/dashboard")
def get_dashboard() -> dict:
    return dashboard()


@app.post("/automations/reminders")
def run_reminders() -> dict:
    return send_reminders()


@app.post("/automations/missed-call")
def run_missed_call(request: MissedCallRequest) -> dict:
    return missed_call(phone=request.phone, name=request.name)


@app.post("/automations/follow-ups")
def run_followups() -> dict:
    return post_visit_followups()


@app.post("/automations/reactivate-leads")
def run_leads() -> dict:
    return reactivate_leads()


@app.post("/automations/checkups")
def run_checkups() -> dict:
    return checkup_reminders()


@app.post("/appointments/complete")
def complete(request: AppointmentIdRequest) -> dict:
    result = complete_appointment(request.appointment_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/notifications/read")
def read_notification(request: NotificationIdRequest) -> dict:
    result = mark_notification_read(request.notification_id)
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result


@app.post("/demo/reset")
def reset_demo() -> dict:
    reset_state()
    return {"ok": True, "message": "Demo data restored."}
