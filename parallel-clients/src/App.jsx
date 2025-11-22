// src/App.jsx
import React, { useEffect, useState, useCallback } from "react";

const API_BASE = "http://localhost:8000";

export default function App() {
  const [roomId, setRoomId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [projectSummary, setProjectSummary] = useState("(no summary yet)");
  const [username, setUsername] = useState("Severin");
  const [input, setInput] = useState("");
  const [isBusy, setIsBusy] = useState(false);

  // Create a room on mount
  useEffect(() => {
    const createRoom = async () => {
      try {
        const resp = await fetch(`${API_BASE}/rooms`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ room_name: "Hackathon Room" }),
        });
        const data = await resp.json();
        setRoomId(data.room_id);
      } catch (err) {
        console.error("Error creating room:", err);
      }
    };

    createRoom();
  }, []);

  const renderMessages = useCallback(() => {
    return messages.map((m, idx) => {
      let cls = "msg";

      if (m.sender_id.startsWith("user:")) {
        cls += " user";
      } else if (m.sender_id === "agent:D") {
        cls += " agent-coordinator";
      } else if (m.sender_id.startsWith("agent:")) {
        cls += " agent-twin";
      }

      return (
        <div key={idx} className={cls}>
          <div className="sender">{m.sender_name}</div>
          <div className="content">{m.content}</div>
        </div>
      );
    });
  }, [messages]);

  const handleSend = async () => {
    if (!roomId || isBusy) return;
    const trimmed = input.trim();
    if (!trimmed) return;

    const name = username.trim() || "Anonymous";
    const userId = name.toLowerCase().replace(/\s+/g, "-");

    setIsBusy(true);

    try {
      const resp = await fetch(`${API_BASE}/rooms/${roomId}/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          user_name: name,
          content: trimmed,
        }),
      });

      const data = await resp.json();
      setMessages(data.messages || []);
      setProjectSummary(data.project_summary || "(no summary yet)");
      setInput("");
    } catch (err) {
      console.error("Error sending message:", err);
      alert("Error sending message. Check console.");
    } finally {
      setIsBusy(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="app-root">
      <aside className="sidebar">
        <div>
          <h1>Parallel Clients</h1>
          <div className="badge">
            <span className="badge-dot" />
            Clients A–D active
          </div>
        </div>

        <div>
          <h2 className="sidebar-heading">Project summary</h2>
          <div className="summary-box">{projectSummary}</div>
        </div>

        <div className="sidebar-footer">
          <strong>Clients:</strong>
          <ul>
            <li>Client A</li>
            <li>Client B</li>
            <li>Client C</li>
            <li>Client D (coordinator)</li>
          </ul>
        </div>
      </aside>

      <main className="main">
        <div className="chat" id="chat">
          {renderMessages()}
        </div>

        <div className="input-bar">
          <input
            id="username"
            placeholder="Your name"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <textarea
            id="message"
            placeholder="Ask the clients something..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button onClick={handleSend} disabled={isBusy || !roomId}>
            {isBusy ? "Thinking..." : "Send"}
          </button>
        </div>
      </main>
    </div>
  );
}
