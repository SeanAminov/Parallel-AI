import "./TeamPanel.css";

export default function TeamPanel() {
  return (
    <div className="team-panel glass">
      <div className="team-member">
        <div className="status-dot active"></div>
        <span>Sean — UI work</span>
      </div>

      <div className="team-member">
        <div className="status-dot idle"></div>
        <span>Severin — Routing</span>
      </div>

      <div className="team-member">
        <div className="status-dot active"></div>
        <span>Yug — Agent Logic</span>
      </div>
    </div>
  );
}
