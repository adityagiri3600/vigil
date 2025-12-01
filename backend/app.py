from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import jwt
import datetime
import os

import json
from pywebpush import webpush, WebPushException

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker



app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app, resources={r"/api/*": {"origins": "*"}})


JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key")


DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

class Family(Base):
    __tablename__ = "families"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    email = Column(String, primary_key=True)
    password = Column(String, nullable=False)
    name = Column(String)
    family_id = Column(String, ForeignKey("families.id"), nullable=False)


class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True)
    family_id = Column(String, ForeignKey("families.id"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    last_seen = Column(String)
    room = Column(String)
    sensor_settings = Column(JSON)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(String, nullable=False)
    type = Column(String)
    severity = Column(String)
    room = Column(String)
    message_en = Column(Text)
    message_ko = Column(Text)
    time = Column(DateTime, default=datetime.datetime.utcnow)


class FamilySettings(Base):
    __tablename__ = "family_settings"

    family_id = Column(String, primary_key=True)
    emergency_number = Column(String)
    auto_call_emergency = Column(Boolean)
    auto_call_delay_seconds = Column(Integer)
    notify_family_push = Column(Boolean)
    notify_family_sms = Column(Boolean)
    fall_detection_sensitivity = Column(String)
    video_streaming_enabled = Column(Boolean)


class DeviceSettings(Base):
    __tablename__ = "device_settings"

    device_id = Column(String, primary_key=True)
    emergency_number = Column(String)
    auto_call_emergency = Column(Boolean)
    auto_call_delay_seconds = Column(Integer)
    fall_detection_sensitivity = Column(String)


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    family_id = Column(String, nullable=False)
    endpoint = Column(Text, unique=True, nullable=False)
    subscription = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)

# In-memory "data store" (still used for devices/alerts/settings for now)
ALERTS = []      # list of alerts
DEVICES = []     # list of devices

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

VAPID_PUBLIC_KEY = os.environ.get(
    "VAPID_PUBLIC_KEY",
    "BNkcdEiq6zQ4uqiGLwuFXzgNO4-DCwnA5VrtSN2IGHeKRZryD09BXpYhPGuj-8rnVXhKI3NVldJhZEI1nk25uiM",
)
VAPID_PRIVATE_KEY = os.environ.get(
    "VAPID_PRIVATE_KEY",
    "KOIrBACUp3tAjARjQ9sxRYs7W89cF5s41H6n6_PzSjY",
)
VAPID_CLAIMS = {
    "sub": "mailto:tootsydeshmukh@gmail.com",  # NOTE the mailto:
}

PUSH_SUBSCRIPTIONS = {}  # family_id -> [subscription dicts]


def seed_data():
    demo_email = "demo@vigil.com"
    family_id = "FAMILY_DEMO"

    db = SessionLocal()
    try:
        # 1) Ensure FAMILY_DEMO exists in families FIRST
        family = db.get(Family, family_id)
        if not family:
            family = Family(id=family_id)
            db.add(family)
            db.commit()  # <-- commit so parent row definitely exists

        # 2) Ensure demo user exists
        user = db.get(User, demo_email)
        if not user:
            user = User(
                email=demo_email,
                password="demo123",  # plain text for demo only
                name="Demo Caregiver",
                family_id=family_id,
            )
            db.add(user)

        # 3) Seed devices (they now see a valid family_id)
        existing_dev1 = db.get(Device, "DEV1")
        if not existing_dev1:
            db.add(
                Device(
                    id="DEV1",
                    family_id=family_id,
                    name="거실 센서 / Living Room Sensor",
                    status="online",
                    last_seen="5 min ago",
                    room="Living Room",
                )
            )
        existing_dev2 = db.get(Device, "DEV2")
        if not existing_dev2:
            db.add(
                Device(
                    id="DEV2",
                    family_id=family_id,
                    name="침실 센서 / Bedroom Sensor",
                    status="online",
                    last_seen="12 min ago",
                    room="Bedroom",
                )
            )

        # 4) Alerts – seed only if none exist
        any_alert = db.query(Alert).first()
        if not any_alert:
            db.add_all(
                [
                    Alert(
                        family_id=family_id,
                        type="fall",
                        severity="high",
                        room="거실 / Living Room",
                        message_en="Possible fall detected",
                        message_ko="낙상 가능성이 감지되었습니다.",
                        time=datetime.datetime(2025, 11, 30, 14, 5),
                    ),
                    Alert(
                        family_id=family_id,
                        type="inactivity",
                        severity="medium",
                        room="침실 / Bedroom",
                        message_en="No movement detected for 3 hours",
                        message_ko="3시간 동안 움직임이 없습니다.",
                        time=datetime.datetime(2025, 11, 30, 10, 30),
                    ),
                ]
            )

        # 5) Family-wide default settings
        fam_settings = db.get(FamilySettings, family_id)
        if not fam_settings:
            fam_settings = FamilySettings(
                family_id=family_id,
                emergency_number=DEFAULT_SETTINGS["emergency_number"],
                auto_call_emergency=DEFAULT_SETTINGS["auto_call_emergency"],
                auto_call_delay_seconds=DEFAULT_SETTINGS["auto_call_delay_seconds"],
                notify_family_push=DEFAULT_SETTINGS["notify_family_push"],
                notify_family_sms=DEFAULT_SETTINGS["notify_family_sms"],
                fall_detection_sensitivity=DEFAULT_SETTINGS[
                    "fall_detection_sensitivity"
                ],
                video_streaming_enabled=DEFAULT_SETTINGS["video_streaming_enabled"],
            )
            db.add(fam_settings)

        # Final commit for user/devices/alerts/settings
        db.commit()
    finally:
        db.close()



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



@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_file(path):
    return send_from_directory(app.static_folder, path)


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

    db = SessionLocal()
    try:
        existing = db.get(User, email)
        if existing:
            return jsonify({"error": "User already exists"}), 400

        if not family_id:
            family_id = f"FAMILY_{email.split('@')[0].upper()}"

        family = db.get(Family, family_id)
        if not family:
            family = Family(id=family_id)
            db.add(family)

        user = User(
            email=email,
            password=password,
            name=name,
            family_id=family_id,
        )
        db.add(user)
        db.commit()

        token = create_token(email, family_id)
        return jsonify(
            {
                "token": token,
                "user": {
                    "email": email,
                    "name": name,
                    "family_id": family_id,
                },
            }
        )
    finally:
        db.close()


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    db = SessionLocal()
    try:
        user = db.get(User, email)
    finally:
        db.close()

    if not user or user.password != password:
        return jsonify({"error": "Invalid credentials"}), 400

    token = create_token(user.email, user.family_id)
    return jsonify(
        {
            "token": token,
            "user": {
                "email": user.email,
                "name": user.name,
                "family_id": user.family_id,
            },
        }
    )


# -------------------------
# Routes - Dashboard
# -------------------------
@app.route("/api/dashboard", methods=["GET"])
@token_required
def dashboard():
    family_id = request.family_id

    db = SessionLocal()
    try:
        devices = (
            db.query(Device)
            .filter(Device.family_id == family_id)
            .all()
        )

        alerts = (
            db.query(Alert)
            .filter(Alert.family_id == family_id)
            .order_by(Alert.time.desc())
            .limit(50)
            .all()
        )
    finally:
        db.close()

    # ---- Summary cards (top bar) ----
    devices_online = sum(1 for d in devices if d.status == "online")
    alerts_last_24h = len(alerts)  # still dummy: treat all as last 24h
    critical_alerts = sum(1 for a in alerts if a.severity == "high")

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
    if devices_online < len(devices):
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

    devices_for_ui = [
        {
            "id": d.id,
            "family_id": d.family_id,
            "name": d.name,
            "status": d.status,
            "last_seen": d.last_seen,
            "room": d.room,
            "sensor_settings": d.sensor_settings,
        }
        for d in devices
    ]

    alerts_for_ui = [
        {
            "family_id": a.family_id,
            "type": a.type,
            "severity": a.severity,
            "room": a.room,
            "message_en": a.message_en,
            "message_ko": a.message_ko,
            "time": a.time.strftime("%Y-%m-%d %H:%M:%S") if a.time else None,
        }
        for a in alerts
    ]

    return jsonify({
        "summary": summary,
        "devices": devices_for_ui,
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

    db = SessionLocal()
    try:
        rows = (
            db.query(User)
            .filter(User.family_id == family_id)
            .order_by(User.email)
            .all()
        )
    finally:
        db.close()

    members = [{"email": u.email, "name": u.name} for u in rows]
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

@app.route("/api/devices/<device_id>/demo-alert", methods=["POST"])
@token_required
def demo_alert(device_id):
    family_id = request.family_id
    dev = next(
        (d for d in DEVICES if d["id"] == device_id and d["family_id"] == family_id),
        None,
    )
    if not dev:
        return jsonify({"error": "Device not found"}), 404

    # Create a dummy alert in memory
    alert = {
        "family_id": family_id,
        "type": "demo",
        "severity": "medium",
        "room": dev["room"],
        "message_en": f"Demo alert from {dev['name']}",
        "message_ko": f"테스트 알림: {dev['name']}",
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    ALERTS.insert(0, alert)

    # Build push payload
    payload = {
        "title": "VIGIL Demo Alert",
        "body": f"{dev['name']} in {dev['room']} sent a demo alert.",
        "url": "/",  # page to open on click
    }

    subs = PUSH_SUBSCRIPTIONS.get(family_id, [])
    for sub in list(subs):
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
        except WebPushException as ex:
            print("WebPush failed:", repr(ex))
            # You could remove dead subscriptions here if desired

    return jsonify({"status": "sent"})

    
    
    

@app.route("/api/push/subscribe", methods=["POST"])
@token_required
def push_subscribe():
    family_id = request.family_id
    subscription = request.json

    if not subscription or "endpoint" not in subscription:
        return jsonify({"error": "Missing subscription"}), 400

    subs = PUSH_SUBSCRIPTIONS.get(family_id, [])
    endpoints = [s.get("endpoint") for s in subs]

    # simple dedupe by endpoint
    if subscription["endpoint"] not in endpoints:
        subs.append(subscription)

    PUSH_SUBSCRIPTIONS[family_id] = subs
    return jsonify({"status": "ok"})



init_db()
seed_data()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
