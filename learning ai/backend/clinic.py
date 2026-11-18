"""Clinic profile used by the AI receptionist and the staff desk."""

CLINIC = {
    "name": "BrightSmile Dental Clinic",
    "phone": "+91 98765 00011",
    "address": "14 Anna Nagar Main Road, Chennai",
    "hours": "Monday to Saturday, 9:00 AM to 5:00 PM. Closed Sunday. Lunch break 1:00 PM to 2:00 PM.",
    "slot_minutes": 30,
    "open_hour": 9,
    "close_hour": 17,
    "lunch_hour": 13,
    "closed_weekdays": [6],  # Sunday
    "dentists": [
        {
            "id": "dr-meera",
            "name": "Dr. Meera Iyer",
            "focus": "General dentistry, cleanings, fillings",
        },
        {
            "id": "dr-arjun",
            "name": "Dr. Arjun Rao",
            "focus": "Root canal, extractions, cosmetic work",
        },
    ],
    "services": [
        {"name": "Consultation", "price": "₹500", "duration_min": 30},
        {"name": "Cleaning / Scaling", "price": "₹1,500", "duration_min": 30},
        {"name": "Filling", "price": "₹2,000–₹4,000", "duration_min": 30},
        {"name": "Root canal", "price": "₹6,000–₹9,000", "duration_min": 60},
        {"name": "Extraction", "price": "₹1,500–₹3,000", "duration_min": 30},
        {"name": "Teeth whitening", "price": "₹8,000", "duration_min": 60},
        {"name": "Braces consult", "price": "₹800", "duration_min": 30},
    ],
    "faq": [
        "Emergency walk-ins are taken when a slot is free; otherwise we book the next opening.",
        "Please arrive 10 minutes early with a photo ID.",
        "Cancellations should be made at least 4 hours before the visit.",
    ],
}
