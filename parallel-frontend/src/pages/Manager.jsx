import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import "./Manager.css";
import {
  fetchTeam,
  listTasks,
  createTask,
  updateTaskStatus,
  pushTaskNotification,
} from "../lib/tasksApi";

export default function Manager({ currentUser = { id: "demo-user", name: "You" } }) {
  const [team, setTeam] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  // form state
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [assignee, setAssignee] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const [members, existing] = await Promise.all([fetchTeam(), listTasks()]);
      setTeam(members);
      setTasks(existing);
      setAssignee(members[0]?.id || "");
      setLoading(false);
    };
    load();
  }, []);

  const byMember = useMemo(() => {
    const map = {};
    for (const t of tasks) {
      map[t.assignee_id] = map[t.assignee_id] || [];
      map[t.assignee_id].push(t);
    }
    return map;
  }, [tasks]);

  const create = async () => {
    if (!title.trim() || !assignee) return;
    const task = await createTask({ title, description: desc, assignee_id: assignee });
    setTasks((prev) => [task, ...prev]);
    setTitle(""); setDesc("");
    // send a notification to the assignee (best-effort)
    await pushTaskNotification({ assignee_id: assignee, task });
  };

  const setStatus = async (taskId, status) => {
    const updated = await updateTaskStatus(taskId, status);
    setTasks((prev) => prev.map(t => t.id === taskId ? { ...t, status: updated.status } : t));
  };

  if (loading) {
    return (
      <div className="manager-wrap">
        <div className="manager-card"><div className="manager-heading"><div className="manager-title">Project Manager</div></div><div className="manager-list">Loading…</div></div>
        <div className="manager-pane"></div>
      </div>
    );
  }

  return (
    <div className="manager-wrap">
      {/* Left: Members + roles */}
      <div className="manager-card">
        <div className="manager-heading">
          <div className="manager-title">Team</div>
        </div>
        <div className="manager-list">
          {team.map(m => (
            <div key={m.id} className="member">
              <div>
                <div style={{fontWeight:700}}>{m.name}</div>
                <div className="roles">{(m.roles || ["—"]).join(", ")}</div>
              </div>
              <div className="roles">{m.status || "active"}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right: Create task + grid */}
      <div className="manager-pane" style={{display:"grid", gridTemplateRows:"auto 1fr"}}>
        <div className="manager-heading">
          <div className="manager-title">Tasks</div>
          <div style={{opacity:.7}}>Assign work to teammates</div>
        </div>

        <div style={{display:"grid", gridTemplateColumns:"360px 1fr", gap:16, padding:16}}>
          {/* Create Task */}
          <div className="manager-card" style={{padding:0}}>
            <div className="manager-heading"><div className="manager-title">Create Task</div></div>
            <div className="task-form">
              <input placeholder="Title" value={title} onChange={e=>setTitle(e.target.value)} />
              <textarea placeholder="Description / details" value={desc} onChange={e=>setDesc(e.target.value)} />
              <select value={assignee} onChange={e=>setAssignee(e.target.value)}>
                {team.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <button className="btn primary" onClick={create}>Create & Notify</button>
            </div>
          </div>

          {/* Task List */}
          <div className="manager-card" style={{padding:0, display:"grid", gridTemplateRows:"auto 1fr"}}>
            <div className="manager-heading">
              <div className="manager-title">All Tasks</div>
              <div className="roles">Newest first</div>
            </div>
            <div className="manager-list" style={{overflowY:"auto"}}>
              {tasks.length === 0 && <div>No tasks yet.</div>}
              {tasks.map(t => (
                <motion.div key={t.id} className="task-row" initial={{opacity:0,y:6}} animate={{opacity:1,y:0}}>
                  <div>
                    <div className="task-col-title">{t.title}</div>
                    <div className="roles">{t.description}</div>
                  </div>
                  <div className="task-col-status">{(team.find(m=>m.id===t.assignee_id)?.name)||"—"}</div>
                  <div className="task-actions">
                    <span className="roles" style={{alignSelf:"center"}}>{t.status || "new"}</span>
                    <button className="btn" onClick={()=>setStatus(t.id,"in_progress")}>In Progress</button>
                    <button className="btn" onClick={()=>setStatus(t.id,"complete")}>Complete</button>
                    <button className="btn" onClick={()=>setStatus(t.id,"report")}>Report</button>
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
