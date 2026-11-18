"""BrightSmile Dental Clinic — patient chat and staff desk.

Run from the project root (with the FastAPI server already running):
    .venv\\Scripts\\streamlit run frontend/app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="BrightSmile Dental Clinic",
    page_icon="🦷",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.4rem; }
      .hint { color: #5b6573; font-size: 0.92rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str) -> dict | None:
    try:
        response = httpx.get(f"{BACKEND_URL}{path}", timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        st.error(
            "Cannot reach the backend. In another terminal run:\n\n"
            "`.venv\\Scripts\\python -m uvicorn backend.main:app --reload --port 8000`"
        )
        return None
    except Exception as exc:
        st.error(f"Backend error: {exc}")
        return None


def api_post(path: str, payload: dict | None = None) -> dict | str:
    try:
        response = httpx.post(f"{BACKEND_URL}{path}", json=payload or {}, timeout=90.0)
        response.raise_for_status()
        return response.json()
    except httpx.ConnectError:
        return (
            "Cannot reach the backend. Start FastAPI with:\n\n"
            "`.venv\\Scripts\\python -m uvicorn backend.main:app --reload --port 8000`"
        )
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except Exception:
            detail = exc.response.text
        return f"Backend error: {detail}"
    except Exception as exc:
        return f"Something went wrong: {exc}"


def ask_backend(user_text: str, history: list[dict], channel: str) -> str:
    payload = {"message": user_text, "history": history, "channel": channel}
    result = api_post("/chat", payload)
    if isinstance(result, str):
        return result
    return result.get("reply", "No reply returned.")


st.title("BrightSmile Dental Clinic")
st.caption(
    "Patient inquiry → AI agent → booking → confirmation → reminders → follow-up → checkups"
)

patient_tab, staff_tab, workflow_tab = st.tabs(
    ["Patient chat", "Staff desk", "Workflow"]
)

with patient_tab:
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("Talk to the clinic AI")
        channel = st.radio(
            "How the patient contacted the clinic",
            ["website", "whatsapp", "phone"],
            horizontal=True,
            format_func=lambda value: {
                "website": "Website chat",
                "whatsapp": "WhatsApp",
                "phone": "Phone / call transcript",
            }[value],
        )
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "channel" not in st.session_state:
            st.session_state.channel = channel
        if st.session_state.channel != channel:
            st.session_state.channel = channel
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        prompt = st.chat_input("Ask about hours, prices, or book a visit...")
        if prompt:
            prior_history = list(st.session_state.messages)
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Clinic AI is responding..."):
                    reply = ask_backend(prompt, prior_history, channel)
                st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})

        if st.button("Clear this conversation"):
            st.session_state.messages = []
            st.rerun()

    with right:
        st.subheader("Try these")
        st.markdown(
            """
