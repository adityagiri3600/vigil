import datetime
import uuid
import json
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from pywebpush import webpush, WebPushException

from db import (
    SessionLocal,
    User,
    Family,
    Device,
    Alert,
    FamilySettings,
    DeviceSettings,
    PushSubscription,
)
from config import DEFAULT_SETTINGS, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIMS


# ---------- DB SESSION HELPER ----------

@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------- AUTH ----------

def signup_user(email: str, password: str, name: str, family_id: Optional[str]) -> Dict[str, Any]:
    with db_session() as db:
        existing = db.get(User, email)
        if existing:
            raise ValueError("User already exists")

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

        return {
            "email": user.email,
            "name": user.name,
            "family_id": user.family_id,
        }


def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    with db_session() as db:
        user = db.get(User, email)
        if not user or user.password != password:
            return None

        return {
            "email": user.email,
            "name": user.name,
            "family_id": user.family_id,
        }


# ---------- FAMILY ----------

def get_family_members(family_id: str) -> List[Dict[str, Any]]:
    with db_session() as db:
        rows = (
            db.query(User)
            .filter(User.family_id == family_id)
            .order_by(User.email)
            .all()
        )

    return [{"email": u.email, "name": u.name} for u in rows]


# ---------- SETTINGS (FAMILY + DEVICE) ----------

def _settings_dict_from_model(settings_model: Optional[FamilySettings]) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for key, default in DEFAULT_SETTINGS.items():
        if settings_model is not None:
            val = getattr(settings_model, key, None)
            data[key] = val if val is not None else default
        else:
            data[key] = default
    return data


def get_family_settings(family_id: str) -> Dict[str, Any]:
    with db_session() as db:
        settings = db.get(FamilySettings, family_id)
        if not settings:
            settings = FamilySettings(
                family_id=family_id,
                **DEFAULT_SETTINGS,
            )
            db.add(settings)

        result = _settings_dict_from_model(settings)

    return result


