import { useStream } from "../store/streamStore";

function SummaryPanel() {
  const { summary, chat } = useStream();
  const latest = chat[chat.length - 1];

  return (
    <section className="summary-panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Shared memory</p>
          <h2>Team notes</h2>
        </div>
        <div className="chip warm">Append-only</div>
      </div>
      <p className="panel-copy">
        Captured by the coordinator so you do not lose context between requests.
      </p>

      <div className="summary-cards">
        {summary.map((item, idx) => (
          <article className="summary-card" key={item.id}>
            <div className="summary-index">#{idx + 1}</div>
            <p>{item.text}</p>
          </article>
        ))}
      </div>

      <div className="summary-footer">
        {latest
          ? `Last activity: ${latest.sender} at ${latest.time}`
          : "No activity yet; ask a question to warm things up."}
      </div>
    </section>
  );
}

export default SummaryPanel;
