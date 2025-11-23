import "./SummaryPanel.css";

const statusMap = {
  Chat: { label: "In chat", detail: "Responding to workspace asks." },
  Team: { label: "Team activity", detail: "Watching live team updates." },
  Inbox: { label: "Inbox review", detail: "Triaging routed tasks." },
  IDE: { label: "Development", detail: "Editing code in IDE mode." },
};

export default function SummaryPanel({ user = { name: "You" }, activeTool = "Chat" }) {
  const status = statusMap[activeTool] || statusMap.Chat;
  const activity = [
    { id: "you", name: user.name || "You", state: status.label, detail: status.detail },
  ];

  return (
    <aside className="summary-panel glass">
      <div className="summary-header">
        <h2 className="summary-title">Activity</h2>
        <span className="summary-chip">{status.label}</span>
      </div>

      <div className="summary-list">
        {activity.map((item) => (
          <div className="file-block" key={item.id}>
            <div className="file-row">
              <div className="file-name">{item.name}</div>
              <div className="file-tag">{item.state}</div>
            </div>
            <pre className="code-box">{item.detail}</pre>
          </div>
        ))}
      </div>
    </aside>
  );
}
