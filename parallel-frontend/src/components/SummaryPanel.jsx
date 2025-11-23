import "./SummaryPanel.css";

const files = [
  { name: "Dashboard.jsx", note: "UI layout optimized by Severin" },
  { name: "ChatPanel.jsx", note: "Added typing indicator + async queue" },
  { name: "index.jsx", note: "Mounted AppLayout + theme provider" },
];

export default function SummaryPanel() {
  return (
    <aside className="summary-panel glass">
      <div className="summary-header">
        <h2 className="summary-title">Recent Code Summary</h2>
        <span className="summary-chip">Live</span>
      </div>

      <div className="summary-list">
        {files.map((file) => (
          <div className="file-block" key={file.name}>
            <div className="file-row">
              <div className="file-name">{file.name}</div>
              <div className="file-tag">updated</div>
            </div>
            <pre className="code-box">{file.note}</pre>
          </div>
        ))}
      </div>
    </aside>
  );
}
