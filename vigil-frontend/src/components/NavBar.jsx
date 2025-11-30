import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useLang } from "../LanguageContext";
import { setAuthToken } from "../api";

const navStyles = {
  nav: {
    backgroundColor: "#111827",
    color: "#ffffff",
    padding: "0.75rem 1rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "1rem",
  },
  left: {
    display: "flex",
    alignItems: "center",
  },
  center: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
  },
  right: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  },
  appName: {
    fontWeight: 600,
    fontSize: "0.95rem",
  },
  link: {
    color: "#e5e7eb",
    textDecoration: "none",
    fontSize: "0.9rem",
  },
  linkHover: {
    textDecoration: "underline",
  },
  langButton: (active) => ({
    border: "none",
    background: "transparent",
    color: active ? "#ffffff" : "#9ca3af",
    fontSize: "0.85rem",
    cursor: "pointer",
    textDecoration: active ? "underline" : "none",
    fontWeight: active ? 600 : 400,
  }),
  actionButton: {
    border: "1px solid #4b5563",
    backgroundColor: "transparent",
    color: "#e5e7eb",
    padding: "0.25rem 0.6rem",
    borderRadius: "9999px",
    fontSize: "0.8rem",
    cursor: "pointer",
  },
};

function NavBar({ user, setUser }) {
  const { t, lang, setLang } = useLang();
  const navigate = useNavigate();
  const token = localStorage.getItem("token");

  const logout = () => {
    setAuthToken(null);
    setUser(null);
    navigate("/login");
  };

  return (
    <nav style={navStyles.nav}>
      <div style={navStyles.left}>
        <span style={navStyles.appName}>{t.appName}</span>
      </div>

      <div style={navStyles.center}>
        {token && (
          <>
            <Link to="/" style={navStyles.link}>
              {t.dashboard}
            </Link>
            <Link to="/family" style={navStyles.link}>
              {t.family}
            </Link>
          </>
        )}
      </div>

      <div style={navStyles.right}>
        <span style={{ fontSize: "0.8rem", color: "#d1d5db" }}>
          {t.language}:
        </span>
        <button
          onClick={() => setLang("en")}
          style={navStyles.langButton(lang === "en")}
        >
          EN
        </button>
        <button
          onClick={() => setLang("ko")}
          style={navStyles.langButton(lang === "ko")}
        >
          한국어
        </button>

        {token ? (
          <button onClick={logout} style={navStyles.actionButton}>
            {t.logout}
          </button>
        ) : (
          <>
            <Link to="/login" style={navStyles.link}>
              {t.login}
            </Link>
            <Link to="/signup" style={navStyles.link}>
              {t.signup}
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}

export default NavBar;