- *Hi, what are your hours and how much is a cleaning?*
- *My name is Divya, phone 9876501888. I have a toothache. Book the next opening.*
- *I called but nobody picked up. Can you still help me book?*
            """
        )
        data = api_get("/dashboard")
        if data:
            st.subheader("Next open slots")
            slots = data.get("available") or []
            if not slots:
                st.write("No open slots in the next week.")
            for slot in slots[:6]:
                st.write(f"- {slot['label']}")

with staff_tab:
    data = api_get("/dashboard")
    if data:
        unread = [n for n in data.get("notifications", []) if not n.get("read")]
        booked = [a for a in data.get("appointments", []) if a.get("status") == "booked"]
        leads = [p for p in data.get("patients", []) if p.get("status") == "lead"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Booked visits", len(booked))
        c2.metric("Unread staff alerts", len(unread))
        c3.metric("Open leads", len(leads))
        c4.metric("Outbound messages", len(data.get("messages", [])))

        st.subheader("Run automations")
        st.caption("In a real clinic these would run on a schedule. Here you trigger them.")
        a1, a2, a3, a4, a5 = st.columns(5)
        with a1:
            if st.button("Send reminders"):
                st.session_state.last_automation = api_post("/automations/reminders")
                st.rerun()
        with a2:
            if st.button("Post-visit follow-up"):
                st.session_state.last_automation = api_post("/automations/follow-ups")
                st.rerun()
        with a3:
            if st.button("Reactivate leads"):
                st.session_state.last_automation = api_post("/automations/reactivate-leads")
                st.rerun()
        with a4:
            if st.button("Checkup due"):
                st.session_state.last_automation = api_post("/automations/checkups")
                st.rerun()
        with a5:
            if st.button("Reset demo data"):
                st.session_state.last_automation = api_post("/demo/reset")
                st.rerun()

        with st.form("missed_call"):
            st.write("Missed call automation")
            cols = st.columns(2)
            phone = cols[0].text_input("Caller phone", value="9876501999")
            caller = cols[1].text_input("Caller name", value="Sanjay")
            submitted = st.form_submit_button("Send missed-call WhatsApp")
            if submitted:
                st.session_state.last_automation = api_post(
                    "/automations/missed-call",
                    {"phone": phone, "name": caller},
                )
                st.rerun()

        if st.session_state.get("last_automation"):
            st.success("Automation finished.")
            st.json(st.session_state.last_automation)

        n_col, m_col = st.columns(2)
        with n_col:
            st.subheader("Staff notifications")
            for note in data.get("notifications", [])[:12]:
                badge = "unread" if not note.get("read") else "read"
                st.markdown(f"**{note.get('title')}** · {note.get('type')} · {badge}")
                st.caption(note.get("body"))
                if not note.get("read"):
                    if st.button("Mark read", key=f"read_{note['id']}"):
                        api_post("/notifications/read", {"notification_id": note["id"]})
                        st.rerun()
        with m_col:
            st.subheader("WhatsApp / SMS outbox")
            messages = data.get("messages") or []
            if not messages:
                st.write("No automated messages yet.")
            for msg in messages[:12]:
                st.markdown(f"**{msg.get('template')}** → {msg.get('to_name')} ({msg.get('channel')})")
                st.caption(msg.get("body"))

        st.subheader("Calendar")
        for apt in data.get("appointments", []):
            cols = st.columns([3, 1, 1])
            cols[0].write(
                f"**{apt.get('patient_name')}** · {apt.get('service')} · "
                f"{apt.get('dentist')} · {apt.get('start')} · **{apt.get('status')}**"
            )
            if apt.get("status") == "booked":
                if cols[1].button("Mark completed", key=f"done_{apt['id']}"):
                    api_post("/appointments/complete", {"appointment_id": apt["id"]})
                    st.rerun()

        st.subheader("Patients")
        st.dataframe(
            [
                {
                    "Name": p.get("name"),
                    "Phone": p.get("phone"),
                    "Status": p.get("status"),
                    "Concern": p.get("concern"),
                    "Channel": p.get("channel"),
                    "Checkup due": p.get("next_checkup_due") or "",
                }
                for p in data.get("patients", [])
            ],
            hide_index=True,
            use_container_width=True,
        )

with workflow_tab:
    st.subheader("Complete workflow")
    st.markdown(
        """
Patient Inquiry → AI Agent → Patient Information → Calendar Booking → Appointment Confirmation → Automated Reminders → Post-Visit Follow-Up → Future Checkups
        """
    )
    steps = [
        ("1. New patient inquiry", "Website, WhatsApp, or phone. The AI answers hours, services, and prices, then collects name, phone, and the concern."),
        ("2. AI appointment booking", "The agent checks open calendar slots and books automatically."),
        ("3. Appointment reminders", "Staff desk → Send reminders for visits in the next 24 hours."),
        ("4. Missed call automation", "Staff desk → enter the caller number. The system texts an offer to book."),
        ("5. Patient follow-up", "After you mark a visit completed, run Post-visit follow-up."),
        ("6. Lead reactivation", "Reactivate leads who never booked, and remind patients whose checkup is due."),
        ("7. Staff notifications", "Bookings, cancellations, and missed calls appear on the staff desk."),
    ]
    for title, body in steps:
        st.markdown(f"**{title}**")
        st.write(body)
