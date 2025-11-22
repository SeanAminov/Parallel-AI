import { create } from "zustand";

export const useStream = create((set) => ({
  chat: [],
  summary: [],

  addMessage: (text) =>
    set((s) => ({
      chat: [...s.chat, { id: Date.now(), sender: "user", text }],
      summary: [
        ...s.summary,
        { id: Date.now(), text: `User asked: "${text}"` }
      ]
    })),
}));
