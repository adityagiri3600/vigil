import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api, { setAuthToken } from "../../api";
import { useLang } from "../../LanguageContext";

function SignupPage({ setUser }) {
  const { t } = useLang();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [familyId, setFamilyId] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api.post("/auth/signup", {
        email,
        password,
        name,
        family_id: familyId || null,
      });
      const { token, user } = res.data;
      setAuthToken(token);
      setUser(user);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.error || "Signup failed");
    }
  };

  return (
    <div className="auth-container">
      <h2>{t.signup}</h2>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <label>{t.name}</label>
        <input value={name} onChange={(e) => setName(e.target.value)} />
        <label>{t.email}</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>{t.password}</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <label>{t.familyIdOptional}</label>
        <input
          value={familyId}
          onChange={(e) => setFamilyId(e.target.value)}
        />
        <button type="submit">{t.signup}</button>
      </form>
      <p>
        {t.haveAccount} <Link to="/login">{t.login}</Link>
      </p>
    </div>
  );
}

export default SignupPage;
