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
    fontSize: "1.25rem",
    fontWeight: 600,
  },
  tableWrapper: {
    backgroundColor: "#ffffff",
    borderRadius: "0.75rem",
    padding: "1rem",
    boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "0.9rem",
  },
  th: {
    textAlign: "left",
    borderBottom: "1px solid #e5e7eb",
    padding: "0.5rem",
    backgroundColor: "#f9fafb",
    fontWeight: 500,
  },
  td: {
    borderBottom: "1px solid #e5e7eb",
    padding: "0.5rem",
  },
  rowLast: {
    borderBottom: "none",
  },
};

function FamilyPage() {
  const { t } = useLang();
  const [members, setMembers] = useState([]);

  useEffect(() => {
    const fetchMembers = async () => {
      const res = await api.get("/family/members");
      setMembers(res.data || []);
    };
    fetchMembers();
  }, []);

  return (
    <div style={styles.page}>
      <h2 style={styles.heading}>{t.family}</h2>
      <div style={styles.tableWrapper}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>{t.name}</th>
              <th style={styles.th}>{t.email}</th>
            </tr>
          </thead>
          <tbody>
            {members.map((m, idx) => (
              <tr key={m.email}>
                <td
                  style={{
                    ...styles.td,
                    ...(idx === members.length - 1 ? styles.rowLast : {}),
                  }}
                >
                  {m.name}
                </td>
                <td
                  style={{
                    ...styles.td,
                    ...(idx === members.length - 1 ? styles.rowLast : {}),
                  }}
                >
                  {m.email}
                </td>
              </tr>
            ))}
            {members.length === 0 && (
              <tr>
                <td colSpan={2} style={styles.td}>
                  (no members yet)
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default FamilyPage;
