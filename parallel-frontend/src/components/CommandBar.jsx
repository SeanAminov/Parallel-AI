import { useState } from "react";
import { useStream } from "../store/streamStore";

const modes = [
  { id: "team", label: "Team", hint: "Route to all teammates" },
  { id: "teammate", label: "Teammate", hint: "Tap a single teammate" },
  { id: "self", label: "Self check", hint: "Log to memory" },
];

const quickPrompts = [
  "Summarize the last 3 messages",
  "What should we ship for the demo?",
  "Ask Yug to tighten the UI spacing",
];

function CommandBar() {
  const [mode, setMode] = useState("team");
  const [value, setValue] = useState("");
  const { addMessage } = useStream();

  const submit = (evt) => {
    evt.preventDefault();
    addMessage(value, mode);
    setValue("");
  };

  return (
    <section className="command-bar">
      <div className="panel-head">
        <div>
          <p className="eyebrow">Command bar</p>
          <h2>Ask Parallel</h2>
        </div>
        <div className="chip subtle">Cmd + Enter to send</div>
      </div>

      <form className="command-form" onSubmit={submit}>
        <div className="mode-toggle">
          {modes.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`mode-pill ${mode === item.id ? "active" : ""}`}
              onClick={() => setMode(item.id)}
            >
              <span>{item.label}</span>
              <small>{item.hint}</small>
            </button>
          ))}
        </div>

        <div className="command-input">
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Ask a teammate, or query shared memory..."
          />
          <button type="submit">Send</button>
        </div>

        <div className="prompt-row">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="prompt-chip"
              onClick={() => setValue(prompt)}
            >
              {prompt}
            </button>
          ))}
        </div>
      </form>
    </section>
  );
}

export default CommandBar;
