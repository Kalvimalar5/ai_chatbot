# BrightSmile Dental Clinic — AI automation

Helping dental clinics automate patient communication, appointment booking, and follow-ups with AI.

This project uses **Google Gemini** as the receptionist, **FastAPI** as the clinic brain, and **Streamlit** as the patient chat plus staff desk.

## Complete workflow

Patient Inquiry → AI Agent → Patient Information → Calendar Booking → Appointment Confirmation → Automated Reminders → Post-Visit Follow-Up → Future Checkups

| Step | What happens |
|------|----------------|
| 1. New patient inquiry | Website, WhatsApp, or phone. The AI answers services, hours, and pricing, then collects patient details. |
| 2. AI appointment booking | The AI asks about the concern, checks calendar slots, and books automatically. |
| 3. Appointment reminders | WhatsApp/SMS reminders before visits (run from the staff desk). |
| 4. Missed call automation | If nobody answers, the system texts an offer to book. |
| 5. Patient follow-up | After a visit is marked completed, a check-in message is sent. |
| 6. Lead reactivation | Follows up with people who inquired but never booked, and reminds patients when a checkup is due. |
| 7. Staff notifications | The team is alerted on bookings, cancellations, and items that need attention. |

## 1. Get a Gemini API key

1. Open [Google AI Studio](https://aistudio.google.com/apikey).
2. Create an API key and paste it in `.env`:

```
GEMINI_API_KEY=paste_your_real_key_here
GEMINI_MODEL=gemini-3.8-flash
BACKEND_URL=http://127.0.0.1:8000
```

## 2. Install packages

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Start the backend (Terminal 1)

```powershell
.\.venv\Scripts\python -m uvicorn backend.main:app --reload --port 8000
```

Open http://127.0.0.1:8000 — you should see `"status": "ok"`.

## 4. Start the UI (Terminal 2)

```powershell
.\.venv\Scripts\streamlit run frontend/app.py
```

## How to demo it

**Patient chat**

1. Choose Website, WhatsApp, or Phone.
2. Ask hours or prices, then book with a name and phone number.
3. The agent saves the patient, takes a real calendar slot, and confirms.

**Staff desk**

1. See the new booking and the staff notification.
2. Click **Send reminders** (Priya has a visit tomorrow in the demo data).
3. Click **Post-visit follow-up** (Rohan completed a filling yesterday).
4. Click **Reactivate leads** (Ananya inquired and never booked).
5. Click **Checkup due** (Karthik is overdue).
6. Enter a phone number and send a **missed-call** WhatsApp.

Demo records live in `data/clinic_state.json`. **Reset demo data** restores the sample patients.

## How the pieces connect

```
Patient chat (Streamlit)
        │
        ▼
FastAPI /chat  →  Gemini + clinic tools (save patient, slots, book)
        │
        ▼
JSON store  →  appointments, WhatsApp/SMS outbox, staff alerts
        │
        ▼
Staff desk automations (reminders, missed call, follow-up, reactivation)
```
