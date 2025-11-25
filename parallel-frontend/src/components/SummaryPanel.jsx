import "./SummaryPanel.css";

const statusMap = {
  Chat: { label: "In chat", detail: "Responding to workspace asks." },
  Team: { label: "Team activity", detail: "Watching live team updates." },
  Inbox: { label: "Inbox review", detail: "Triaging routed tasks." },
  IDE: { label: "Development", detail: "Editing code in IDE mode." },
};

export default function SummaryPanel({ user = { name: "You" }, activeTool = "Chat", activityLog = [] }) {
  const status = statusMap[activeTool] || statusMap.Chat;
  const activity = activityLog.length
    ? activityLog
    : [{ id: "you", name: user.name || "You", state: status.label, detail: status.detail, at: "" }];
  const current = activity.reduce((acc, entry) => {
    if (!acc[entry.name]) acc[entry.name] = entry;
    return acc;
  }, {});

  return (
    <aside className="summary-panel glass">
      <div className="summary-header">
        <div>
          <h2 className="summary-title">Activity</h2>
          <p className="summary-subtitle">Signed in as {user.name || "You"}</p>
        </div>
        <span className="summary-chip">{status.label}</span>
      </div>

      <div className="summary-list">
        {Object.values(current).map((item) => (
          <div className="file-block" key={item.id}>
            <div className="file-row">
              <div className="file-name">{item.name}</div>
              <div className="file-tag">{item.state}</div>
            </div>
            <pre className="code-box">
              {item.detail}
              {item.at ? ` — ${item.at}` : ""}
            </pre>
          </div>
        ))}
      </div>

      <div className="activity-feed">
        {activity.map((item) => (
          <div className="activity-line" key={item.id}>
            [{item.at || "--:--"}] {item.name}: {item.detail}
          </div>
        ))}
      </div>
    </aside>
  );
}
