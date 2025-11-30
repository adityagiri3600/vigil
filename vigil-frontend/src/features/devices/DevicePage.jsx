import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "../../api";
import { useLang } from "../../LanguageContext";
import { FiCpu, FiArrowLeft, FiAlertTriangle, FiPhoneCall } from "react-icons/fi";

const styles = {
  page: {
    padding: "1.5rem",
    fontFamily: "system-ui, sans-serif",
    backgroundColor: "#f3f4f6",
    minHeight: "100vh",
  },
  headingRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    marginBottom: "1rem",
  },
  backLink: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.25rem",
    fontSize: "0.9rem",
    textDecoration: "none",
    color: "#2563eb",
  },
  cardRow: {
    display: "grid",
    gridTemplateColumns: "minmax(0, 1.2fr) minmax(0, 1fr)",
    gap: "1rem",
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: "0.75rem",
    padding: "1rem",
    boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
  },
  cardTitle: {
    marginTop: 0,
    marginBottom: "0.75rem",
    fontSize: "1rem",
    fontWeight: 600,
    display: "flex",
    alignItems: "center",
    gap: "0.35rem",
  },
  field: {
    marginBottom: "0.75rem",
  },
  label: {
    display: "flex",
    alignItems: "center",
    gap: "0.35rem",
    fontSize: "0.9rem",
    fontWeight: 500,
    marginBottom: "0.25rem",
  },
  input: {
    width: "100%",
    padding: "0.45rem 0.5rem",
    borderRadius: "0.375rem",
    border: "1px solid #d1d5db",
    fontSize: "0.9rem",
  },
  select: {
    width: "100%",
    padding: "0.45rem 0.5rem",
    borderRadius: "0.375rem",
    border: "1px solid #d1d5db",
    fontSize: "0.9rem",
  },
  checkboxRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    fontSize: "0.9rem",
  },
  infoRow: {
    fontSize: "0.85rem",
    marginBottom: "0.35rem",
  },
  badge: (status) => ({
    display: "inline-block",
    padding: "0.15rem 0.5rem",
    borderRadius: "9999px",
    fontSize: "0.75rem",
    textTransform: "uppercase",
    backgroundColor: status === "online" ? "#dcfce7" : "#fee2e2",
    color: status === "online" ? "#166534" : "#991b1b",
  }),
  saveButton: {
    border: "none",
    padding: "0.45rem 0.9rem",
    borderRadius: "9999px",
    backgroundColor: "#2563eb",
    color: "#ffffff",
    fontSize: "0.9rem",
    cursor: "pointer",
  },
  message: {
    marginTop: "0.5rem",
    fontSize: "0.85rem",
    color: "#16a34a",
  },
  icon: {
    verticalAlign: "middle",
  },
};

