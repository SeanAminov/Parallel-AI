import { useState } from "react";
import { motion } from "framer-motion";
import "./Auth.css";

export default function Signup({ goLogin, goDashboard }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(false);

  const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000";

  const submit = async () => {
    if (!name || !email || !password) {
      setStatus("Fill all fields.");
      return;
    }
    setLoading(true);
    setStatus("");
    try {
      const res = await fetch(`${apiBase}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name, email, password }),
      });
      if (!res.ok) {
        setStatus("Signup failed.");
      } else {
        setStatus("Account created.");
        goDashboard();
      }
    } catch (err) {
      setStatus("Signup failed.");
    } finally {
      setLoading(false);
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter") submit();
  };

  return (
    <div className="auth-container">
      <motion.div
        className="auth-card glass"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2 className="auth-title">Create Account</h2>
        <p className="auth-subtitle">Start your workspace</p>

        <input
          className="auth-input"
          placeholder="Full Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={onKey}
        />
        <input
          className="auth-input"
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={onKey}
        />
        <input
          className="auth-input"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={onKey}
        />

        {status && <div className="auth-status">{status}</div>}

        <button className="auth-button" onClick={submit} disabled={loading}>
          {loading ? "Signing up..." : "Sign Up"}
        </button>

        <p className="auth-footer">
          Already have an account? <span onClick={goLogin}>Sign in</span>
        </p>
      </motion.div>
    </div>
  );
}
