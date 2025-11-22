// src/App.jsx
import { useState } from "react";
import "./App.css";

import Landing from "./components/Landing";
import Dashboard from "./components/Dashboard";
import ThemeToggle from "./components/ThemeToggle";
import { createRoom } from "./api"; // <-- new

export default function App() {
  const [entered, setEntered] = useState(false);
  const [roomId, setRoomId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleEnter() {
    try {
      setBusy(true);
      setError("");
      const r = await createRoom("Dev Room"); // calls backend POST /rooms
      setRoomId(r.room_id);
      setEntered(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-container">
      {!entered ? (
        // Landing already supports onEnter; busy/error are optional
        <Landing onEnter={handleEnter} busy={busy} error={error} />
      ) : (
        <>
          <ThemeToggle />
          {/* pass roomId to Dashboard so it can poll/send */}
          <Dashboard roomId={roomId} />
        </>
      )}
    </div>
  );
}
