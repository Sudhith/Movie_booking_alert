# backend/checker.py
import time
import json
import requests
from bs4 import BeautifulSoup

from notifier import send_alert
from agent import booking_decision

DATA_FILE = "data.json"


def safe_read_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def safe_write_json(path: str, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    import os
    os.replace(tmp, path)


def fetch_page(url: str, retries=3, timeout=12) -> str:
    headers = {"User-Agent": "Mozilla/5.0 CinePing/1.0"}
    last_err = None

    for _ in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.text
            last_err = f"HTTP {r.status_code}"
        except Exception as e:
            last_err = str(e)
        time.sleep(1.5)

    raise RuntimeError(f"Failed to fetch page: {last_err}")


def check_booking(url: str) -> str:
    html = fetch_page(url)
    soup = BeautifulSoup(html, "html.parser")

    # Extract visible text + button-like terms
    page_text = soup.get_text(separator=" ", strip=True)

    # Smart decision
    return booking_decision(page_text)


def run_once():
    items = safe_read_json(DATA_FILE, default=[])

    if not items:
        print("No tracking items found.")
        return

    remaining = []
    for item in items:
        if not item.get("active", True):
            remaining.append(item)
            continue

        movie = item.get("movie", "Unknown")
        theatre = item.get("theatre", "Unknown")
        url = item.get("url", "")

        if not url:
            continue

        try:
            status = check_booking(url)
            print(f"[{movie}] at [{theatre}] -> {status}")

            if status == "OPEN":
                send_alert(f"🎬 Booking OPEN!\nMovie: {movie}\nTheatre: {theatre}\nLink: {url}")
                # do not keep it (stop tracking)
            else:
                remaining.append(item)

        except Exception as e:
            print(f"Error checking {movie}: {e}")
            remaining.append(item)

    safe_write_json(DATA_FILE, remaining)


if __name__ == "__main__":
    # Local mode: keep running
    while True:
        run_once()
        time.sleep(300)  # 5 minutes
