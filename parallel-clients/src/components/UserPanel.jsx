export default function UserPanel({ name, isSelf }) {
  return (
    <div className="card" style={{ height: "420px", display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "12px" }}>
        <h3 style={{ fontWeight: 500 }}>{name}</h3>
        {isSelf && <span style={{ color: "#6366f1", fontSize: "12px" }}>You</span>}
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          paddingRight: "4px",
        }}
      >
        <div style={{ background: "#1F1F22", padding: "12px", borderRadius: "12px", marginBottom: "10px", color: "#bfbfc5" }}>
          Live AI responses will appear here.
        </div>
      </div>
    </div>
  );
}
