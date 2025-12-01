import os
import datetime

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

from .config import DEFAULT_SETTINGS

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

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
Base = declarative_base()


# ---------- MODELS ----------

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


# ---------- INIT / SEED ----------

def init_db():
    Base.metadata.create_all(bind=engine)


def seed_data():
    """Seed a demo family, user, devices, alerts, and family settings."""
    demo_email = "demo@vigil.com"
    family_id = "FAMILY_DEMO"

    db = SessionLocal()
    try:
        # 1) Ensure FAMILY_DEMO exists
        family = db.get(Family, family_id)
        if not family:
            family = Family(id=family_id)
            db.add(family)
            db.commit()  # commit so FK references work

        # 2) Demo user
        user = db.get(User, demo_email)
        if not user:
            user = User(
                email=demo_email,
                password="demo123",  # plain text for demo only
                name="Demo Caregiver",
                family_id=family_id,
            )
            db.add(user)

        # 3) Devices
        dev1 = db.get(Device, "DEV1")
        if not dev1:
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

        dev2 = db.get(Device, "DEV2")
        if not dev2:
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

        # 4) Alerts (only if table empty)
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

        # 5) Family default settings
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

        db.commit()
    finally:
        db.close()
