import { motion } from "framer-motion";
import "./Auth.css";

export default function Login({ goSignup, goForgot, goDashboard }) {
  return (
    <div className="auth-container">
      <motion.div
        className="auth-card glass"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2 className="auth-title">Welcome Back</h2>
        <p className="auth-subtitle">Sign in to your workspace</p>

        <input className="auth-input" placeholder="Email" type="email" />
        <input className="auth-input" placeholder="Password" type="password" />

        <button className="auth-button" onClick={goDashboard}>
          Sign In
        </button>

        <p className="auth-link" onClick={goForgot}>
          Forgot password?
        </p>

        <p className="auth-footer">
          New here? <span onClick={goSignup}>Create an account</span>
        </p>
      </motion.div>
    </div>
  );
}
