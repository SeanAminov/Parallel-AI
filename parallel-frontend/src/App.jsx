import Sidebar from "./components/Sidebar";
import ChatFeed from "./components/ChatFeed";
import CommandBar from "./components/CommandBar";
import SummaryPanel from "./components/SummaryPanel";
import "./App.css";
import "./styles/globals.css";
import "./styles/layout.css";
import "./styles/chat.css";
import "./styles/neon.css";

function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="workspace">
        <header className="workspace__header">
          <div>
            <p className="eyebrow">Parallel workspace</p>
            <h1>Ship the demo together</h1>
            <p className="subhead">
              Route questions to teammates, keep shared memory in sync, and see
              what the team is doing at a glance.
            </p>
          </div>
          <div className="status-stack">
            <span className="status-pill online">Live</span>
            <span className="status-pill neutral">FastAPI backend ready</span>
            <span className="status-pill info">CORS open for localhost</span>
          </div>
        </header>

        <div className="workspace__body">
          <ChatFeed />
          <SummaryPanel />
        </div>

        <CommandBar />
      </main>
    </div>
  );
}

export default App;
