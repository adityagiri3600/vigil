import React from "react";
import { useLang } from "../LanguageContext";

function NotificationList({ alerts }) {
  const { t, lang } = useLang();
  if (!alerts || alerts.length === 0) return <p>{t.noAlerts}</p>;

  return (
    <ul className="alert-list">
      {alerts.map((a, idx) => (
        <li key={idx} className={`alert-item alert-${a.severity}`}>
          <strong>{a.type.toUpperCase()}</strong>{" "}
          <span>
            {lang === "ko" ? a.message_ko : a.message_en} – {a.room} ({a.time})
          </span>
        </li>
      ))}
    </ul>
  );
}

export default NotificationList;
