import ThemeToggle from "./ThemeToggle";
import logo from "../assets/parallel-logo.svg"; 
import "./Sidebar.css";

export default function Sidebar() {
  return (
    <div className="sidebar glass">

      <div className="sidebar-header">
        <img src={logo} alt="Parallel Logo" className="sidebar-logo" />
      </div>

      <div className="sidebar-links">
        <p>Dashboard</p>
        <p>Chat</p>
        <p>Team</p>
        <p>Code</p>
      </div>

      <ThemeToggle />
    </div>
  );
}
