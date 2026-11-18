"""Deterministic clinic operations the AI tools and staff automations share."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from backend.clinic import CLINIC
from backend.store import add_record, find_patient, load_state, save_state, update_by_id


def _parse(dt: str) -> datetime:
    return datetime.fromisoformat(dt)


def _fmt(dt: datetime) -> str:
    return dt.strftime("%a %d %b %Y, %I:%M %p")


def clinic_info() -> dict[str, Any]:
    return {
        "name": CLINIC["name"],
        "phone": CLINIC["phone"],
        "address": CLINIC["address"],
        "hours": CLINIC["hours"],
        "dentists": CLINIC["dentists"],
        "services": CLINIC["services"],
        "faq": CLINIC["faq"],
    }


def save_patient(
    name: str,
    phone: str,
    concern: str,
    email: str = "",
    channel: str = "website",
) -> dict[str, Any]:
    existing = find_patient(phone=phone, name=name)
    payload = {
        "name": name.strip(),
        "phone": "".join(ch for ch in phone if ch.isdigit()),
        "email": email.strip(),
        "concern": concern.strip(),
        "channel": channel,
        "status": existing["status"] if existing else "lead",
        "booked": bool(existing.get("booked")) if existing else False,
        "inquired_at": existing.get("inquired_at") if existing else datetime.now().isoformat(timespec="seconds"),
    }
    if existing:
        updated = update_by_id("patients", existing["id"], payload)
        return {"ok": True, "patient": updated, "created": False}
    payload["last_visit"] = None
    payload["next_checkup_due"] = None
    created = add_record("patients", payload)
    return {"ok": True, "patient": created, "created": True}


def _slot_range(days_ahead: int = 7) -> list[datetime]:
    now = datetime.now().replace(second=0, microsecond=0)
    start_day = now.date()
    slots: list[datetime] = []
    for day_offset in range(0, days_ahead + 1):
        day = start_day + timedelta(days=day_offset)
        if day.weekday() in CLINIC["closed_weekdays"]:
            continue
        cursor = datetime.combine(day, datetime.min.time()).replace(hour=CLINIC["open_hour"])
        close = datetime.combine(day, datetime.min.time()).replace(hour=CLINIC["close_hour"])
        while cursor < close:
            if cursor.hour == CLINIC["lunch_hour"]:
                cursor += timedelta(hours=1)
                continue
            if cursor > now:
                slots.append(cursor)
            cursor += timedelta(minutes=CLINIC["slot_minutes"])
    return slots


def _taken_starts() -> set[str]:
    taken: set[str] = set()
    for apt in load_state().get("appointments", []):
        if apt.get("status") == "booked":
            taken.add(apt["start"])
    return taken


def list_available_slots(days_ahead: int = 7, limit: int = 8) -> dict[str, Any]:
    taken = _taken_starts()
    open_slots = []
    for start in _slot_range(days_ahead):
        iso = start.isoformat()
        if iso in taken:
            continue
        end = start + timedelta(minutes=CLINIC["slot_minutes"])
        open_slots.append(
            {
                "start": iso,
                "end": end.isoformat(),
                "label": _fmt(start),
                "dentist": "First available (Dr. Meera Iyer or Dr. Arjun Rao)",
            }
        )
        if len(open_slots) >= limit:
            break
    return {"ok": True, "slots": open_slots, "clinic_hours": CLINIC["hours"]}


def book_appointment(
    name: str,
    phone: str,
    start: str,
    service: str = "Consultation",
    dentist: str = "Dr. Meera Iyer",
    concern: str = "",
    channel: str = "website",
) -> dict[str, Any]:
    try:
        start_dt = _parse(start)
    except ValueError:
        return {"ok": False, "error": "Use an ISO datetime from list_available_slots, for example 2026-11-13T10:00:00."}

    if start_dt.weekday() in CLINIC["closed_weekdays"]:
        return {"ok": False, "error": "The clinic is closed on Sunday."}
    if start_dt.hour == CLINIC["lunch_hour"]:
        return {"ok": False, "error": "That time is during the lunch break."}

    end_dt = start_dt + timedelta(minutes=CLINIC["slot_minutes"])
    taken = _taken_starts()
    if start_dt.isoformat() in taken:
        return {"ok": False, "error": "That slot is already booked. Ask for other times."}

    saved = save_patient(name=name, phone=phone, concern=concern or service, channel=channel)
    patient = saved["patient"]
    update_by_id("patients", patient["id"], {"status": "patient", "booked": True})

    appointment = add_record(
        "appointments",
        {
            "patient_id": patient["id"],
            "patient_name": patient["name"],
            "phone": patient["phone"],
            "service": service,
            "dentist": dentist,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "status": "booked",
            "channel": channel,
            "notes": concern,
            "reminder_sent": False,
            "followup_sent": False,
        },
    )

    confirmation = (
        f"{CLINIC['name']}: your {service} with {dentist} is booked for {_fmt(start_dt)}. "
        f"Please arrive 10 minutes early. Reply if you need to reschedule."
    )
    add_record(
        "messages",
        {
            "to": patient["phone"],
            "to_name": patient["name"],
            "channel": "whatsapp" if channel == "whatsapp" else "sms",
            "template": "confirmation",
            "body": confirmation,
        },
    )
    notify_staff(
        kind="booked",
        title=f"New booking: {patient['name']}",
        body=f"{service} with {dentist} on {_fmt(start_dt)} via {channel}.",
    )
    return {
        "ok": True,
        "appointment": appointment,
        "confirmation_message": confirmation,
    }


def cancel_appointment(appointment_id: str, reason: str = "") -> dict[str, Any]:
    apt = update_by_id("appointments", appointment_id, {"status": "cancelled", "cancel_reason": reason})
    if not apt:
        return {"ok": False, "error": "Appointment not found."}
    notify_staff(
        kind="cancelled",
        title=f"Cancelled: {apt.get('patient_name')}",
        body=f"{apt.get('service')} on {apt.get('start')} was cancelled. {reason}".strip(),
    )
    return {"ok": True, "appointment": apt}


def notify_staff(kind: str, title: str, body: str) -> dict[str, Any]:
    note = add_record(
        "notifications",
        {"type": kind, "title": title, "body": body, "read": False},
    )
    return {"ok": True, "notification": note}


def lookup_patient(phone: str = "", name: str = "") -> dict[str, Any]:
    patient = find_patient(phone=phone or None, name=name or None)
    if not patient:
        return {"ok": False, "error": "No matching patient."}
    apts = [
        apt
        for apt in load_state().get("appointments", [])
        if apt.get("patient_id") == patient["id"]
    ]
    return {"ok": True, "patient": patient, "appointments": apts}


def send_reminders() -> dict[str, Any]:
    """Send WhatsApp/SMS reminders for visits in the next 24 hours."""
    now = datetime.now()
    horizon = now + timedelta(hours=24)
    sent: list[dict[str, Any]] = []
    for apt in load_state().get("appointments", []):
        if apt.get("status") != "booked" or apt.get("reminder_sent"):
            continue
        start = _parse(apt["start"])
        if now <= start <= horizon:
            body = (
                f"Reminder from {CLINIC['name']}: {_fmt(start)} with {apt['dentist']} "
                f"({apt['service']}). Reply YES to confirm or call {CLINIC['phone']} to reschedule."
            )
            msg = add_record(
                "messages",
                {
                    "to": apt["phone"],
                    "to_name": apt["patient_name"],
                    "channel": "whatsapp",
                    "template": "reminder",
                    "body": body,
                },
            )
            update_by_id("appointments", apt["id"], {"reminder_sent": True})
            sent.append(msg)
    return {"ok": True, "sent": len(sent), "messages": sent}


def missed_call(phone: str, name: str = "there") -> dict[str, Any]:
    display = name if name != "there" else "there"
    body = (
        f"Hi {display}, sorry we missed your call at {CLINIC['name']}. "
        "I can help you book an appointment on WhatsApp. Tell me your name, "
        "what is bothering you, and a preferred day."
    )
    msg = add_record(
        "messages",
        {
            "to": "".join(ch for ch in phone if ch.isdigit()),
            "to_name": name,
            "channel": "whatsapp",
            "template": "missed_call",
            "body": body,
        },
    )
    notify_staff(
        kind="attention",
        title="Missed call follow-up sent",
        body=f"Auto-message sent to {phone}.",
    )
    save_patient(name=name if name != "there" else f"Caller {phone[-4:]}", phone=phone, concern="Missed call", channel="phone")
    return {"ok": True, "message": msg}


def post_visit_followups() -> dict[str, Any]:
    sent: list[dict[str, Any]] = []
    for apt in load_state().get("appointments", []):
        if apt.get("status") != "completed" or apt.get("followup_sent"):
            continue
        body = (
            f"Hi {apt['patient_name']}, this is {CLINIC['name']}. How are you feeling after yesterday's "
            f"{apt['service']}? If you need a follow-up visit, reply here and I will book it."
        )
        msg = add_record(
            "messages",
            {
                "to": apt["phone"],
                "to_name": apt["patient_name"],
                "channel": "whatsapp",
                "template": "followup",
                "body": body,
            },
        )
        update_by_id("appointments", apt["id"], {"followup_sent": True})
        sent.append(msg)
    return {"ok": True, "sent": len(sent), "messages": sent}


def reactivate_leads() -> dict[str, Any]:
    sent: list[dict[str, Any]] = []
    for patient in load_state().get("patients", []):
        if patient.get("status") != "lead" or patient.get("booked"):
            continue
        if patient.get("reactivation_sent"):
            continue
        body = (
            f"Hi {patient['name']}, you asked {CLINIC['name']} about {patient.get('concern') or 'a visit'} "
            "and we still have openings this week. Would you like me to reserve a slot?"
        )
        msg = add_record(
            "messages",
            {
                "to": patient["phone"],
                "to_name": patient["name"],
                "channel": patient.get("channel") or "whatsapp",
                "template": "reactivation",
                "body": body,
            },
        )
        update_by_id("patients", patient["id"], {"reactivation_sent": True})
        sent.append(msg)
    return {"ok": True, "sent": len(sent), "messages": sent}


def checkup_reminders() -> dict[str, Any]:
    today = datetime.now().date().isoformat()
    sent: list[dict[str, Any]] = []
    for patient in load_state().get("patients", []):
        due = patient.get("next_checkup_due")
        if not due or due > today or patient.get("checkup_reminder_sent"):
            continue
        body = (
            f"Hi {patient['name']}, it is time for your routine dental checkup at {CLINIC['name']}. "
            "Reply with a preferred morning or evening and I will book it."
        )
        msg = add_record(
            "messages",
            {
                "to": patient["phone"],
                "to_name": patient["name"],
                "channel": "sms",
                "template": "checkup",
                "body": body,
            },
        )
        update_by_id("patients", patient["id"], {"checkup_reminder_sent": True})
        sent.append(msg)
    return {"ok": True, "sent": len(sent), "messages": sent}


def mark_completed(appointment_id: str) -> dict[str, Any]:
    apt = update_by_id("appointments", appointment_id, {"status": "completed"})
    if not apt:
        return {"ok": False, "error": "Appointment not found."}
    visit_day = _parse(apt["start"]).date().isoformat()
    due = (_parse(apt["start"]).date() + timedelta(days=180)).isoformat()
    update_by_id(
        "patients",
        apt["patient_id"],
        {"last_visit": visit_day, "next_checkup_due": due, "status": "patient"},
    )
    return {"ok": True, "appointment": apt}


def dashboard() -> dict[str, Any]:
    state = load_state()
    return {
        "clinic": clinic_info(),
        "patients": state.get("patients", []),
        "appointments": sorted(
            state.get("appointments", []),
            key=lambda a: a.get("start", ""),
            reverse=True,
        ),
        "messages": list(reversed(state.get("messages", []))),
        "notifications": list(reversed(state.get("notifications", []))),
        "available": list_available_slots()["slots"],
    }


def mark_notification_read(notification_id: str) -> dict[str, Any]:
    note = update_by_id("notifications", notification_id, {"read": True})
    if not note:
        return {"ok": False, "error": "Notification not found."}
    return {"ok": True, "notification": note}


def complete_appointment(appointment_id: str) -> dict[str, Any]:
    return mark_completed(appointment_id)
