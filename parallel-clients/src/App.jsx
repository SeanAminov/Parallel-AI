import "./App.css";
import Sidebar from "./components/Sidebar";
import UserPanel from "./components/UserPanel";
import CommandBar from "./components/CommandBar";
import CollabDrawer from "./components/CollabDrawer";
import PresenceBar from "./components/PresenceBar";

export default function App() {
  return (
    <div className="app-container">
      <Sidebar />

      <div className="main-area">
        <PresenceBar />

        <div className="panels-grid">
          <UserPanel name="Yug" isSelf />
          <UserPanel name="Sean" />
          <UserPanel name="Severin" />
        </div>

        <CollabDrawer />
        <CommandBar />
      </div>
    </div>
  );
}
