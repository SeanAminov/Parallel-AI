export default function CommandBar() {
  return (
    <div
      style={{
        width: "100%",
        position: "absolute",
        bottom: 0,
        background: "#0F0F10",
        borderTop: "1px solid #1F1F22",
        padding: "16px",
        display: "flex",
        gap: "12px",
      }}
    >
      <input
        style={{
          flex: 1,
          background: "#151517",
          color: "white",
          border: "1px solid #252528",
          padding: "14px",
          borderRadius: "12px",
          outline: "none",
        }}
        placeholder="Type your prompt…"
      />

      <button
        style={{
          background: "#6366f1",
          padding: "14px 26px",
          borderRadius: "12px",
          color: "white",
          fontWeight: 500,
          border: "none",
          cursor: "pointer",
        }}
      >
        Run
      </button>
    </div>
  );
}
