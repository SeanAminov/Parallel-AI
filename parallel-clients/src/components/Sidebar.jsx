export default function Sidebar() {
  return (
    <aside
      style={{
        width: "80px",
        background: "#0F0F10",
        borderRight: "1px solid #1F1F22",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        paddingTop: "24px",
        gap: "40px",
      }}
    >
      <div style={{ fontSize: "28px" }}>⚡</div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "28px",
          color: "#7b7b85",
        }}
      >
        <button className="hover-btn">🏠</button>
        <button className="hover-btn">💬</button>
        <button className="hover-btn">📚</button>
        <button className="hover-btn">⚙️</button>
      </div>
    </aside>
  );
}
