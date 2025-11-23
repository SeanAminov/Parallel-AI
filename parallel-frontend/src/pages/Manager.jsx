import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import "./Manager.css";
import {
  fetchTeam,
  listTasks, // keep "all tasks" view; swap to listTasksByUser if you add it
  createTask,
  updateTaskStatus,
  pushTaskNotification,
} from "../lib/tasksApi";
import { useTasks } from "../context/TaskContext";

export default function Manager({ currentUser = { id: "demo-user", name: "You" } }) {
  const [team, setTeam] = useState([]);
  const { tasks, setTasks } = useTasks();
  const [loading, setLoading] = useState(true);

  // permissions (UI-only placeholder)
  const [permissions, setPermissions] = useState({}); // { [userId]: { frontend: bool, backend: bool } }

  // form state
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [assignee, setAssignee] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const [members, existing] = await Promise.all([fetchTeam(), listTasks()]);
      setTeam(members || []);
      setTasks(existing || []);
      setAssignee((members && members[0]?.id) || "");

      // seed default permissions per member (both checked)
      setPermissions(prev => {
        const next = { ...prev };
        for (const m of members || []) {
          if (!next[m.id]) next[m.id] = { frontend: true, backend: true };
        }
        return next;
      });

      setLoading(false);
    };
    load();
  }, [setTasks]);

  const togglePerm = (userId, key) => {
    setPermissions(prev => ({
      ...prev,
      [userId]: { ...prev[userId], [key]: !prev[userId]?.[key] }
    }));
  };

  const create = async () => {
    if (!title.trim() || !assignee) return;
    const task = await createTask({ title, description: desc, assignee_id: assignee });
    setTasks(prev => [task, ...prev]);
    setTitle("");
    setDesc("");
    // best-effort notification
    try { await pushTaskNotification({ assignee_id: assignee, task }); } catch {}
  };

  const setStatus = async (taskId, status) => {
    const updated = await updateTaskStatus(taskId, status);
    setTasks(prev => prev.map(t => (t.id === taskId ? { ...t, status: updated.status } : t)));
  };

  if (loading) {
    return (
      <div className="manager-wrap">
        <div className="manager-card">
          <div className="manager-heading">
            <div className="manager-title">Project Manager</div>
          </div>
          <div className="manager-list">Loading…</div>
        </div>
        <div className="manager-pane" />
      </div>
    );
  }

  return (
    <div className="manager-wrap">
      {/* Left: Team + Roles + Permissions (UI only) */}
      <div className="manager-card">
        <div className="manager-heading">
          <div className="manager-title">Team</div>
        </div>
        <div className="manager-list">
          {team.length === 0 && <div>No teammates yet.</div>}
          {team.map(m => (
            <div key={m.id} className="member">
              <div style={{ width: "100%" }}>
                <div style={{ fontWeight: 700 }}>{m.name}</div>
                <div className="roles">{(m.roles || ["—"]).join(", ")}</div>

                {/* Permissions placeholder (not persisted) */}
                <div className="perm-row">
                  <label>
                    <input
                      type="checkbox"
                      checked={permissions[m.id]?.frontend ?? true}
                      onChange={() => togglePerm(m.id, "frontend")}
                    />
                    Frontend
                  </label>
                  <label>
                    <input
                      type="checkbox"
                      checked={permissions[m.id]?.backend ?? true}
                      onChange={() => togglePerm(m.id, "backend")}
                    />
                    Backend
                  </label>
                </div>
              </div>
              <div className="roles">{m.status || "active"}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right: Tasks */}
      <div className="manager-pane" style={{ display: "grid", gridTemplateRows: "auto 1fr" }}>
        <div className="manager-heading">
          <div className="manager-title">Tasks</div>
          <div style={{ opacity: 0.7 }}>Assign work to teammates</div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 16, padding: 16 }}>
          {/* Create Task */}
          <div className="manager-card" style={{ padding: 0 }}>
            <div className="manager-heading">
              <div className="manager-title">Create Task</div>
            </div>
            <div className="task-form">
              <input
                placeholder="Title"
                value={title}
                onChange={e => setTitle(e.target.value)}
              />
              <textarea
                placeholder="Description / details"
                value={desc}
                onChange={e => setDesc(e.target.value)}
              />
              <select value={assignee} onChange={e => setAssignee(e.target.value)}>
                {team.map(m => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
              <button className="btn primary" onClick={create}>
                Create & Notify
              </button>
            </div>
          </div>

          {/* Task List */}
          <div className="manager-card" style={{ padding: 0, display: "grid", gridTemplateRows: "auto 1fr" }}>
            <div className="manager-heading">
              <div className="manager-title">All Tasks</div>
              <div className="roles">Newest first</div>
            </div>
            <div className="manager-list" style={{ overflowY: "auto" }}>
              {tasks.length === 0 && <div>No tasks yet.</div>}
              {tasks.map(t => (
                <motion.div
                  key={t.id}
                  className="task-row"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  <div>
                    <div className="task-col-title">{t.title}</div>
                    <div className="roles">{t.description}</div>
                  </div>
                  <div className="task-col-status">
                    {(team.find(m => m.id === t.assignee_id)?.name) || "—"}
                  </div>
                  <div className="task-actions">
                    <span className="roles" style={{ alignSelf: "center" }}>
                      {t.status || "new"}
                    </span>
                    <button className="btn" onClick={() => setStatus(t.id, "in_progress")}>
                      In Progress
                    </button>
                    <button className="btn" onClick={() => setStatus(t.id, "complete")}>
                      Complete
                    </button>
                    <button className="btn" onClick={() => setStatus(t.id, "report")}>
                      Report
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
