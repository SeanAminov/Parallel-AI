import { useEffect, useState } from "react";
import { listMyNotifications, updateTaskStatus } from "../lib/tasksApi";

export default function NotificationsPanel({ user }) {
  const [items, setItems] = useState([]);

  useEffect(() => {
    let canceled = false;
    const load = async () => {
      const res = await listMyNotifications(user.id);
      if (!canceled) setItems(res);
    };
    load();
    const id = setInterval(load, 6000);
    return () => { canceled = true; clearInterval(id); };
  }, [user.id]);

  const act = async (taskId, status) => {
    await updateTaskStatus(taskId, status);
  };

  if (!items.length) return null;

  return (
    <div className="glass" style={{padding:14, borderRadius:"var(--radius)", border:"1px solid var(--border)"}}>
      <div style={{fontWeight:700, marginBottom:8}}>Notifications</div>
      {items.map(n => (
        <div key={n.id} style={{border:"1px solid var(--border)", borderRadius:"var(--radius-sm)", padding:10, marginBottom:8}}>
          <div style={{fontWeight:600}}>{n.title || "Task Assigned"}</div>
          <div style={{opacity:.8, fontSize:13, margin:"6px 0"}}>{n.message}</div>
          {n.task_id && (
            <div style={{display:"flex", gap:8}}>
              <button className="btn" onClick={()=>act(n.task_id, "in_progress")}>Mark In Progress</button>
              <button className="btn" onClick={()=>act(n.task_id, "complete")}>Complete</button>
              <button className="btn" onClick={()=>act(n.task_id, "report")}>Report</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
