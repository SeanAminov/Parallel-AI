import "./Sidebar.css";
import ThemeToggle from "./ThemeToggle";

export default function Sidebar() {
  return (
    <div className="sidebar glass">
      <div className="logo">Parallel OS</div>

      <div className="menu">
        <div className="menu-item">Dashboard</div>
        <div className="menu-item">Chat</div>
        <div className="menu-item">Team</div>
        <div className="menu-item">Code Summary</div>
      </div>

      <ThemeToggle />
    </div>
  );
}
