"""JSON file store for patients, appointments, outbound messages, and staff alerts."""

from __future__ import annotations

import json
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from backend.config import PROJECT_ROOT

DATA_FILE = PROJECT_ROOT / "data" / "clinic_state.json"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


def _seed() -> dict[str, Any]:
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    last_week = today - timedelta(days=4)
    checkup_due = today - timedelta(days=11)

    priya = {
        "id": "pat_priya",
        "name": "Priya Sharma",
        "phone": "9876501001",
        "email": "priya.sharma@example.com",
        "channel": "website",
        "concern": "Tooth sensitivity",
        "status": "patient",
        "last_visit": None,
        "next_checkup_due": None,
        "created_at": _now(),
    }
    rohan = {
        "id": "pat_rohan",
        "name": "Rohan Menon",
        "phone": "9876501002",
        "email": "rohan.menon@example.com",
        "channel": "whatsapp",
        "concern": "Filling completed",
        "status": "patient",
        "last_visit": yesterday.isoformat(),
        "next_checkup_due": (yesterday + timedelta(days=180)).isoformat(),
        "created_at": _now(),
    }
    ananya = {
        "id": "pat_ananya",
        "name": "Ananya Krishnan",
        "phone": "9876501003",
        "email": "ananya.k@example.com",
        "channel": "whatsapp",
        "concern": "Wisdom tooth pain",
        "status": "lead",
        "last_visit": None,
        "next_checkup_due": None,
        "created_at": last_week.isoformat() + "T10:15:00",
        "inquired_at": last_week.isoformat() + "T10:15:00",
        "booked": False,
    }
    karthik = {
        "id": "pat_karthik",
        "name": "Karthik Raman",
        "phone": "9876501004",
        "email": "karthik.r@example.com",
        "channel": "phone",
        "concern": "Routine checkup",
        "status": "patient",
        "last_visit": (today - timedelta(days=190)).isoformat(),
        "next_checkup_due": checkup_due.isoformat(),
        "created_at": _now(),
    }

    return {
        "patients": [priya, rohan, ananya, karthik],
        "appointments": [
            {
                "id": "apt_priya_tmrw",
                "patient_id": priya["id"],
                "patient_name": priya["name"],
                "phone": priya["phone"],
                "service": "Consultation",
                "dentist": "Dr. Meera Iyer",
                "start": datetime.combine(tomorrow, datetime.min.time()).replace(
                    hour=10, minute=0
                ).isoformat(),
                "end": datetime.combine(tomorrow, datetime.min.time()).replace(
                    hour=10, minute=30
                ).isoformat(),
                "status": "booked",
                "channel": "website",
                "notes": "Sensitivity on upper left.",
                "reminder_sent": False,
                "followup_sent": False,
            },
            {
                "id": "apt_rohan_yday",
                "patient_id": rohan["id"],
                "patient_name": rohan["name"],
                "phone": rohan["phone"],
                "service": "Filling",
                "dentist": "Dr. Arjun Rao",
                "start": datetime.combine(yesterday, datetime.min.time()).replace(
                    hour=11, minute=0
                ).isoformat(),
                "end": datetime.combine(yesterday, datetime.min.time()).replace(
                    hour=11, minute=30
                ).isoformat(),
                "status": "completed",
                "channel": "whatsapp",
                "notes": "Composite filling on molar.",
                "reminder_sent": True,
                "followup_sent": False,
            },
        ],
        "messages": [],
        "notifications": [
            {
                "id": "ntf_seed",
                "type": "attention",
                "title": "Demo clinic is ready",
                "body": "Seed patients, one booked visit, one completed visit, one lead, and one overdue checkup are loaded.",
                "read": False,
                "created_at": _now(),
            }
        ],
    }


def _ensure() -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text(json.dumps(_seed(), indent=2), encoding="utf-8")


def load_state() -> dict[str, Any]:
    with _LOCK:
        _ensure()
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_state(state: dict[str, Any]) -> None:
    with _LOCK:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def reset_state() -> dict[str, Any]:
    state = _seed()
    save_state(state)
    return state


def add_record(collection: str, record: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    if "id" not in record:
        prefixes = {
            "patients": "pat",
            "appointments": "apt",
            "messages": "msg",
            "notifications": "ntf",
        }
        record["id"] = _new_id(prefixes.get(collection, "rec"))
    if "created_at" not in record:
        record["created_at"] = _now()
    state.setdefault(collection, []).append(record)
    save_state(state)
    return record


def update_by_id(collection: str, record_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    state = load_state()
    for item in state.get(collection, []):
        if item.get("id") == record_id:
            item.update(changes)
            save_state(state)
            return item
    return None


def find_patient(*, phone: str | None = None, name: str | None = None) -> dict[str, Any] | None:
    state = load_state()
    phone_digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    name_l = (name or "").strip().lower()
    for patient in state.get("patients", []):
        stored_phone = "".join(ch for ch in str(patient.get("phone", "")) if ch.isdigit())
        if phone_digits and stored_phone.endswith(phone_digits[-10:]):
            return patient
        if name_l and str(patient.get("name", "")).lower() == name_l:
            return patient
    return None
