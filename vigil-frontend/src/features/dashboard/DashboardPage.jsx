import React, { useEffect, useState } from "react";
import api from "../../api";
import { useLang } from "../../LanguageContext";

const styles = {
  page: {
    padding: "1.5rem",
    fontFamily: "system-ui, sans-serif",
    backgroundColor: "#f3f4f6",
    minHeight: "100vh",
  },
  heading: {
    marginBottom: "1rem",
  },
  summaryGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
    gap: "0.75rem",
    marginBottom: "1rem",
  },
  summaryCard: {
    backgroundColor: "#ffffff",
    borderRadius: "0.75rem",
    padding: "0.75rem 1rem",
    boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
  },
  summaryTitle: {
    fontSize: "0.85rem",
    color: "#6b7280",
    marginBottom: "0.25rem",
  },
  summaryStatus: {
    fontWeight: 600,
  },
  summaryLabel: {
    fontSize: "0.8rem",
    color: "#6b7280",
  },
  summaryValue: {
    fontSize: "1.5rem",
    fontWeight: 600,
  },
  summarySub: {
    fontSize: "0.75rem",
    color: "#9ca3af",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
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
  },
  // alert timeline
  alertTimelineWrapper: {
    maxHeight: "260px",
    overflowY: "auto",
  },
  timelineItem: {
    display: "flex",
    alignItems: "flex-start",
    marginBottom: "0.75rem",
  },
  timelineDot: (severity) => ({
    width: "10px",
    height: "10px",
    borderRadius: "9999px",
    marginRight: "8px",
    marginTop: "4px",
    backgroundColor:
      severity === "high"
        ? "#ef4444"
        : severity === "medium"
        ? "#f59e0b"
        : "#9ca3af",
    flexShrink: 0,
  }),
  timelineLine: {
    width: "2px",
    backgroundColor: "#e5e7eb",
    marginRight: "8px",
    marginTop: "4px",
    alignSelf: "stretch",
    flexShrink: 0,
  },
  timelineContent: {
    fontSize: "0.8rem",
  },
  timelineTime: {
    color: "#6b7280",
  },
  // devices
  deviceItem: {
    padding: "0.5rem 0",
    borderBottom: "1px solid #e5e7eb",
    fontSize: "0.85rem",
  },
  deviceMain: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "0.25rem",
  },
  deviceName: {
    fontWeight: 500,
  },
  deviceStatusBadge: (status) => ({
    padding: "0.15rem 0.5rem",
    borderRadius: "9999px",
    fontSize: "0.7rem",
    textTransform: "uppercase",
    backgroundColor: status === "online" ? "#dcfce7" : "#fee2e2",
    color: status === "online" ? "#166534" : "#991b1b",
  }),
  deviceSub: {
    fontSize: "0.75rem",
    color: "#6b7280",
  },
  // activity chart
  timelineChart: {
    display: "flex",
    gap: "0.5rem",
    alignItems: "flex-end",
    height: "120px",
  },
  timelineBarWrapper: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  timelineBar: (height) => ({
    width: "16px",
    borderRadius: "9999px 9999px 0 0",
    backgroundColor: "#3b82f6",
    height: `${height}px`,
  }),
  timelineLabel: {
    fontSize: "0.7rem",
    marginTop: "0.25rem",
    color: "#6b7280",
  },
  // room heatmap grid
  roomGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
    gap: "0.5rem",
  },
  roomCell: (bg) => ({
    padding: "0.5rem",
    borderRadius: "0.5rem",
    color: "#ffffff",
    fontSize: "0.8rem",
    backgroundColor: bg,
  }),
  roomName: {
    fontWeight: 500,
  },
  roomCount: {
    fontSize: "0.75rem",
  },
  // safety score
  safetyWrapper: {
    display: "flex",
    gap: "1rem",
    alignItems: "center",
  },
  safetyCircle: {
    width: "80px",
    height: "80px",
    borderRadius: "9999px",
    border: "4px solid #22c55e",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
  },
  safetyScore: {
    fontSize: "1.4rem",
    fontWeight: 600,
  },
  safetyMax: {
    fontSize: "0.7rem",
    color: "#6b7280",
  },
  safetyLabels: {
    fontSize: "0.85rem",
  },
  // today vs yesterday
  compareGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
    gap: "0.5rem",
  },
  compareCard: {
    borderRadius: "0.5rem",
    padding: "0.5rem",
    backgroundColor: "#f9fafb",
    fontSize: "0.8rem",
  },
  compareTitle: {
    fontWeight: 500,
    marginBottom: "0.25rem",
  },
  // camera
  cameraContainer: {
    position: "relative",
    borderRadius: "0.75rem",
    overflow: "hidden",
  },
  cameraImage: {
    width: "100%",
    display: "block",
    objectFit: "cover",
  },
  clockOverlay: {
    position: "absolute",
    top: "8px",
    left: "8px",
    backgroundColor: "rgba(0,0,0,0.6)",
    color: "#ffffff",
    padding: "4px 10px",
    borderRadius: "9999px",
    fontSize: "0.8rem",
    fontFamily: "monospace",
  },
};

