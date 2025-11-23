import { useState } from "react";
import "./ChatPanel.css";
import ChatBubble from "./ChatBubble";
import TeamPanel from "./TeamPanel";
import TypingIndicator from "./TypingIndicator";

export default function ChatPanel() {
  const [messages, setMessages] = useState([
    { sender: "ai", text: "Hey Yug — how can I help today?" }
  ]);
  const [input, setInput] = useState("");
  const [typing, setTyping] = useState(false);

  function send() {
    if (!input.trim()) return;
    setMessages([...messages, { sender: "user", text: input }]);
    setInput("");
    setTyping(true);

    setTimeout(() => {
      setMessages(m => [...m, { sender: "ai", text: "Analyzing…" }]);
      setTyping(false);
    }, 900);
  }

  return (
    <div className="chat-wrapper">
      <TeamPanel />

      <div className="chat-scroll">
        {messages.map((m, i) => (
          <ChatBubble key={i} sender={m.sender} text={m.text} />
        ))}
        {typing && <TypingIndicator />}
      </div>

      <div className="input-container">
        <input
          className="chat-input"
          placeholder="Ask Parallel OS..."
          value={input}
          onChange={e => setInput(e.target.value)}
        />
        <button onClick={send} className="chat-send">Send</button>
      </div>
    </div>
  );
}
