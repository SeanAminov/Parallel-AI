// src/api.js
const API = import.meta.env.VITE_API_BASE;

export async function createRoom(room_name = "Dev Room") {
  const r = await fetch(`${API}/rooms`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room_name }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getRoom(room_id) {
  const r = await fetch(`${API}/rooms/${room_id}`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

// Ask with routing: mode = "self" | "teammate" | "team"
// For self/teammate, include target_agent: "yug" | "sean" | "severin" | "nayab"
export async function ask(room_id, payload) {
  const r = await fetch(`${API}/rooms/${room_id}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getMemory(room_id) {
  const r = await fetch(`${API}/rooms/${room_id}/memory`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function queryMemory(room_id, question, user_name = "User") {
  const r = await fetch(`${API}/rooms/${room_id}/memory/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, user_name }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
