from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
import datetime
import os


app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app, resources={r"/api/*": {"origins": "*"}})


JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key")

# -------------------------
# In-memory "data store"
# -------------------------
USERS = {}      # email -> {password, name, family_id}
FAMILIES = {}   # family_id -> [emails]
ALERTS = []     # list of alerts
DEVICES = []    # list of devices

FAMILY_SETTINGS = {}  # family_id -> settings dict
DEVICE_SETTINGS = {}  # device_id -> settings dict

DEFAULT_SETTINGS = {
    "emergency_number": "119",
    "auto_call_emergency": True,
    "auto_call_delay_seconds": 60,
    "notify_family_push": True,
    "notify_family_sms": False,
    "fall_detection_sensitivity": "medium",  # low | medium | high
    "video_streaming_enabled": False,
}

# Seed demo data
def seed_data():
    demo_email = "demo@vigil.com"
    family_id = "FAMILY_DEMO"

    USERS[demo_email] = {
        "password": "demo123",  # plain text for demo only
        "name": "Demo Caregiver",
        "family_id": family_id,
    }
    FAMILIES[family_id] = [demo_email]

    DEVICES.extend([
        {
            "id": "DEV1",
            "family_id": family_id,
            "name": "거실 센서 / Living Room Sensor",
            "status": "online",
            "last_seen": "5 min ago",
            "room": "Living Room",
        },
        {
            "id": "DEV2",
            "family_id": family_id,
            "name": "침실 센서 / Bedroom Sensor",
            "status": "online",
            "last_seen": "12 min ago",
            "room": "Bedroom",
        },
    ])

    ALERTS.extend([
        {
            "family_id": family_id,
            "type": "fall",
            "severity": "high",
            "room": "거실 / Living Room",
            "message_en": "Possible fall detected",
            "message_ko": "낙상 가능성이 감지되었습니다.",
            "time": "2025-11-30 14:05",
        },
        {
            "family_id": family_id,
            "type": "inactivity",
            "severity": "medium",
            "room": "침실 / Bedroom",
            "message_en": "No movement detected for 3 hours",
            "message_ko": "3시간 동안 움직임이 없습니다.",
            "time": "2025-11-30 10:30",
        },
    ])

    # Family-wide default settings
    FAMILY_SETTINGS[family_id] = DEFAULT_SETTINGS.copy()

    # Per-device settings initially follow key emergency-related settings
    for dev in DEVICES:
        DEVICE_SETTINGS[dev["id"]] = {
            "emergency_number": DEFAULT_SETTINGS["emergency_number"],
            "auto_call_emergency": DEFAULT_SETTINGS["auto_call_emergency"],
            "auto_call_delay_seconds": DEFAULT_SETTINGS["auto_call_delay_seconds"],
            "fall_detection_sensitivity": DEFAULT_SETTINGS["fall_detection_sensitivity"],
        }


seed_data()

# -------------------------
# Helpers
# -------------------------
def create_token(email, family_id):
    payload = {
        "sub": email,
        "family_id": family_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    # pyjwt may return bytes in older versions
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def decode_token(token):
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])

def token_required(fn):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except Exception:
            return jsonify({"error": "Invalid or expired token"}), 401

        request.user_email = payload["sub"]
        request.family_id = payload["family_id"]
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

# -------------------------
# Routes - Auth
# -------------------------
@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    name = data.get("name", "")
    family_id = data.get("family_id")  # optional

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    if email in USERS:
        return jsonify({"error": "User already exists"}), 400

    # If family_id not provided, create a new family
    if not family_id:
        family_id = f"FAMILY_{email.split('@')[0].upper()}"

    USERS[email] = {
        "password": password,
        "name": name,
        "family_id": family_id,
    }

    if family_id not in FAMILIES:
        FAMILIES[family_id] = []
    FAMILIES[family_id].append(email)

    token = create_token(email, family_id)
    return jsonify({
        "token": token,
        "user": {
            "email": email,
            "name": name,
            "family_id": family_id,
        }
    })

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user = USERS.get(email)
    if not user or user["password"] != password:
        return jsonify({"error": "Invalid credentials"}), 400

    token = create_token(email, user["family_id"])
    return jsonify({
        "token": token,
        "user": {
            "email": email,
            "name": user["name"],
            "family_id": user["family_id"],
        }
    })

