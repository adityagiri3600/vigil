import datetime
import uuid
import json
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

from pywebpush import webpush, WebPushException

from .db import (
    Motion,
    SessionLocal,
    User,
    Family,
    Device,
    Alert,
    FamilySettings,
    DeviceSettings,
    PushSubscription,
)
from .config import DEFAULT_SETTINGS, VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_CLAIMS


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

def register_device_for_family(
    family_id: str,
    token: str,
    name: str,
    room: str,
) -> Dict[str, Any]:
    """
    Create a new device bound to a family, given a device auth token.

    Called from the app (user is logged in) after scanning the device's QR.
    """
    # derive a stable-ish id from token (good enough for prototype)
    device_id = f"DEV_{token[-8:].upper()}"

    with db_session() as db:
        # make sure family exists
        family = db.get(Family, family_id)
        if not family:
            family = Family(id=family_id)
            db.add(family)

        # make sure token isn't already used
        existing_devices = db.query(Device).all()
        for d in existing_devices:
            settings = d.sensor_settings or {}
            if settings.get("auth_token") == token:
                raise ValueError("Device with this token is already registered.")

        # simple collision check on id
        if db.get(Device, device_id):
            raise ValueError("Device with this ID already exists.")

        dev = Device(
            id=device_id,
            family_id=family_id,
            name=name or "New Sensor",
            status="online",
            last_seen="never",
            room=room or "Unknown",
            sensor_settings={"auth_token": token},
        )
        db.add(dev)

        # thanks to expire_on_commit=False you can access attributes after context
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


