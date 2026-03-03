# backend/agent.py

import re

def booking_decision(page_text: str) -> str:
    text = (page_text or "").lower()

    # Strong signals that booking is open
    open_signals = [
        "book tickets",
        "select seats",
        "seat layout",
        "proceed",
        "pay",
        "showtimes",
        "show timings",
        "available shows",
        "tickets available",
        "select show",
        "choose seats",
    ]

    # Common signals that booking is not open yet
    closed_signals = [
        "booking opens soon",
        "coming soon",
        "not available",
        "no shows available",
        "releasing on",
        "stay tuned",
    ]

    # Detect if ANY time like 10:30 AM exists (very strong hint showtimes exist)
    time_pattern = r"\b(1[0-2]|0?[1-9]):[0-5][0-9]\s?(am|pm)\b"
    has_time = bool(re.search(time_pattern, text))

    # If it says coming soon etc -> NOT OPEN
    for s in closed_signals:
        if s in text:
            return "NOT OPEN"

    # If it has book / seat / show actions -> OPEN
    for s in open_signals:
        if s in text:
            return "OPEN"

    # If any showtime exists -> OPEN
    if has_time:
        return "OPEN"

    return "NOT OPEN"