function DashboardPage() {
  const { t } = useLang();
  const [alerts, setAlerts] = useState([]);
  const [devices, setDevices] = useState([]);
  const [activity, setActivity] = useState(null);
  const [summary, setSummary] = useState(null);
  const [activityTimeline, setActivityTimeline] = useState([]);
  const [roomStats, setRoomStats] = useState({});
  const [safetyScore, setSafetyScore] = useState(null);
  const [todayStats, setTodayStats] = useState(null);
  const [yesterdayStats, setYesterdayStats] = useState(null);
  const [clock, setClock] = useState(new Date());

  const fetchDashboard = async () => {
    const res = await api.get("/dashboard");
    setAlerts(res.data.alerts || []);
    setDevices(res.data.devices || []);
    setActivity(res.data.activity || null);
    setSummary(res.data.summary || null);
    setActivityTimeline(res.data.activity_timeline || []);
    setRoomStats(res.data.room_stats || {});
    setSafetyScore(res.data.safety_score || null);
    setTodayStats(res.data.today_stats || null);
    setYesterdayStats(res.data.yesterday_stats || null);
  };

  useEffect(() => {
    fetchDashboard();
    const id = setInterval(fetchDashboard, 15000);
    return () => clearInterval(id);
  }, []);

  // Realtime clock, updates every second
  useEffect(() => {
    const id = setInterval(() => {
      setClock(new Date());
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const maxRoomCount = Object.values(roomStats).reduce(
    (max, v) => (v > max ? v : max),
    0
  );

  const getStatusLabel = (status) => {
    if (status === "critical") return "🔴 Critical";
    if (status === "warning") return "🟠 Warning";
    return "🟢 OK";
  };

  const clockString = clock
    .toLocaleTimeString("en-GB", { hour12: false }) // HH:MM:SS 24h
    .slice(0, 8); // just in case locale adds extras

  return (
    <div style={styles.page}>
      <h2 style={styles.heading}>{t.dashboard}</h2>

      {/* SUMMARY BAR */}
      {summary && (
        <div style={styles.summaryGrid}>
          <div style={styles.summaryCard}>
            <div style={styles.summaryTitle}>{t.overview}</div>
            <div
              style={{
                ...styles.summaryStatus,
                color:
                  summary.status === "critical"
                    ? "#dc2626"
                    : summary.status === "warning"
                    ? "#f97316"
                    : "#16a34a",
              }}
            >
              {getStatusLabel(summary.status)}
            </div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryLabel}>{t.devices}</div>
            <div style={styles.summaryValue}>
              {summary.devices_online ?? 0}
            </div>
            <div style={styles.summarySub}>online</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryLabel}>{t.alertsCount}</div>
            <div style={styles.summaryValue}>
              {summary.alerts_last_24h ?? 0}
            </div>
            <div style={styles.summarySub}>last 24h</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryLabel}>Critical</div>
            <div style={styles.summaryValue}>
              {summary.critical_alerts ?? 0}
            </div>
            <div style={styles.summarySub}>high severity</div>
          </div>
        </div>
      )}

      {/* MAIN GRID */}
      <div style={styles.grid}>
        {/* Alerts timeline */}
        <section style={styles.card}>
          <h3 style={styles.cardTitle}>{t.alerts}</h3>
          <div style={styles.alertTimelineWrapper}>
            {alerts.length === 0 && <p>{t.noAlerts}</p>}
            {alerts.map((a, idx) => (
              <div key={idx} style={styles.timelineItem}>
                <div style={styles.timelineDot(a.severity)} />
                <div style={styles.timelineLine} />
                <div style={styles.timelineContent}>
                  <div style={styles.timelineTime}>{a.time}</div>
                  <div>
                    {a.type.toUpperCase()} – {a.room}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Devices panel */}
        <section style={styles.card}>
          <h3 style={styles.cardTitle}>{t.devices}</h3>
          {devices.map((d) => (
            <div key={d.id} style={styles.deviceItem}>
              <div style={styles.deviceMain}>
                <span style={styles.deviceName}>{d.name}</span>
                <span style={styles.deviceStatusBadge(d.status)}>
                  {d.status}
                </span>
              </div>
              <div style={styles.deviceSub}>
                Room: {d.room} · Last seen: {d.last_seen}
              </div>
            </div>
          ))}
        </section>

        {/* Activity timeline bars */}
        <section style={styles.card}>
          <h3 style={styles.cardTitle}>{t.activityTimeline}</h3>
          <div style={styles.timelineChart}>
            {activityTimeline.map((point, idx) => {
              const maxVal = Math.max(
                1,
                ...activityTimeline.map((p) => p.motions || 1)
              );
              const height = (point.motions / maxVal) * 80 + 10;
              return (
                <div key={idx} style={styles.timelineBarWrapper}>
                  <div style={styles.timelineBar(height)} />
                  <div style={styles.timelineLabel}>{point.label}</div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Room usage grid */}
        <section style={styles.card}>
          <h3 style={styles.cardTitle}>{t.roomUsage}</h3>
          <div style={styles.roomGrid}>
            {Object.entries(roomStats).map(([room, count]) => {
              const intensity =
                maxRoomCount > 0 ? count / maxRoomCount : 0.1;
              const bg = `rgba(37, 99, 235, ${0.2 + intensity * 0.6})`;
              return (
                <div key={room} style={styles.roomCell(bg)}>
                  <div style={styles.roomName}>{room}</div>
                  <div style={styles.roomCount}>{count} motions</div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Safety score */}
        <section style={styles.card}>
          <h3 style={styles.cardTitle}>{t.safetyScore}</h3>
          {safetyScore && (
            <div style={styles.safetyWrapper}>
              <div style={styles.safetyCircle}>
                <div style={styles.safetyScore}>{safetyScore.score}</div>
                <div style={styles.safetyMax}>/ 100</div>
              </div>
              <div style={styles.safetyLabels}>
                <div>{safetyScore.label_en}</div>
                <div>{safetyScore.label_ko}</div>
              </div>
            </div>
          )}
        </section>

        {/* Today vs yesterday */}
        <section style={styles.card}>
          <h3 style={styles.cardTitle}>
            {t.today} vs {t.yesterday}
          </h3>
          <div style={styles.compareGrid}>
            <div style={styles.compareCard}>
              <div style={styles.compareTitle}>{t.today}</div>
              {todayStats && (
                <>
                  <div>
                    {t.alertsCount}: {todayStats.alerts}
                  </div>
                  <div>
                    {t.motionsCount}: {todayStats.motions}
                  </div>
                </>
              )}
            </div>
            <div style={styles.compareCard}>
              <div style={styles.compareTitle}>{t.yesterday}</div>
              {yesterdayStats && (
                <>
                  <div>
                    {t.alertsCount}: {yesterdayStats.alerts}
                  </div>
                  <div>
                    {t.motionsCount}: {yesterdayStats.motions}
                  </div>
                </>
              )}
            </div>
          </div>
        </section>

        {/* Camera feed – static image + realtime clock */}
        <section style={styles.card}>
          <h3 style={styles.cardTitle}>{t.cameraFeed}</h3>
          <div style={styles.cameraContainer}>
            <div style={styles.clockOverlay}>{clockString}</div>
            {/* Make sure you have /public/camera_demo.jpg */}
            <img
              src="/image.png"
              alt="Camera feed"
              style={styles.cameraImage}
            />
          </div>
        </section>

        {/* Simple recent activity */}
        <section style={styles.card}>
          <h3 style={styles.cardTitle}>{t.recentActivity}</h3>
          {activity && (
            <div>
              <p>
                {t.lastMotion}: {activity.last_motion}
              </p>
              <p>
                {t.roomsVisited}: {activity.rooms_visited.join(", ")}
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default DashboardPage;
