import os

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key")

DEFAULT_SETTINGS = {
    "emergency_number": "119",
    "auto_call_emergency": True,
    "auto_call_delay_seconds": 60,
    "notify_family_push": True,
    "notify_family_sms": False,
    "fall_detection_sensitivity": "medium", 
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
    "sub": os.environ.get("VAPID_SUBJECT", "mailto:tootsydeshmukh@gmail.com"),
}
