import { useMemo } from "react";
import { useStream } from "../store/streamStore";

const rooms = [
  { id: "launch", name: "Launch Week", active: true },
  { id: "memory", name: "Memory QA", active: false },
  { id: "infra", name: "Infra + Deploy", active: false },
];

const teammates = [
  { id: "yug", name: "Yug", status: "Typing reply" },
  { id: "sean", name: "Sean", status: "Deploying backend" },
  { id: "severin", name: "Severin", status: "Prioritizing asks" },
  { id: "nayab", name: "Nayab", status: "Coordinating memory" },
];

function Sidebar() {
  const { summary } = useStream();

  const memoryCount = useMemo(() => summary.length, [summary]);
  const fill = Math.min(100, Math.max(12, memoryCount * 12));

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="brand-mark">||</div>
        <div>
          <div className="brand-title">Parallel</div>
          <div className="brand-subtitle">AI workspace</div>
        </div>
      </div>

      <div className="sidebar__section">
        <p className="section-label">Rooms</p>
        <div className="pill-group">
          {rooms.map((room) => (
            <button
              key={room.id}
              type="button"
              className={`pill ${room.active ? "active" : ""}`}
            >
              {room.name}
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar__section">
        <p className="section-label">Team presence</p>
        <div className="presence-list">
          {teammates.map((mate) => (
            <div className="presence-row" key={mate.id}>
              <div className="presence-avatar">{mate.name[0]}</div>
              <div>
                <div className="presence-name">{mate.name}</div>
                <div className="presence-status">{mate.status}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="sidebar__section memory-block">
        <p className="section-label">Shared memory</p>
        <p className="memory-copy">
          {memoryCount} notes captured; append-only and synced to backend.
        </p>
        <div className="memory-meter">
          <div className="memory-fill" style={{ width: `${fill}%` }} />
        </div>
        <div className="memory-foot">Ask memory: "What changed in the last hour?"</div>
      </div>
    </aside>
  );
}

export default Sidebar;
