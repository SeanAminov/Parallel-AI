import "./SummaryPanel.css";

export default function SummaryPanel() {
  return (
    <div className="summary-panel glass">
      <h2 className="summary-title">Recent Code Summary</h2>

      <div className="file-block">
        <div className="file-name">Dashboard.jsx</div>
        <pre className="code-box">UI layout optimized by Severin</pre>
      </div>

      <div className="file-block">
        <div className="file-name">ChatPanel.jsx</div>
        <pre className="code-box">Added typing indicator + async queue</pre>
      </div>

      <div className="file-block">
        <div className="file-name">index.jsx</div>
        <pre className="code-box">Mounted AppLayout + theme provider</pre>
      </div>
    </div>
  );
}
