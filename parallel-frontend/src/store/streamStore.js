import { create } from "zustand";

const now = () =>
  new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

const seedChat = [
  {
    id: "msg-1",
    sender: "Severin",
    role: "user",
    text: "Can we pull the Parallel workspace together for the demo?",
    mode: "team",
    time: "09:12",
  },
  {
    id: "msg-2",
    sender: "Yug",
    role: "assistant",
    text: "I'll own the frontend canvas and command bar. Expect a pass in 30m.",
    mode: "teammate",
    time: "09:13",
  },
  {
    id: "msg-3",
    sender: "Sean",
    role: "assistant",
    text: "Backend routes are live: /rooms, /ask, /memory. CORS is open for localhost.",
    mode: "self",
    time: "09:15",
  },
  {
    id: "msg-4",
    sender: "Nayab",
    role: "assistant",
    text: "I'll keep memory summarized. Ping me if you want a fresh rollup.",
    mode: "team",
    time: "09:16",
  },
];

const seedSummary = [
  { id: "note-1", text: "Project: Parallel workspace with shared memory and ask modes." },
  { id: "note-2", text: "Frontend: layout = sidebar + chat feed + summary rail + command bar." },
  { id: "note-3", text: "Backend: FastAPI provides /rooms, /ask, /memory endpoints with CORS open." },
];

export const useStream = create((set) => ({
  chat: seedChat,
  summary: seedSummary,

  addMessage: (text, mode = "team") =>
    set((state) => {
      if (!text?.trim()) return state;

      const timestamp = now();
      const id = `msg-${Date.now()}`;
      const userMessage = {
        id,
        sender: "You",
        role: "user",
        text: text.trim(),
        mode,
        time: timestamp,
      };

      const modeMap = {
        team: "Team synthesis in progress. Coordinator will draft a unified reply.",
        teammate: "Routed to the teammate you tagged. Expect a focused answer.",
        self: "Treating this as a self-check. Logging it to memory.",
      };

      const acknowledgement = {
        id: `${id}-ack`,
        sender: mode === "team" ? "Coordinator" : "Agent",
        role: "assistant",
        text: modeMap[mode] || "Noted. Capturing this ask for the group.",
        mode,
        time: timestamp,
      };

      return {
        chat: [...state.chat, userMessage, acknowledgement],
        summary: [
          ...state.summary,
          { id: `note-${Date.now()}`, text: `Captured (${mode}) ask: ${text.trim()}` },
        ],
      };
    }),
}));
