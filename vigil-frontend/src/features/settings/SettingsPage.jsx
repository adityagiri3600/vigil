import React, { useEffect, useState } from "react";
import api from "../../api";
import { useLang } from "../../LanguageContext";
import { FiPhoneCall, FiBell, FiAlertTriangle, FiVideo } from "react-icons/fi";

const styles = {
  page: {
    padding: "1.5rem",
    fontFamily: "system-ui, sans-serif",
    backgroundColor: "#f3f4f6",
    minHeight: "100vh",
  },
  heading: {
    marginBottom: "1rem",
    fontSize: "1.25rem",
    fontWeight: 600,
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: "0.75rem",
    padding: "1rem",
    boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
    maxWidth: "540px",
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
  checkboxRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    fontSize: "0.9rem",
  },
  select: {
    width: "100%",
    padding: "0.45rem 0.5rem",
    borderRadius: "0.375rem",
    border: "1px solid #d1d5db",
    fontSize: "0.9rem",
  },
  buttonRow: {
    marginTop: "0.75rem",
    display: "flex",
    justifyContent: "flex-start",
    gap: "0.5rem",
  },
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

function SettingsPage() {
  const { t } = useLang();
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const loadSettings = async () => {
    const res = await api.get("/settings");
    setSettings(res.data);
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleChange = (field, value) => {
    setSettings((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setMessage("");
    try {
      const res = await api.post("/settings", settings);
      setSettings(res.data);
      setMessage(t.settingsSaved);
    } catch (e) {
      setMessage("Error saving settings");
    } finally {
      setSaving(false);
    }
  };

  if (!settings) {
    return (
      <div style={styles.page}>
        <h2 style={styles.heading}>{t.settings}</h2>
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <h2 style={styles.heading}>{t.settings}</h2>
      <div style={styles.card}>
        <h3 style={{ marginTop: 0, marginBottom: "0.75rem" }}>
          {t.globalSettings}
        </h3>

        {/* Emergency number */}
        <div style={styles.field}>
          <div
            style={styles.label}
            title="Default emergency number used when auto-calling services."
          >
            <FiPhoneCall style={styles.icon} />
            <span>{t.emergencyNumber}</span>
          </div>
          <input
            style={styles.input}
            value={settings.emergency_number || ""}
            onChange={(e) =>
              handleChange("emergency_number", e.target.value)
            }
          />
        </div>

        {/* Auto-call emergency */}
        <div style={styles.field}>
          <div
            style={styles.label}
            title="If enabled, the system will automatically call the emergency number after a severe incident if no response is detected."
          >
            <FiAlertTriangle style={styles.icon} />
            <span>{t.autoCallEmergency}</span>
          </div>
          <div style={styles.checkboxRow}>
            <input
              type="checkbox"
              checked={!!settings.auto_call_emergency}
              onChange={(e) =>
                handleChange("auto_call_emergency", e.target.checked)
              }
            />
            <span>{t.autoCallEmergency}</span>
          </div>
        </div>

        {/* Auto-call delay */}
        <div style={styles.field}>
          <div
            style={styles.label}
            title="How long to wait before automatically dialing emergency services."
          >
            <FiAlertTriangle style={styles.icon} />
            <span>{t.autoCallDelaySeconds}</span>
          </div>
          <input
            style={styles.input}
            type="number"
            min={0}
            value={settings.auto_call_delay_seconds || 0}
            onChange={(e) =>
              handleChange("auto_call_delay_seconds", Number(e.target.value))
            }
          />
        </div>

        {/* Notify family push */}
        <div style={styles.field}>
          <div
            style={styles.label}
            title="Send push/app notifications to family members on alerts."
          >
            <FiBell style={styles.icon} />
            <span>{t.notifyFamilyPush}</span>
          </div>
          <div style={styles.checkboxRow}>
            <input
              type="checkbox"
              checked={!!settings.notify_family_push}
              onChange={(e) =>
                handleChange("notify_family_push", e.target.checked)
              }
            />
            <span>{t.notifyFamilyPush}</span>
          </div>
        </div>

        {/* Notify family SMS */}
        <div style={styles.field}>
          <div
            style={styles.label}
            title="Also send SMS messages for important alerts."
          >
            <FiBell style={styles.icon} />
            <span>{t.notifyFamilySms}</span>
          </div>
          <div style={styles.checkboxRow}>
            <input
              type="checkbox"
              checked={!!settings.notify_family_sms}
              onChange={(e) =>
                handleChange("notify_family_sms", e.target.checked)
              }
            />
            <span>{t.notifyFamilySms}</span>
          </div>
        </div>

        {/* Fall detection sensitivity */}
        <div style={styles.field}>
          <div
            style={styles.label}
            title="Higher sensitivity detects more potential falls but may increase false alarms."
          >
            <FiAlertTriangle style={styles.icon} />
            <span>{t.fallDetectionSensitivity}</span>
          </div>
          <select
            style={styles.select}
            value={settings.fall_detection_sensitivity || "medium"}
            onChange={(e) =>
              handleChange("fall_detection_sensitivity", e.target.value)
            }
          >
            <option value="low">{t.sensitivityLow}</option>
            <option value="medium">{t.sensitivityMedium}</option>
            <option value="high">{t.sensitivityHigh}</option>
          </select>
        </div>

        {/* Video streaming enabled */}
        <div style={styles.field}>
          <div
            style={styles.label}
            title="Allow video to be streamed to caregivers when a serious incident occurs."
          >
            <FiVideo style={styles.icon} />
            <span>{t.videoStreamingEnabled}</span>
          </div>
          <div style={styles.checkboxRow}>
            <input
              type="checkbox"
              checked={!!settings.video_streaming_enabled}
              onChange={(e) =>
                handleChange("video_streaming_enabled", e.target.checked)
              }
            />
            <span>{t.videoStreamingEnabled}</span>
          </div>
        </div>

        <div style={styles.buttonRow}>
          <button
            style={styles.saveButton}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving..." : t.save}
          </button>
        </div>

        {message && <div style={styles.message}>{message}</div>}
      </div>
    </div>
  );
}

export default SettingsPage;
