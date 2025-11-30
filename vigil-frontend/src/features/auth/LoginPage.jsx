import React, { useState } from "react";
import { useNavigate, Link, useLocation } from "react-router-dom";
import api, { setAuthToken } from "../../api";
import { useLang } from "../../LanguageContext";

function LoginPage({ setUser }) {
  const { t } = useLang();
  const [email, setEmail] = useState("demo@vigil.com");
  const [password, setPassword] = useState("demo123");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/auth/login", { email, password });
      const { token, user } = res.data;
      setAuthToken(token);
      setUser(user);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.response?.data?.error || "Login failed");
    }
  };

  return (
    <div className="auth-container">
      <h2>{t.login}</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <label>{t.email}</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>{t.password}</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">{t.login}</button>
      </form>
      <p>
        {t.noAccount} <Link to="/signup">{t.signup}</Link>
      </p>
    </div>
  );
}

export default LoginPage;
