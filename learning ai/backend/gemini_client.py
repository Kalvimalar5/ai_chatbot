"""Talk to Google Gemini as the BrightSmile dental receptionist."""

from __future__ import annotations

from typing import Any, Callable

from google import genai
from google.genai import types

from backend.clinic import CLINIC
from backend.config import get_gemini_api_key, get_gemini_model
from backend.workflow import (
    book_appointment,
    cancel_appointment,
    clinic_info,
    list_available_slots,
    lookup_patient,
    notify_staff,
    save_patient,
)

SYSTEM_INSTRUCTION = f"""You are the AI receptionist for {CLINIC['name']}.
Address: {CLINIC['address']}. Phone: {CLINIC['phone']}.
Hours: {CLINIC['hours']}.

Your job is to run this clinic workflow in a natural conversation:
1. New patient inquiry — answer services, hours, and pricing. Collect name, phone, and the dental concern.
2. Appointment booking — ask about the concern, call list_available_slots, then book_appointment with a real slot start time from that list.
3. Confirm the booking in plain language. A WhatsApp/SMS confirmation is sent automatically when you book.
4. If the channel is phone and the person says nobody answered or this is a missed call, be extra brief and offer to book now.
5. After booking, mention that they will get a reminder before the visit and a follow-up after treatment.
6. If they inquired before but never booked, help them finish booking.
7. Staff are notified automatically when you book or cancel.

Rules:
- Be warm, short, and professional. Do not give a medical diagnosis. For severe swelling, bleeding, or trauma, tell them to come in urgently or visit emergency care.
- Always save_patient once you have a name and phone.
- Never invent an open slot. Use list_available_slots, then pass that exact start value to book_appointment.
- Default service is Consultation if they are unsure.
- Pick Dr. Meera Iyer for cleanings, fillings, and checkups. Pick Dr. Arjun Rao for root canal, extraction, or whitening.
- Prices are estimates; the dentist confirms the final fee after an exam.
- If a tool returns ok=false, explain the problem and offer another time.
"""

TOOLS: dict[str, Callable[..., Any]] = {
    "clinic_info": clinic_info,
    "save_patient": save_patient,
    "list_available_slots": list_available_slots,
    "book_appointment": book_appointment,
    "cancel_appointment": cancel_appointment,
    "lookup_patient": lookup_patient,
    "notify_staff": notify_staff,
}

_CLIENT: genai.Client | None = None


def _client() -> genai.Client:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = genai.Client(api_key=get_gemini_api_key())
    return _CLIENT


def _history_contents(history: list[dict], message: str, channel: str) -> list[types.Content]:
    contents: list[types.Content] = []
    for turn in history:
        role = "user" if turn["role"] == "user" else "model"
        text = (turn.get("content") or "").strip()
        if not text:
            continue
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    channel_note = (
        f"[Channel: {channel}. You are chatting on the clinic website, WhatsApp, or a phone call transcript.]"
    )
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"{channel_note}\n{message}")],
        )
    )
    return contents


def _run_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    fn = TOOLS.get(name)
    if fn is None:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    try:
        result = fn(**(args or {}))
    except TypeError as exc:
        return {"ok": False, "error": f"Bad arguments for {name}: {exc}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    if isinstance(result, dict):
        return result
    return {"ok": True, "result": result}


def generate_reply(message: str, history: list[dict], channel: str = "website") -> str:
    """Send the patient's message plus prior turns to Gemini with clinic tools."""
    contents = _history_contents(history, message, channel)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=list(TOOLS.values()),
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    for _ in range(8):
        response = _client().models.generate_content(
            model=get_gemini_model(),
            contents=contents,
            config=config,
        )
        calls = list(response.function_calls or [])
        if not calls:
            text = (response.text or "").strip()
            if not text:
                return "Sorry, I could not reply just now. Please try again in a moment."
            return text

        model_content = response.candidates[0].content
        contents.append(model_content)
        function_parts: list[types.Part] = []
        for call in calls:
            result = _run_tool(call.name, dict(call.args or {}))
            function_parts.append(
                types.Part.from_function_response(name=call.name, response=result)
            )
        contents.append(types.Content(role="user", parts=function_parts))

    return "I started booking but needed too many steps. Please send your name, phone, and a preferred day again."