function DevicePage() {
  const { t } = useLang();
  const { deviceId } = useParams();
  const navigate = useNavigate();

  const [device, setDevice] = useState(null);
  const [familySettings, setFamilySettings] = useState(null);
  const [deviceSettings, setDeviceSettings] = useState(null);
  const [effectiveSettings, setEffectiveSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const loadDevice = async () => {
    const res = await api.get(`/devices/${deviceId}`);
    setDevice(res.data.device);
    setFamilySettings(res.data.family_settings);
    setDeviceSettings(
      res.data.device_settings || {
        emergency_number: res.data.family_settings.emergency_number,
        auto_call_emergency: res.data.family_settings.auto_call_emergency,
        auto_call_delay_seconds:
          res.data.family_settings.auto_call_delay_seconds,
        fall_detection_sensitivity:
          res.data.family_settings.fall_detection_sensitivity,
      }
    );
    setEffectiveSettings(res.data.effective_settings);
  };

  useEffect(() => {
    loadDevice().catch(() => {
      navigate("/");
    });
  }, [deviceId, navigate]);

  const handleChange = (field, value) => {
    setDeviceSettings((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    if (!deviceSettings) return;
    setSaving(true);
    setMessage("");
    try {
      const res = await api.post(
        `/devices/${deviceId}/settings`,
        deviceSettings
      );
      setDeviceSettings(res.data.device_settings);
      setEffectiveSettings(res.data.effective_settings);
      setMessage("Settings sent to sensor");
    } catch (e) {
      setMessage("Error updating device settings");
    } finally {
      setSaving(false);
    }
  };

  if (!device || !familySettings || !deviceSettings || !effectiveSettings) {
    return (
      <div style={styles.page}>
        <div style={styles.headingRow}>
          <button
            onClick={() => navigate(-1)}
            style={{
              border: "none",
              background: "transparent",
              color: "#2563eb",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "0.25rem",
              padding: 0,
            }}
          >
            <FiArrowLeft />
            {t.backToDashboard}
          </button>
        </div>
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <div style={styles.headingRow}>
        <button
          onClick={() => navigate(-1)}
          style={{
            border: "none",
            background: "transparent",
            color: "#2563eb",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "0.25rem",
            padding: 0,
          }}
        >
          <FiArrowLeft />
          {t.backToDashboard}
        </button>
      </div>

      <h2 style={{ marginTop: 0, marginBottom: "1rem" }}>
        <FiCpu style={{ verticalAlign: "middle", marginRight: "0.35rem" }} />
        {t.devicePage}: {device.name}
      </h2>

      <div style={styles.cardRow}>
        {/* Device settings editor */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>
            <FiAlertTriangle style={styles.icon} />
            {t.deviceSettings}
          </h3>

          <div style={{ ...styles.infoRow }}>
            <strong>ID:</strong> {device.id}
          </div>
          <div style={styles.infoRow}>
            <strong>Room:</strong> {device.room}
          </div>
          <div style={styles.infoRow}>
            <strong>Status:</strong>{" "}
            <span style={styles.badge(device.status)}>
              {device.status}
            </span>
          </div>

          {/* Device emergency number */}
          <div style={styles.field}>
            <div
              style={styles.label}
              title="Override the default emergency number for this sensor."
            >
              <FiPhoneCall style={styles.icon} />
              <span>{t.emergencyNumber}</span>
            </div>
            <input
              style={styles.input}
              value={deviceSettings.emergency_number || ""}
              onChange={(e) =>
                handleChange("emergency_number", e.target.value)
              }
            />
          </div>

          {/* Device auto-call */}
          <div style={styles.field}>
            <div
              style={styles.label}
              title="If enabled, this sensor will auto-call emergency services using its own settings."
            >
              <FiAlertTriangle style={styles.icon} />
              <span>{t.autoCallEmergency}</span>
            </div>
            <div style={styles.checkboxRow}>
              <input
                type="checkbox"
                checked={!!deviceSettings.auto_call_emergency}
                onChange={(e) =>
                  handleChange("auto_call_emergency", e.target.checked)
                }
              />
              <span>{t.autoCallEmergency}</span>
            </div>
          </div>

          {/* Device auto-call delay */}
          <div style={styles.field}>
            <div
              style={styles.label}
              title="How long this specific sensor waits before auto-calling."
            >
              <FiAlertTriangle style={styles.icon} />
              <span>{t.autoCallDelaySeconds}</span>
            </div>
            <input
              style={styles.input}
              type="number"
              min={0}
              value={deviceSettings.auto_call_delay_seconds || 0}
              onChange={(e) =>
                handleChange(
                  "auto_call_delay_seconds",
                  Number(e.target.value)
                )
              }
            />
          </div>

          {/* Device fall detection sensitivity */}
          <div style={styles.field}>
            <div
              style={styles.label}
              title="Fine-tune how sensitive this sensor is to falls."
            >
              <FiAlertTriangle style={styles.icon} />
              <span>{t.fallDetectionSensitivity}</span>
            </div>
            <select
              style={styles.select}
              value={
                deviceSettings.fall_detection_sensitivity ||
                familySettings.fall_detection_sensitivity ||
                "medium"
              }
              onChange={(e) =>
                handleChange("fall_detection_sensitivity", e.target.value)
              }
            >
              <option value="low">{t.sensitivityLow}</option>
              <option value="medium">{t.sensitivityMedium}</option>
              <option value="high">{t.sensitivityHigh}</option>
            </select>
          </div>

          <button
            style={styles.saveButton}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : t.save}
          </button>
          {message && <div style={styles.message}>{message}</div>}
        </div>

        {/* Read-only overview */}
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>{t.familySettings}</h3>
          <div style={styles.infoRow}>
            <strong>{t.emergencyNumber}:</strong>{" "}
            {familySettings.emergency_number}
          </div>
          <div style={styles.infoRow}>
            <strong>{t.autoCallEmergency}:</strong>{" "}
            {familySettings.auto_call_emergency ? "ON" : "OFF"}
          </div>
          <div style={styles.infoRow}>
            <strong>{t.autoCallDelaySeconds}:</strong>{" "}
            {familySettings.auto_call_delay_seconds} s
          </div>
          <div style={styles.infoRow}>
            <strong>{t.fallDetectionSensitivity}:</strong>{" "}
            {familySettings.fall_detection_sensitivity}
          </div>

          <h3 style={{ ...styles.cardTitle, marginTop: "1rem" }}>
            {t.effectiveSettings}
          </h3>
          <div style={styles.infoRow}>
            <strong>{t.emergencyNumber}:</strong>{" "}
            {effectiveSettings.emergency_number}
          </div>
          <div style={styles.infoRow}>
            <strong>{t.autoCallEmergency}:</strong>{" "}
            {effectiveSettings.auto_call_emergency ? "ON" : "OFF"}
          </div>
          <div style={styles.infoRow}>
            <strong>{t.autoCallDelaySeconds}:</strong>{" "}
            {effectiveSettings.auto_call_delay_seconds} s
          </div>
          <div style={styles.infoRow}>
            <strong>{t.fallDetectionSensitivity}:</strong>{" "}
            {effectiveSettings.fall_detection_sensitivity}
          </div>
        </div>
      </div>
    </div>
  );
}

export default DevicePage;
