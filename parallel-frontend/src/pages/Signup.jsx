import { motion } from "framer-motion";
import "./Auth.css";

export default function Signup({ goLogin }) {
  return (
    <div className="auth-container">
      <motion.div
        className="auth-card glass"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h2 className="auth-title">Create Account</h2>
        <p className="auth-subtitle">Start your workspace</p>

        <input className="auth-input" placeholder="Full Name" />
        <input className="auth-input" placeholder="Email" type="email" />
        <input className="auth-input" placeholder="Password" type="password" />

        <button className="auth-button">Sign Up</button>

        <p className="auth-footer">
          Already have an account? <span onClick={goLogin}>Sign in</span>
        </p>
      </motion.div>
    </div>
  );
}
