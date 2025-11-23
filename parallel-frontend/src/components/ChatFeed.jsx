import { useStream } from "../store/streamStore";

const modeLabel = {
  team: "Team ask",
  teammate: "Teammate",
  self: "Self",
};

const Message = ({ message }) => {
  const label = modeLabel[message.mode] || "Ask";
  return (
    <div className={`chat-message ${message.role}`}>
      <div className="chat-avatar">{message.sender[0]}</div>
      <div className="chat-body">
        <div className="chat-meta">
          <span className="chat-sender">{message.sender}</span>
          <span className="chat-time">{message.time}</span>
          <span className="chat-mode">{label}</span>
        </div>
        <p className="chat-text">{message.text}</p>
      </div>
    </div>
  );
};

function ChatFeed() {
  const { chat } = useStream();

  return (
    <section className="chat-feed">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Live collaboration</p>
          <h2>Conversation</h2>
        </div>
        <div className="chip">Streaming</div>
      </div>
      <div className="chat-scroll">
        {chat.map((message) => (
          <Message key={message.id} message={message} />
        ))}
      </div>
    </section>
  );
}

export default ChatFeed;