def handle_device_event(token: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process an event sent by a device identified by its auth token.

    Returns a small dict for the HTTP response, or None if device not found.
    """
    event_type = payload.get("type") or "unknown"
    severity = payload.get("severity") or "medium"
    room = payload.get("room") or "Unknown"

    ts_str = payload.get("timestamp")
    if ts_str:
        try:
            # allow "2025-12-01T10:23:00Z" or with offset
            timestamp = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            timestamp = datetime.datetime.utcnow()
    else:
        timestamp = datetime.datetime.utcnow()

    with db_session() as db:
        # find device by auth_token stored in sensor_settings
        devices = db.query(Device).all()
        dev: Optional[Device] = None
        for d in devices:
            settings = d.sensor_settings or {}
            if settings.get("auth_token") == token:
                dev = d
                break

        if not dev:
            return None

        ts_utc = timestamp.astimezone(datetime.timezone.utc)
        dev.last_seen = ts_utc.isoformat().replace("+00:00", "Z")
        dev.status = "online"

        # save these so we can use them outside the session
        dev_id = dev.id
        dev_family_id = dev.family_id
        dev_name = dev.name
        dev_room = room or (dev.room or "Unknown")

        if event_type == "heartbeat":
            # heartbeat: nothing more to do, no notification
            return {"status": "ok", "device_id": dev_id}

        # Otherwise: create alert
        alert = Alert(
            family_id=dev_family_id,
            type=event_type,
            severity=severity,
            room=dev_room,
            message_en=payload.get(
                "message_en",
                f"{event_type.capitalize()} event from device {dev_id}",
            ),
            message_ko=payload.get("message_ko", None),
            time=timestamp,
        )
        db.add(alert)

    # --- send push notification outside DB session ---
    title = "VIGIL Alert"
    body = payload.get(
        "notification_body",
        f"{event_type.capitalize()} detected by {dev_name} in {dev_room}.",
    )
    push_result = _send_push_to_family(dev_family_id, title, body, url="/")

    return {
        "status": "alert_created",
        "device_id": dev_id,
        "event_type": event_type,
        **push_result,
    }



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

def _send_push_to_family(
    family_id: str,
    title: str,
    body: str,
    url: str = "/",
) -> Dict[str, int]:
    """Send a web push notification to all push subscriptions of a family."""
    # First fetch subscriptions from DB
    with db_session() as db:
        subs = (
            db.query(PushSubscription)
            .filter(PushSubscription.family_id == family_id)
            .all()
        )
        subs_payloads = [s.subscription for s in subs]

    payload = {
        "title": title,
        "body": body,
        "url": url,
    }

    ok_count = 0
    fail_count = 0

    for sub in subs_payloads:
        try:
            webpush(
                subscription_info=sub,
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS,
            )
            ok_count += 1
        except WebPushException as ex:
            print("WebPush failed:", repr(ex))
            fail_count += 1

    return {"sent_to": ok_count, "failed": fail_count}


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

    alert_type = payload.get("type", "custom")
    severity = payload.get("severity", "medium")
    room = payload.get("room", "Unknown")
    msg_en = payload.get("message_en", "")
    msg_ko = payload.get("message_ko", "")

    with db_session() as db:
        alert = Alert(
            family_id=family_id,
            type=alert_type,
            severity=severity,
            room=room,
            message_en=msg_en,
            message_ko=msg_ko,
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

    # --- push notification for manual alert ---
    title = "VIGIL Alert"
    # fallback message if none provided
    body = msg_en or f"{alert_type.capitalize()} alert in {room}."
    _send_push_to_family(family_id, title, body, url="/")

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
    """Create a demo alert for a device and send web push to all family subscriptions."""
    now = datetime.datetime.utcnow()

    with db_session() as db:
        dev = (
            db.query(Device)
            .filter(Device.id == device_id, Device.family_id == family_id)
            .first()
        )
        if not dev:
            return None

        dev_name = dev.name
        dev_room = dev.room or "Unknown"

        alert = Alert(
            family_id=family_id,
            type="demo",
            severity="medium",
            room=dev_room,
            message_en=f"Demo alert from {dev_name}",
            message_ko=f"테스트 알림: {dev_name}",
            time=now,
        )
        db.add(alert)

    # send push outside the session
    push_result = _send_push_to_family(
        family_id,
        "VIGIL Demo Alert",
        f"{dev_name} in {dev_room} sent a demo alert.",
        url="/",
    )

    return {
        "status": "sent",
        "device_id": device_id,
        **push_result,
    }



# ---------- MOTIONS ----------

def log_motion(device_id: str, ts: Optional[datetime.datetime] = None) -> None:
    """Insert a motion event for a device."""
    if ts is None:
        ts = datetime.datetime.now(datetime.timezone.utc)
    with db_session() as db:
        db.add(Motion(device_id=device_id, ts=ts))
        db.commit()


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
    ONLINE_GRACE_SECONDS = 60

    def compute_device_status(
        last_seen: Optional[str], stored_status: Optional[str]
    ) -> str:
        """Return 'online' or 'offline' from last_seen; treat parse failures as offline."""
        s = (last_seen or "").strip()
        if not s or s == "never":
            return "offline"
        try:
            if s.endswith("Z"):
                # 'YYYY-mm-ddTHH:MM:SS(.fff)Z'
                dt = datetime.datetime.fromisoformat(s[:-1]).replace(
                    tzinfo=datetime.timezone.utc
                )
            else:
                # 'YYYY-mm-ddTHH:MM:SS(.fff)+HH:MM' or naive
                dt = datetime.datetime.fromisoformat(s)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            delta = now_utc - dt.astimezone(datetime.timezone.utc)
            return "online" if delta.total_seconds() <= ONLINE_GRACE_SECONDS else "offline"
        except Exception:
            # malformed strings → offline
            return "offline"

    def humanize_last_motion(last_ts: Optional[datetime.datetime]) -> str:
        if last_ts is None:
            return "No motion yet"
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=datetime.timezone.utc)
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        delta = now_utc - last_ts
        secs = int(delta.total_seconds())
        if secs < 60:
            return "just now"
        if secs < 3600:
            return f"{secs // 60} min ago"
        if secs < 86400:
            return f"{secs // 3600} hr ago"
        return f"{secs // 86400} d ago"

    now_utc_naive = datetime.datetime.utcnow()
    now_utc_aware = datetime.datetime.now(datetime.timezone.utc)

    with db_session() as db:
        # ---------- Devices ----------
        device_rows = (
            db.query(Device)
            .filter(Device.family_id == family_id)
            .all()
        )

        effective_devices: List[Dict[str, Any]] = []
        devices_online = 0

        for d in device_rows:
            status = compute_device_status(d.last_seen, d.status)
            if status == "online":
                devices_online += 1
            effective_devices.append(
                {
                    "id": d.id,
                    "family_id": d.family_id,
                    "name": d.name,
                    "status": status,  # computed
                    "last_seen": d.last_seen,
                    "room": d.room,
                    "sensor_settings": d.sensor_settings,
                }
            )

        # ---------- Alerts ----------
        alert_rows = (
            db.query(Alert)
            .filter(Alert.family_id == family_id)
            .order_by(Alert.time.desc())
            .limit(50)
            .all()
        )

        alerts_for_ui: List[Dict[str, Any]] = []
        critical_alerts = 0
        threshold_24h_alerts = now_utc_naive - datetime.timedelta(hours=24)
        alerts_last_24h = 0

        for a in alert_rows:
            alerts_for_ui.append(
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
            )
            if a.severity == "high":
                critical_alerts += 1
            if a.time is not None and a.time >= threshold_24h_alerts:
                alerts_last_24h += 1

        # ---------- Motions (for activity / rooms / today/yesterday) ----------
        base_motion_q = (
            db.query(Motion, Device)
            .join(Device, Motion.device_id == Device.id)
            .filter(Device.family_id == family_id)
        )

        # Motions in last 24h for timeline + room usage + rooms_visited
        threshold_24h_motions = now_utc_aware - datetime.timedelta(hours=24)
        motions_last_24 = (
            base_motion_q
            .filter(Motion.ts >= threshold_24h_motions)
            .all()
        )

        hour_counts: Dict[str, int] = {}
        room_counts: Dict[str, int] = {}
        rooms_visited_set = set()

        for motion, device in motions_last_24:
            ts = motion.ts
            if ts is None:
                continue
            if ts.tzinfo is None:
                ts_utc = ts.replace(tzinfo=datetime.timezone.utc)
            else:
                ts_utc = ts.astimezone(datetime.timezone.utc)

            # bucket by hour label "HH:00"
            label = ts_utc.strftime("%H:00")
            hour_counts[label] = hour_counts.get(label, 0) + 1

            room_name = device.room or "Unknown"
            room_counts[room_name] = room_counts.get(room_name, 0) + 1
            rooms_visited_set.add(room_name)

        activity_timeline = [
            {"label": label, "motions": motions}
            for label, motions in sorted(hour_counts.items())
        ]
        room_stats = room_counts

        # Today vs yesterday (motions)
        today_start = now_utc_aware.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        tomorrow_start = today_start + datetime.timedelta(days=1)
        yesterday_start = today_start - datetime.timedelta(days=1)

        motions_today_count = (
            base_motion_q
            .filter(Motion.ts >= today_start, Motion.ts < tomorrow_start)
            .count()
        )
        motions_yesterday_count = (
            base_motion_q
            .filter(Motion.ts >= yesterday_start, Motion.ts < today_start)
            .count()
        )

        # Last motion timestamp (for "5 min ago" style text)
        last_motion_row = (
            base_motion_q
            .order_by(Motion.ts.desc())
            .first()
        )
        if last_motion_row is not None:
            last_motion_ts = last_motion_row[0].ts
        else:
            last_motion_ts = None

    # ---------- Summary / safety / stats assembled outside the session ----------

    if critical_alerts > 0:
        overall_status = "critical"
    elif alerts_last_24h > 0:
        overall_status = "warning"
    else:
        overall_status = "ok"

    summary = {
        "status": overall_status,
        "devices_online": devices_online,
        "alerts_last_24h": alerts_last_24h,
        "critical_alerts": critical_alerts,
    }

    base_score = 100
    base_score -= critical_alerts * 20
    base_score -= max(0, alerts_last_24h - critical_alerts) * 5
    if devices_online < len(effective_devices):
        base_score -= 10
    score = max(0, min(100, base_score))

    safety_score = {
        "score": score,
        "label_en": "Good" if score >= 80 else ("Fair" if score >= 50 else "Risky"),
        "label_ko": "양호" if score >= 80 else ("보통" if score >= 50 else "위험"),
    }

    today_stats = {
        "alerts": alerts_last_24h,  # still approximate; can refine later
        "motions": motions_today_count,
    }
    yesterday_stats = {
        "alerts": max(0, alerts_last_24h - 1),  # placeholder as before
        "motions": motions_yesterday_count,
    }

    activity = {
        "today_active": motions_today_count > 0,
        "last_motion": humanize_last_motion(last_motion_ts),
        "rooms_visited": sorted(rooms_visited_set),
    }

    return {
        "summary": summary,
        "devices": effective_devices,
        "alerts": alerts_for_ui,
        "activity": activity,
        "activity_timeline": activity_timeline,
        "room_stats": room_stats,
        "safety_score": safety_score,
        "today_stats": today_stats,
        "yesterday_stats": yesterday_stats,
    }