# -------------------------
# Routes - Dashboard
# -------------------------
@app.route("/api/dashboard", methods=["GET"])
@token_required
def dashboard():
    family_id = request.family_id

    family_devices = [d for d in DEVICES if d["family_id"] == family_id]
    family_alerts = [a for a in ALERTS if a["family_id"] == family_id]

    # ---- Summary cards (top bar) ----
    devices_online = sum(1 for d in family_devices if d["status"] == "online")
    alerts_last_24h = len(family_alerts)  # dummy: treat all as last 24h
    critical_alerts = sum(1 for a in family_alerts if a["severity"] == "high")

    if critical_alerts > 0:
        status = "critical"
    elif alerts_last_24h > 0:
        status = "warning"
    else:
        status = "ok"

    summary = {
        "status": status,  # ok | warning | critical
        "devices_online": devices_online,
        "alerts_last_24h": alerts_last_24h,
        "critical_alerts": critical_alerts,
    }

    # ---- Activity timeline (dummy) ----
    activity_timeline = [
        {"label": "06:00", "motions": 2},
        {"label": "09:00", "motions": 5},
        {"label": "12:00", "motions": 3},
        {"label": "15:00", "motions": 4},
        {"label": "18:00", "motions": 6},
        {"label": "21:00", "motions": 2},
    ]

    # ---- Room stats / heatmap grid ----
    room_stats = {
        "Living Room": 12,
        "Kitchen": 4,
        "Bedroom": 8,
        "Bathroom": 2,
    }

    # ---- Safety score ----
    base = 100
    base -= critical_alerts * 20
    base -= max(0, alerts_last_24h - critical_alerts) * 5
    if devices_online < len(family_devices):
        base -= 10
    score = max(0, min(100, base))

    safety_score = {
        "score": score,
        "label_en": "Good" if score >= 80 else ("Fair" if score >= 50 else "Risky"),
        "label_ko": "양호" if score >= 80 else ("보통" if score >= 50 else "위험"),
    }

    today_stats = {
        "alerts": alerts_last_24h,
        "motions": 40,
    }
    yesterday_stats = {
        "alerts": max(0, alerts_last_24h - 1),
        "motions": 35,
    }

    activity = {
        "today_active": True,
        "last_motion": "5 min ago",
        "rooms_visited": list(room_stats.keys()),
    }

    alerts_for_ui = family_alerts[:20]

    return jsonify({
        "summary": summary,
        "devices": family_devices,
        "alerts": alerts_for_ui,
        "activity": activity,
        "activity_timeline": activity_timeline,
        "room_stats": room_stats,
        "safety_score": safety_score,
        "today_stats": today_stats,
        "yesterday_stats": yesterday_stats,
    })


# -------------------------
# Routes - Family
# -------------------------
@app.route("/api/family/members", methods=["GET"])
@token_required
def family_members():
    family_id = request.family_id
    member_emails = FAMILIES.get(family_id, [])
    members = []
    for email in member_emails:
        u = USERS.get(email)
        if not u:
            continue
        members.append({
            "email": email,
            "name": u["name"],
        })
    return jsonify(members)

# -------------------------
# Health
# -------------------------
@app.route("/api/health")
def health():
    return {"status": "ok"}


# -------------------------
# Settings
# -------------------------
@app.route("/api/settings", methods=["GET", "POST"])
@token_required
def settings():
    family_id = request.family_id

    # GET: return current settings (or defaults)
    if request.method == "GET":
        settings = FAMILY_SETTINGS.get(family_id) or DEFAULT_SETTINGS.copy()
        FAMILY_SETTINGS[family_id] = settings
        return jsonify(settings)

    # POST: update settings
    data = request.json or {}
    settings = FAMILY_SETTINGS.get(family_id) or DEFAULT_SETTINGS.copy()

    for key in DEFAULT_SETTINGS.keys():
        if key in data:
            settings[key] = data[key]

    FAMILY_SETTINGS[family_id] = settings

    # Simulate "pushing" relevant settings to all sensors for that family
    for dev in DEVICES:
        if dev["family_id"] == family_id:
            dev_id = dev["id"]
            dev_settings = DEVICE_SETTINGS.get(dev_id) or {}
            # sync a subset of settings to each sensor if not overridden
            for key in ["emergency_number", "auto_call_emergency", "auto_call_delay_seconds"]:
                if key in settings and key not in dev_settings:
                    dev_settings[key] = settings[key]
            DEVICE_SETTINGS[dev_id] = dev_settings
            dev["sensor_settings"] = dev_settings  # purely informational

    return jsonify(settings)



@app.route("/api/devices/<device_id>", methods=["GET"])
@token_required
def get_device(device_id):
    family_id = request.family_id
    dev = next(
        (d for d in DEVICES if d["id"] == device_id and d["family_id"] == family_id),
        None,
    )
    if not dev:
        return jsonify({"error": "Device not found"}), 404

    family_settings = FAMILY_SETTINGS.get(family_id) or DEFAULT_SETTINGS.copy()
    device_settings = DEVICE_SETTINGS.get(device_id) or {}
    effective = family_settings.copy()
    effective.update(device_settings)  # device overrides

    return jsonify({
        "device": dev,
        "family_settings": family_settings,
        "device_settings": device_settings,
        "effective_settings": effective,
    })


@app.route("/api/devices/<device_id>/settings", methods=["POST"])
@token_required
def update_device_settings(device_id):
    family_id = request.family_id
    dev = next(
        (d for d in DEVICES if d["id"] == device_id and d["family_id"] == family_id),
        None,
    )
    if not dev:
        return jsonify({"error": "Device not found"}), 404

    data = request.json or {}
    device_settings = DEVICE_SETTINGS.get(device_id) or {}

    for key in DEFAULT_SETTINGS.keys():
        if key in data:
            device_settings[key] = data[key]

    DEVICE_SETTINGS[device_id] = device_settings
    # simulate applying settings on the sensor
    dev["sensor_settings"] = device_settings

    family_settings = FAMILY_SETTINGS.get(family_id) or DEFAULT_SETTINGS.copy()
    effective = family_settings.copy()
    effective.update(device_settings)

    return jsonify({
        "device_settings": device_settings,
        "effective_settings": effective,
    })



if __name__ == "__main__":
    app.run(port=5000, debug=True)
