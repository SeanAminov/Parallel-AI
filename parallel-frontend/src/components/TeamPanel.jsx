import "./TeamPanel.css";

const statusColor = {
  active: "active",
  idle: "idle",
  offline: "offline",
};

export default function TeamPanel({ user = { name: "You" }, statuses = [] }) {
  const members = statuses.length
    ? statuses
    : [
        { name: user.name || "You", role: "In chat", state: "active" },
        { name: "Coordinator", role: "Orchestrating replies", state: "idle" },
      ];

  return (
    <div className="team-panel glass">
      {members.map((m) => (
        <div className="team-member" key={m.name}>
          <div className={`status-dot ${statusColor[m.state] || "idle"}`}></div>
          <span>{`${m.name} — ${m.role}`}</span>
        </div>
      ))}
    </div>
  );
}
