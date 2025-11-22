// src/components/Dashboard.jsx
import { useEffect, useMemo, useState } from "react";
import Background3D from "./Background3D";
import Sidebar from "./Sidebar";
import FloatingAvatars from "./FloatingAvatars";
import UserPanel from "./UserPanel";
import CommandBar from "./CommandBar";
import { getRoom, ask, getMemory, queryMemory } from "../api";

export default function Dashboard({ roomId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);

  const [mode, setMode] = useState("team");             // "self" | "teammate" | "team"
  const [teammate, setTeammate] = useState("yug");      // when self/teammate
  const [memory, setMemory] = useState({ memory_summary: "", notes: [], count: 0 });
  const userId = "severin";   // demo user id
  const userName = "Severin"; // demo name

  // Poll room + memory every 1.5s
  useEffect(() => {
    if (!roomId) return;
    let timer;
    async function tick() {
      try {
        const r = await getRoom(roomId);
        setMessages(r.messages ?? []);
        const mem = await getMemory(roomId);
        setMemory(mem);
      } catch (e) {
        console.error(e);
      }
    }
    tick();
    timer = setInterval(tick, 1500);
    return () => clearInterval(timer);
  }, [roomId]);

  async function send() {
    const content = input.trim();
    if (!content || !roomId) return;
    setSending(true);
    setInput("");
    try {
      await ask(roomId, {
        user_id: userId,
        user_name: userName,
        content,
        mode,
        target_agent: mode === "team" ? undefined : teammate,
      });
      // next poll will refresh
    } catch (e) {
      console.error(e);
      setInput(content); // restore on failure
    } finally {
      setSending(false);
    }
  }

  async function askMemory() {
    const q = prompt("Ask the shared memory:");
    if (!q) return;
    try {
      const { answer } = await queryMemory(roomId, q, userName);
      alert(answer);
    } catch (e) {
      alert("Memory query failed. See console.");
      console.error(e);
    }
  }

  const latestAssistant =
    [...messages].reverse().find((m) => m.role === "assistant")?.content || "";

  const transcript = useMemo(
    () => messages.map((m) => `${m.sender_name}: ${m.content}`).join("\n\n"),
    [messages]
  );

  return (
    <div style={{ height: "100vh", display: "flex", position: "relative", overflow: "hidden" }}>
      <Background3D />
      <Sidebar />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", position: "relative" }}>
        <FloatingAvatars />

        {/* Memory summary */}
        <div
          className="glass"
          style={{
            margin: "8px 32px 0 32px", padding: "14px", borderRadius: "12px",
            border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.04)",
            display: "flex", justifyContent: "space-between", gap: 12,
          }}
        >
          <div style={{ whiteSpace: "pre-wrap", fontSize: 14 }}>
            <b>Shared Memory:</b> {memory.memory_summary || "(empty—ask team to propose a summary)"}
          </div>
          <button onClick={askMemory} style={{ padding: "8px 12px", borderRadius: 10 }}>
            Ask Memory
          </button>
        </div>

        {/* Transcript */}
        <div
          className="glass"
          style={{
            margin: "8px 32px 0 32px", padding: "14px", borderRadius: "12px",
            border: "1px solid rgba(255,255,255,0.08)", background: "rgba(255,255,255,0.04)",
            whiteSpace: "pre-wrap", maxHeight: 220, overflowY: "auto", fontSize: 14,
          }}
        >
          {transcript || "No messages yet…"}
        </div>

        {/* Panels */}
        <div
          style={{
            flex: 1, display: "grid", gap: "24px",
            padding: "24px 32px 100px 32px",
            gridTemplateColumns: "repeat(auto-fill, minmax(380px, 1fr))",
            overflowY: "auto",
          }}
        >
          <UserPanel name="Yug (Frontend)"     latestText={latestAssistant} />
          <UserPanel name="Sean (Backend)"      latestText={latestAssistant} />
          <UserPanel name="Severin (PM/FS)"     latestText={latestAssistant} />
          <UserPanel name="Nayab (Coord/Infra)" latestText={latestAssistant} />
        </div>

        <CommandBar
          value={input}
          onChange={setInput}
          onRun={send}
          disabled={!roomId || sending}
          mode={mode}
          setMode={setMode}
          teammate={teammate}
          setTeammate={setTeammate}
        />
      </div>
    </div>
  );
}
