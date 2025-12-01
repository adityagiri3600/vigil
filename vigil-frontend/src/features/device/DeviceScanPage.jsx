import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api";
import { FiCamera } from "react-icons/fi";

const styles = {
  page: {
    padding: "1.5rem",
    fontFamily: "system-ui, sans-serif",
    backgroundColor: "#f3f4f6",
    minHeight: "100vh",
  },
  wrapper: {
    maxWidth: "600px",
    margin: "0 auto",
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: "1rem",
    padding: "1.5rem",
    boxShadow: "0 10px 30px rgba(15,23,42,0.12)",
    border: "1px solid rgba(148,163,184,0.35)",
  },
  titleRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    marginBottom: "0.3rem",
  },
  title: {
    fontSize: "1.3rem",
    fontWeight: 600,
  },
  subtitle: {
    fontSize: "0.9rem",
    color: "#64748b",
    marginBottom: "1rem",
  },
  readerBox: {
    width: "100%",
    minHeight: "260px",
    borderRadius: "1rem",
    overflow: "hidden",
  },
  error: {
    color: "#b91c1c",
    fontSize: "0.9rem",
    marginTop: "0.75rem",
  },
  success: {
    color: "#16a34a",
    fontSize: "0.9rem",
    marginTop: "0.75rem",
  },
  buttonsRow: {
    marginTop: "1rem",
    display: "flex",
    justifyContent: "flex-end",
    gap: "0.5rem",
  },
  btn: {
    padding: "0.55rem 1rem",
    borderRadius: "999px",
    border: "none",
    fontSize: "0.85rem",
    fontWeight: 500,
    cursor: "pointer",
  },
  btnSecondary: {
    backgroundColor: "#e5e7eb",
    color: "#111827",
  },
  btnPrimary: {
    backgroundColor: "#2563eb",
    color: "#f9fafb",
  },
};

export default function DeviceScanPage() {
  const [scanError, setScanError] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let scannerInstance = null;
    let cancelled = false;

    async function initScanner() {
      try {
        const { Html5QrcodeScanner } = await import("html5-qrcode");

        if (cancelled) return;

        scannerInstance = new Html5QrcodeScanner(
          "qr-reader",
          {
            fps: 10,
            qrbox: 250,
            rememberLastUsedCamera: true,
          },
          false
        );

        const onScanSuccess = async (decodedText /*, decodedResult */) => {
          if (loading) return;

          setScanError("");
          setInfo("QR code detected, registering device...");

          let payload;
          try {
            payload = JSON.parse(decodedText);
          } catch (err) {
            console.error("Invalid QR payload:", err);
            setScanError("QR payload is not valid JSON.");
            return;
          }

          if (!payload.token) {
            setScanError("QR is missing a device token.");
            return;
          }

          setLoading(true);
          try {
            // Adjust path if your backend route is different (e.g. "/devices")
            await api.post("/devices/register", {
              token: payload.token,
              name: payload.name || "New Sensor",
              room: payload.room || "Unknown",
            });

            setInfo("Device registered successfully! 🎉");

            // Stop scanner and go back to dashboard after a short delay
            try {
              await scannerInstance.clear();
            } catch (e) {
              console.warn("Scanner clear error:", e);
            }

            setTimeout(() => {
              navigate("/dashboard"); // or "/" depending on your routing
            }, 900);
          } catch (err) {
            console.error(err);
            setScanError(
              err?.response?.data?.error ||
                "Error while registering device. Please try again."
            );
          } finally {
            setLoading(false);
          }
        };

        const onScanFailure = (errorMessage) => {
          // Called repeatedly while scanning; keep this silent to avoid spam
          // console.log("scan failure:", errorMessage);
        };

        scannerInstance.render(onScanSuccess, onScanFailure);
      } catch (err) {
        console.error("QR init error:", err);
        setScanError("Unable to access camera. Check permissions.");
      }
    }

    initScanner();

    return () => {
      cancelled = true;
      if (scannerInstance) {
        scannerInstance
          .clear()
          .catch((err) => console.warn("Scanner clear on unmount error:", err));
      }
    };
  }, [navigate, loading]);

  return (
    <div style={styles.page}>
      <div style={styles.wrapper}>
        <div style={styles.card}>
          <div style={styles.titleRow}>
            <FiCamera />
            <h2 style={styles.title}>Scan device QR code</h2>
          </div>
          <p style={styles.subtitle}>
            Open <code>device_qr.png</code> from your emulator and point your
            phone or laptop camera at it. We’ll automatically register the sensor
            to this family account.
          </p>

          <div id="qr-reader" style={styles.readerBox} />

          {scanError && <p style={styles.error}>{scanError}</p>}
          {info && !scanError && <p style={styles.success}>{info}</p>}

          <div style={styles.buttonsRow}>
            <button
              type="button"
              style={{ ...styles.btn, ...styles.btnSecondary }}
              onClick={() => navigate("/dashboard")} // adjust if your dashboard route is "/"
            >
              Back to dashboard
            </button>
            <button
              type="button"
              style={{ ...styles.btn, ...styles.btnPrimary }}
              onClick={() => window.location.reload()}
            >
              Rescan
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
