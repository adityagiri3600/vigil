import os
import datetime

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Boolean,
    Integer,
    DateTime,
    func,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import DEFAULT_SETTINGS
from dotenv import load_dotenv
load_dotenv()

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

class Motion(Base):
    __tablename__ = "motions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey("devices.id"), nullable=False)
    # TIMESTAMPTZ in Postgres -> timezone-aware DateTime here
    ts = Column(DateTime(timezone=True), nullable=False, server_default=func.now())