// src/components/CommandBar.jsx
export default function CommandBar({
  value, onChange, onRun, disabled,
  mode, setMode, teammate, setTeammate
}) {
  return (
    <div
      style={{
        width: "100%",
        padding: "16px",
        background: "rgba(10,10,15,0.55)",
        borderTop: "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        gap: "10px",
        position: "absolute",
        bottom: 0, left: 0,
        alignItems: "center"
      }}
    >
      <select
        value={mode}
        onChange={(e) => setMode(e.target.value)}
        style={{ padding: "10px", borderRadius: 10 }}
        title="Routing mode"
      >
        <option value="self">Self</option>
        <option value="teammate">Teammate</option>
        <option value="team">Ask Team</option>
      </select>

      {mode !== "team" && (
        <select
          value={teammate}
          onChange={(e) => setTeammate(e.target.value)}
          style={{ padding: "10px", borderRadius: 10 }}
          title="Target agent"
        >
          <option value="yug">Yug</option>
          <option value="sean">Sean</option>
          <option value="severin">Severin</option>
          <option value="nayab">Nayab</option>
        </select>
      )}

      <input
        placeholder="Ask something…"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => (e.key === "Enter" ? onRun() : null)}
        style={{
          flex: 1, padding: "14px", borderRadius: "10px",
          border: "none", background: "rgba(255,255,255,0.06)",
          color: "white", outline: "none", fontSize: "16px",
        }}
      />

      <button
        onClick={onRun}
        disabled={disabled}
        style={{
          padding: "12px 24px", borderRadius: "12px", border: "none",
          background: "linear-gradient(135deg,#7c3aed,#6366f1)",
          color: "white", cursor: disabled ? "not-allowed" : "pointer",
          fontSize: 16, opacity: disabled ? 0.6 : 1,
        }}
      >
        Send
      </button>
    </div>
  );
}