def update_family_settings(family_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with db_session() as db:
        settings = db.get(FamilySettings, family_id)
        if not settings:
            settings = FamilySettings(family_id=family_id)
            db.add(settings)

        # Update from payload
        for key in DEFAULT_SETTINGS.keys():
            if key in payload:
                setattr(settings, key, payload[key])

        # Propagate emergency-related fields into per-device settings (if not overridden)
        devices = db.query(Device).filter(Device.family_id == family_id).all()
        for dev in devices:
            dev_settings = db.get(DeviceSettings, dev.id)
            if not dev_settings:
                dev_settings = DeviceSettings(device_id=dev.id)
                db.add(dev_settings)

            for key in ["emergency_number", "auto_call_emergency", "auto_call_delay_seconds"]:
                if key in payload and getattr(dev_settings, key) is None:
                    setattr(dev_settings, key, payload[key])

            # Optionally reflect on the sensor_settings JSON
            sensor = dev.sensor_settings or {}
            for key in DEFAULT_SETTINGS.keys():
                # device override wins, else family, else default
                val = getattr(dev_settings, key, None)
                if val is None:
                    val = getattr(settings, key, None)
                if val is None:
                    val = DEFAULT_SETTINGS[key]
                sensor[key] = val
            dev.sensor_settings = sensor

        result = _settings_dict_from_model(settings)

    return result


def get_device_settings_bundle(family_id: str, device_id: str) -> Optional[Dict[str, Any]]:
    with db_session() as db:
        dev = (
            db.query(Device)
            .filter(Device.id == device_id, Device.family_id == family_id)
            .first()
        )
        if not dev:
            return None

        fam_settings = db.get(FamilySettings, family_id)
        if not fam_settings:
            fam_settings = FamilySettings(family_id=family_id, **DEFAULT_SETTINGS)
            db.add(fam_settings)

        dev_settings = db.get(DeviceSettings, device_id)
        if not dev_settings:
            dev_settings = DeviceSettings(device_id=device_id)
            db.add(dev_settings)

        family_settings_dict = _settings_dict_from_model(fam_settings)

        device_settings_dict: Dict[str, Any] = {}
        for key in DEFAULT_SETTINGS.keys():
            device_settings_dict[key] = getattr(dev_settings, key, None)

        effective = dict(family_settings_dict)
        for key, val in device_settings_dict.items():
            if val is not None:
                effective[key] = val

        device_dict = {
            "id": dev.id,
            "family_id": dev.family_id,
            "name": dev.name,
            "status": dev.status,
            "last_seen": dev.last_seen,
            "room": dev.room,
            "sensor_settings": dev.sensor_settings,
        }

        return {
            "device": device_dict,
            "family_settings": family_settings_dict,
            "device_settings": device_settings_dict,
            "effective_settings": effective,
        }


def update_device_settings(
    family_id: str, device_id: str, payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    with db_session() as db:
        dev = (
            db.query(Device)
            .filter(Device.id == device_id, Device.family_id == family_id)
            .first()
        )
        if not dev:
            return None

        dev_settings = db.get(DeviceSettings, device_id)
        if not dev_settings:
            dev_settings = DeviceSettings(device_id=device_id)
            db.add(dev_settings)

        for key in DEFAULT_SETTINGS.keys():
            if key in payload:
                setattr(dev_settings, key, payload[key])

        fam_settings = db.get(FamilySettings, family_id)
        if not fam_settings:
            fam_settings = FamilySettings(family_id=family_id, **DEFAULT_SETTINGS)
            db.add(fam_settings)

        family_settings_dict = _settings_dict_from_model(fam_settings)
        device_settings_dict: Dict[str, Any] = {}
        for key in DEFAULT_SETTINGS.keys():
            device_settings_dict[key] = getattr(dev_settings, key, None)

        effective = dict(family_settings_dict)
        for key, val in device_settings_dict.items():
            if val is not None:
                effective[key] = val

        # reflect effective on sensor_settings JSON
        dev.sensor_settings = effective

        result = {
            "device_settings": device_settings_dict,
            "effective_settings": effective,
        }

    return result


# ---------- DEVICES CRUD ----------

def list_devices(family_id: str) -> List[Dict[str, Any]]:
    with db_session() as db:
        devices = (
            db.query(Device)
            .filter(Device.family_id == family_id)
            .order_by(Device.id)
            .all()
        )

    return [
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


def create_device(family_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    name = payload.get("name") or "Unnamed device"
    room = payload.get("room") or "Unknown"
    status = payload.get("status") or "online"
    last_seen = payload.get("last_seen") or "just now"

    device_id = payload.get("id") or f"DEV_{uuid.uuid4().hex[:8].upper()}"

    with db_session() as db:
        family = db.get(Family, family_id)
        if not family:
            family = Family(id=family_id)
            db.add(family)

        existing = db.get(Device, device_id)
        if existing:
            raise ValueError("Device with this ID already exists")

        dev = Device(
            id=device_id,
            family_id=family_id,
            name=name,
            status=status,
            last_seen=last_seen,
            room=room,
            sensor_settings={},
        )
        db.add(dev)

        result = {
            "id": dev.id,
            "family_id": dev.family_id,
            "name": dev.name,
            "status": dev.status,
            "last_seen": dev.last_seen,
            "room": dev.room,
            "sensor_settings": dev.sensor_settings,
        }

    return result


def update_device_core(
    family_id: str, device_id: str, payload: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    with db_session() as db:
        dev = (
            db.query(Device)
            .filter(Device.id == device_id, Device.family_id == family_id)
            .first()
        )
        if not dev:
            return None

        for field in ["name", "status", "last_seen", "room"]:
            if field in payload:
                setattr(dev, field, payload[field])

        result = {
            "id": dev.id,
            "family_id": dev.family_id,
            "name": dev.name,
            "status": dev.status,
            "last_seen": dev.last_seen,
            "room": dev.room,
            "sensor_settings": dev.sensor_settings,
        }

    return result


def delete_device(family_id: str, device_id: str) -> bool:
    with db_session() as db:
        dev = (
            db.query(Device)
            .filter(Device.id == device_id, Device.family_id == family_id)
            .first()
        )
        if not dev:
            return False

        # delete device settings
        db.query(DeviceSettings).filter(DeviceSettings.device_id == device_id).delete()
        # delete the device
        db.delete(dev)

    return True


# ---------- ALERTS CRUD + DEMO ALERT ----------

def list_alerts(family_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    with db_session() as db:
        alerts = (
            db.query(Alert)
            .filter(Alert.family_id == family_id)
            .order_by(Alert.time.desc())
            .limit(limit)
            .all()
        )

    return [
        {
            "id": a.id,
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


def create_alert(family_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    with db_session() as db:
        alert = Alert(
            family_id=family_id,
            type=payload.get("type", "custom"),
            severity=payload.get("severity", "medium"),
            room=payload.get("room", "Unknown"),
            message_en=payload.get("message_en", ""),
            message_ko=payload.get("message_ko", ""),
            time=now,
        )
        db.add(alert)

        result = {
            "id": alert.id,
            "family_id": alert.family_id,
            "type": alert.type,
            "severity": alert.severity,
            "room": alert.room,
            "message_en": alert.message_en,
            "message_ko": alert.message_ko,
            "time": alert.time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    return result


def delete_alert(family_id: str, alert_id: int) -> bool:
    with db_session() as db:
        alert = (
            db.query(Alert)
            .filter(Alert.id == alert_id, Alert.family_id == family_id)
            .first()
        )
        if not alert:
            return False

        db.delete(alert)

    return True


def create_demo_alert(family_id: str, device_id: str) -> Optional[Dict[str, Any]]:
    now = datetime.datetime.utcnow()

    with db_session() as db:
        dev = (
            db.query(Device)
            .filter(Device.id == device_id, Device.family_id == family_id)
            .first()
        )
        if not dev:
            return None

        alert = Alert(
            family_id=family_id,
            type="demo",
            severity="medium",
            room=dev.room,
            message_en=f"Demo alert from {dev.name}",
            message_ko=f"테스트 알림: {dev.name}",
            time=now,
        )
        db.add(alert)

        subs = (
            db.query(PushSubscription)
            .filter(PushSubscription.family_id == family_id)
            .all()
        )
        subs_payloads = [s.subscription for s in subs]

    # Send web push outside the session
    payload = {
        "title": "VIGIL Demo Alert",
        "body": f"{dev.name} in {dev.room} sent a demo alert.",
        "url": "/",
    }

    for sub in subs_payloads:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
        except WebPushException as ex:
            print("WebPush failed:", repr(ex))

    return {"status": "sent"}


# ---------- PUSH SUBSCRIPTIONS ----------

def subscribe_push(family_id: str, subscription: Dict[str, Any]) -> None:
    endpoint = subscription.get("endpoint")
    if not endpoint:
        raise ValueError("Missing subscription endpoint")

    with db_session() as db:
        existing = (
            db.query(PushSubscription)
            .filter(PushSubscription.endpoint == endpoint)
            .first()
        )
        if existing:
            existing.family_id = family_id
            existing.subscription = subscription
        else:
            sub = PushSubscription(
                family_id=family_id,
                endpoint=endpoint,
                subscription=subscription,
            )
            db.add(sub)


# ---------- DASHBOARD AGGREGATION ----------

def get_dashboard_data(family_id: str) -> Dict[str, Any]:
    with db_session() as db:
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

    devices_online = sum(1 for d in devices if d.status == "online")
    alerts_last_24h = len(alerts)  # todo: filter by time if needed
    critical_alerts = sum(1 for a in alerts if a.severity == "high")

    if critical_alerts > 0:
        status = "critical"
    elif alerts_last_24h > 0:
        status = "warning"
    else:
        status = "ok"

    summary = {
        "status": status,
        "devices_online": devices_online,
        "alerts_last_24h": alerts_last_24h,
        "critical_alerts": critical_alerts,
    }

    activity_timeline = [
        {"label": "06:00", "motions": 2},
        {"label": "09:00", "motions": 5},
        {"label": "12:00", "motions": 3},
        {"label": "15:00", "motions": 4},
        {"label": "18:00", "motions": 6},
        {"label": "21:00", "motions": 2},
    ]

    room_stats = {
        "Living Room": 12,
        "Kitchen": 4,
        "Bedroom": 8,
        "Bathroom": 2,
    }

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
            "id": a.id,
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

    return {
        "summary": summary,
        "devices": devices_for_ui,
        "alerts": alerts_for_ui,
        "activity": activity,
        "activity_timeline": activity_timeline,
        "room_stats": room_stats,
        "safety_score": safety_score,
        "today_stats": today_stats,
        "yesterday_stats": yesterday_stats,
    }
