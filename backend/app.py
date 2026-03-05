# backend/app.py (CLEAN + WORKING)

import os
import json
import time
from typing import List, Dict, Any

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from checker import check_booking
from notifier import send_alert

load_dotenv()

DATA_FILE = "data.json"
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ---------- Utilities ----------
def safe_read_json(path: str, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def safe_write_json(path: str, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def validate_tracking_payload(data: Dict[str, Any]) -> List[str]:
    # URL must be present for checking
    required = ["movie", "theatre", "date", "timing", "platform", "url"]
    return [k for k in required if not data.get(k)]

@app.route("/")
def home():
    return "CinePing backend running ✅"

# ---------- Tracking ----------
@app.route("/add", methods=["POST"])
def add_tracking():
    data = request.get_json(force=True, silent=True) or {}
    data["location"] = "Visakhapatnam"

    missing = validate_tracking_payload(data)

    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    all_items = safe_read_json(DATA_FILE, default=[])

    # fingerprint to detect duplicates
    fingerprint = f"{data['movie']}|{data['theatre']}|{data['location']}|{data['date']}|{data['platform']}|{data['url']}"

    already = any(
        f"{i.get('movie')}|{i.get('theatre')}|{i.get('location')}|{i.get('date')}|{i.get('platform')}|{i.get('url')}"
        == fingerprint
        for i in all_items
    )

    # Add only if new
    if not already:
        data["created_at"] = int(time.time())
        data["active"] = True
        all_items.append(data)
        safe_write_json(DATA_FILE, all_items)

    # ✅ INSTANT CHECK ALWAYS (even if already tracking)
    try:
        status = check_booking(data["url"])

        if status == "OPEN":
            send_alert(
                f"🎬 TICKETS AVAILABLE NOW ✅\n\n"
                f"🎥 Movie: {data['movie']}\n"
                f"📍 City: {data['location']}\n"
                f"🏛️ Theatre: {data['theatre']}\n"
                f"📅 Date: {data['date']}\n"
                f"⏰ Timing: {data['timing']}\n\n"
                f"🔗 Link: {data['url']}"
            )

            return jsonify({
                "status": "Tickets already available ✅ Telegram sent!",
                "open": True,
                "already": already
            }), 200

    except Exception as e:
        print("Instant check failed:", e)

    return jsonify({
        "status": "Already tracking ✅" if already else "Tracking started ✅",
        "open": False,
        "already": already
    }), 200

@app.route("/list", methods=["GET"])
def list_tracking():
    return jsonify(safe_read_json(DATA_FILE, default=[])), 200

@app.route("/delete", methods=["POST"])
def delete_tracking():
    payload = request.get_json(force=True, silent=True) or {}
    idx = payload.get("index")

    all_items = safe_read_json(DATA_FILE, default=[])

    if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(all_items):
        return jsonify({"error": "Invalid index"}), 400

    removed = all_items.pop(idx)
    safe_write_json(DATA_FILE, all_items)

    return jsonify({"status": "Deleted ✅", "removed": removed}), 200

# ---------- TMDB ----------
def tmdb_get(endpoint: str, params: Dict[str, Any] = None):
    if not TMDB_API_KEY:
        return None, "TMDB_API_KEY missing in .env"

    url = f"https://api.themoviedb.org/3{endpoint}"
    params = params or {}
    params["api_key"] = TMDB_API_KEY

    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return None, f"TMDB error: {r.status_code}"
        return r.json(), None
    except Exception as e:
        return None, str(e)
