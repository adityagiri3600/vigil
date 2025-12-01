from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import jwt
import datetime

from .config import JWT_SECRET
from .db import init_db, seed_data
from .services import (
    signup_user,
    login_user,
    get_dashboard_data,
    get_family_members,
    get_family_settings,
    update_family_settings,
    list_devices,
    create_device,
    get_device_settings_bundle,
    update_device_settings,
    update_device_core,
    delete_device,
    list_alerts,
    create_alert,
    delete_alert,
    create_demo_alert,
    subscribe_push,
)


app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ---------- JWT HELPERS ----------

def create_token(email, family_id):
    payload = {
        "sub": email,
        "family_id": family_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
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


# ---------- STATIC (FRONTEND) ----------

@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_file(path):
    return send_from_directory(app.static_folder, path)


# ---------- AUTH CONTROLLERS ----------

@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")
    name = data.get("name", "")
    family_id = data.get("family_id")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    try:
        user = signup_user(email, password, name, family_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    token = create_token(user["email"], user["family_id"])
    return jsonify({"token": token, "user": user})


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user = login_user(email, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 400

    token = create_token(user["email"], user["family_id"])
    return jsonify({"token": token, "user": user})


# ---------- DASHBOARD ----------

@app.route("/api/dashboard", methods=["GET"])
@token_required
def dashboard():
    family_id = request.family_id
    data = get_dashboard_data(family_id)
    return jsonify(data)


# ---------- FAMILY ----------

@app.route("/api/family/members", methods=["GET"])
@token_required
def family_members():
    family_id = request.family_id
    members = get_family_members(family_id)
    return jsonify(members)


# ---------- SETTINGS ----------

@app.route("/api/settings", methods=["GET", "POST"])
@token_required
def settings():
    family_id = request.family_id

    if request.method == "GET":
        settings_data = get_family_settings(family_id)
        return jsonify(settings_data)

    payload = request.json or {}
    settings_data = update_family_settings(family_id, payload)
    return jsonify(settings_data)


# ---------- DEVICES CRUD + SETTINGS ----------

@app.route("/api/devices", methods=["GET", "POST"])
@token_required
def devices_collection():
    family_id = request.family_id

    if request.method == "GET":
        devices = list_devices(family_id)
        return jsonify(devices)

    payload = request.json or {}
    try:
        device = create_device(family_id, payload)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(device), 201


@app.route("/api/devices/<device_id>", methods=["GET", "PUT", "DELETE"])
@token_required
def device_detail(device_id):
    family_id = request.family_id

    if request.method == "GET":
        bundle = get_device_settings_bundle(family_id, device_id)
        if not bundle:
            return jsonify({"error": "Device not found"}), 404
        return jsonify(bundle)

    if request.method == "PUT":
        payload = request.json or {}
        updated = update_device_core(family_id, device_id, payload)
        if not updated:
            return jsonify({"error": "Device not found"}), 404
        return jsonify(updated)

    # DELETE
    ok = delete_device(family_id, device_id)
    if not ok:
        return jsonify({"error": "Device not found"}), 404
    return jsonify({"status": "deleted"})


@app.route("/api/devices/<device_id>/settings", methods=["POST"])
@token_required
def device_settings(device_id):
    family_id = request.family_id
    payload = request.json or {}

    result = update_device_settings(family_id, device_id, payload)
    if not result:
        return jsonify({"error": "Device not found"}), 404

    return jsonify(result)


@app.route("/api/devices/<device_id>/demo-alert", methods=["POST"])
@token_required
def demo_alert(device_id):
    family_id = request.family_id
    result = create_demo_alert(family_id, device_id)
    if not result:
        return jsonify({"error": "Device not found"}), 404
    return jsonify(result)


# ---------- ALERTS CRUD ----------

@app.route("/api/alerts", methods=["GET", "POST"])
@token_required
def alerts_collection():
    family_id = request.family_id

    if request.method == "GET":
        limit = int(request.args.get("limit", 50))
        alerts = list_alerts(family_id, limit=limit)
        return jsonify(alerts)

    payload = request.json or {}
    alert = create_alert(family_id, payload)
    return jsonify(alert), 201


@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
@token_required
def delete_alert_route(alert_id):
    family_id = request.family_id
    ok = delete_alert(family_id, alert_id)
    if not ok:
        return jsonify({"error": "Alert not found"}), 404
    return jsonify({"status": "deleted"})


# ---------- PUSH SUBSCRIPTIONS ----------

@app.route("/api/push/subscribe", methods=["POST"])
@token_required
def push_subscribe_route():
    family_id = request.family_id
    subscription = request.json or {}

    try:
        subscribe_push(family_id, subscription)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"status": "ok"})


# ---------- HEALTH ----------

@app.route("/api/health")
def health():
    return {"status": "ok"}


# ---------- BOOTSTRAP DB ----------

init_db()
seed_data()

if __name__ == "__main__":
    app.run(port=5000, debug=True)
