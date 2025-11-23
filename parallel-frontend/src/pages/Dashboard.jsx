import "./Dashboard.css";
import Sidebar from "../components/Sidebar";
import ChatPanel from "../components/ChatPanel";
import SummaryPanel from "../components/SummaryPanel";

export default function Dashboard() {
  return (
    <div className="dashboard-container">
      <Sidebar />
      <ChatPanel />
      <SummaryPanel />
    </div>
  );
}
