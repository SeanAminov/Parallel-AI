import { useEffect, useState } from "react";
import "./Dashboard.css";
import Sidebar from "../components/Sidebar";
import ChatPanel from "../components/ChatPanel";
import SummaryPanel from "../components/SummaryPanel";
import TeamPanel from "../components/TeamPanel";
import { GitTextEditorPanel } from "../features/ide/GitTextEditorPanel";

function TeamView({ user, statuses }) {
  return (
    <div className="chat-wrapper glass">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Live work</p>
          <h2>Team activity</h2>
        </div>
      </div>
      <TeamPanel user={user} statuses={statuses} />
      <p className="subhead">Updates stream here when Team is selected.</p>
    </div>
  );
}

function InboxView() {
  return (
    <div className="chat-wrapper glass">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Inbox</p>
          <h2>Captured tasks</h2>
        </div>
      </div>
      <p className="subhead">Tasks routed from chat will show here.</p>
    </div>
  );
}

function IdeView() {
  return <GitTextEditorPanel />;
}

export default function Dashboard() {
  const [activeTool, setActiveTool] = useState("Team");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [user, setUser] = useState({ id: "demo-user", name: "You" });
  const [activityLog, setActivityLog] = useState([]);
  const [teamStatuses, setTeamStatuses] = useState([]);
  const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000";

  useEffect(() => {
    const fetchMe = async () => {
      try {
        const res = await fetch(`${apiBase}/me`, { credentials: "include" });
        if (res.ok) {
          const data = await res.json();
          setUser({ id: data.id, name: data.name || "You" });
        }
      } catch (err) {
        // ignore; keep default
      }
    };
    fetchMe();
  }, [apiBase]);

  useEffect(() => {
    const label = activeTool === "IDE" ? "Development" : activeTool === "Inbox" ? "Inbox review" : activeTool === "Team" ? "Team activity" : "In chat";
    const entry = {
      id: `${Date.now()}`,
      state: label,
      detail: `Switched to ${activeTool}`,
      at: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      name: user.name || "You",
    };
    setActivityLog((prev) => [entry, ...prev].slice(0, 6));
    setTeamStatuses([
      { name: user.name || "You", role: label, state: "active" },
    ]);
  }, [activeTool, user.name]);

  const renderRight = () => {
    if (activeTool === "Team") return <TeamView user={user} statuses={teamStatuses} />;
    if (activeTool === "Inbox") return <InboxView />;
    if (activeTool === "IDE") return <IdeView />;
    return <SummaryPanel user={user} activeTool={activeTool} activityLog={activityLog} />;
  };

  return (
    <div className="dashboard-container">
      {sidebarOpen && <Sidebar active={activeTool} onSelect={setActiveTool} onToggle={() => setSidebarOpen(false)} />}
      {!sidebarOpen && (
        <button className="sidebar-toggle" onClick={() => setSidebarOpen(true)}>
          ☰
        </button>
      )}
      <ChatPanel user={user} />
      <SummaryPanel user={user} activeTool={activeTool} activityLog={activityLog} />
    </div>
  );
}
