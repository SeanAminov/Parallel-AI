export default function CollabDrawer() {
  return (
    <div
      style={{
        position: "absolute",
        right: 0,
        top: "60px",
        height: "calc(100% - 120px)",
        width: "300px",
        background: "#151517",
        borderLeft: "1px solid #1F1F22",
        padding: "20px",
      }}
    >
      <h3 style={{ marginBottom: "12px", fontWeight: 500 }}>Shared Notes</h3>
      <textarea
        style={{
          width: "100%",
          height: "90%",
          background: "#1F1F22",
          color: "white",
          border: "1px solid #252528",
          borderRadius: "10px",
          padding: "12px",
          outline: "none",
        }}
        placeholder="Collaborative notes go here..."
      />
    </div>
  );
}
