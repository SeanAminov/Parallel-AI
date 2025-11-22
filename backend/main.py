# backend/main.py
import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import CLIENTS, OPENAI_MODEL
from openai import OpenAI

# ============================================================
# Data models / in-memory store (hackathon simple)
# ============================================================

class Message(BaseModel):
    id: str
    sender_id: str           # e.g. "user:severin", "agent:yug"
    sender_name: str         # "Severin", "Yug", etc.
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime

class RoomState(BaseModel):
    id: str
    name: str
    project_summary: str = ""
    messages: List[Message] = []
    # shared memory (not auto-shown; only used when asked)
    memory_summary: str = ""              # 1–3 sentence rolling summary
    memory_notes: List[str] = []          # append-only log of important notes

ROOMS: Dict[str, RoomState] = {}

TEAM = [
    {"id": "yug",     "name": "Yug"},
    {"id": "sean",    "name": "Sean"},
    {"id": "severin", "name": "Severin"},
    {"id": "nayab",   "name": "Nayab"},
]

# ============================================================
# API schemas
# ============================================================

class CreateRoomRequest(BaseModel):
    room_name: str

class CreateRoomResponse(BaseModel):
    room_id: str
    room_name: str

class AskModeRequest(BaseModel):
    user_id: str
    user_name: str
    content: str
    mode: Literal["self", "teammate", "team"] = "self"
    target_agent: Optional[Literal["yug","sean","severin","nayab"]] = None  # used for self/teammate

class RoomResponse(BaseModel):
    room_id: str
    room_name: str
    project_summary: str
    memory_summary: str
    memory_count: int
    messages: List[Message]

class MemoryQueryRequest(BaseModel):
    question: str
    user_name: str = "System"

# ============================================================
# FastAPI app + CORS
# ============================================================

app = FastAPI(title="Parallel Workspace with Shared Memory")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # open for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Helpers
# ============================================================

def client_for(agent_id: str) -> OpenAI:
    if agent_id not in CLIENTS:
        raise HTTPException(400, f"Unknown agent '{agent_id}'")
    return CLIENTS[agent_id]

def summary_update_from(text: str) -> Optional[str]:
    marker = "SUMMARY_UPDATE:"
    if marker not in text:
        return None
    return text.split(marker, 1)[1].strip() or None

def make_assistant_msg(agent_id: str, agent_name: str, content: str) -> Message:
    return Message(
        id=str(uuid.uuid4()),
        sender_id=f"agent:{agent_id}",
        sender_name=agent_name,
        role="assistant",
        content=content,
        created_at=datetime.utcnow(),
    )

def append_memory_note(room: RoomState, note: str) -> None:
    room.memory_notes.append(f"[{datetime.utcnow().isoformat(timespec='seconds')}] {note}")

def build_system_context(room: RoomState) -> str:
    # memory_summary is concise; memory_notes is only summarized when asked
    return f"""Shared Memory Summary (not auto-shown to users unless asked):
{room.memory_summary or "(empty yet)"}

Team members:
- Yug (Frontend)
- Sean (Backend)
- Severin (Full stack/PM)
- Nayab (Coordination & Infra)

Guidelines:
- When answering, you may rely on the summary above to know what teammates are doing.
- Do not interrupt or change others' work unless asked; offer handoff steps or integration tips instead.
- If you think the memory summary should be updated, include at the end:

SUMMARY_UPDATE:
<1–3 sentences>
"""

def chat(client: OpenAI, messages: List[Dict[str, str]], temperature=0.4) -> str:
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content

# ============================================================
# Routes
# ============================================================

@app.post("/rooms", response_model=CreateRoomResponse)
def create_room(payload: CreateRoomRequest):
    room_id = str(uuid.uuid4())
    room = RoomState(id=room_id, name=payload.room_name)
    ROOMS[room_id] = room
    return CreateRoomResponse(room_id=room_id, room_name=room.name)

@app.get("/rooms/{room_id}", response_model=RoomResponse)
def get_room(room_id: str):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomResponse(
        room_id=room.id,
        room_name=room.name,
        project_summary=room.project_summary,
        memory_summary=room.memory_summary,
        memory_count=len(room.memory_notes),
        messages=room.messages,
    )

@app.post("/rooms/{room_id}/ask", response_model=RoomResponse)
def ask(room_id: str, payload: AskModeRequest):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # 1) store human message
    human = Message(
        id=str(uuid.uuid4()),
        sender_id=f"user:{payload.user_id}",
        sender_name=payload.user_name,
        role="user",
        content=payload.content,
        created_at=datetime.utcnow(),
    )
    room.messages.append(human)

    sys_ctx = build_system_context(room)

    # 2) routing
    if payload.mode in ("self","teammate"):
        # target agent required
        agent_id = payload.target_agent or "yug"
        agent_name = next((m["name"] for m in TEAM if m["id"] == agent_id), agent_id.title())

        msgs = [
            {"role":"system","content": sys_ctx},
            {"role":"user","content": f"{payload.user_name} asks {agent_name}:\n{payload.content}"},
        ]
        text = chat(client_for(agent_id), msgs, temperature=0.35)
        room.messages.append(make_assistant_msg(agent_id, agent_name, text))

        # update project/memory summaries if suggested
        if (upd := summary_update_from(text)):
            room.project_summary = upd
            room.memory_summary  = upd
            append_memory_note(room, f"{agent_name} updated summary.")

    else:  # mode == "team"
        # All teammates draft; Nayab synthesizes
        drafts: Dict[str,str] = {}
        for member in ["yug","sean","severin","nayab"]:
            agent_name = next((m["name"] for m in TEAM if m["id"] == member), member.title())
            msgs = [
                {"role":"system","content": sys_ctx},
                {"role":"system","content": f"You are {agent_name}. Provide your perspective."},
                {"role":"user","content": f"Team question from {payload.user_name}:\n{payload.content}"},
            ]
            drafts[member] = chat(client_for(member), msgs, temperature=0.4)
            room.messages.append(make_assistant_msg(member, agent_name, drafts[member]))

        # coordinator synthesis (use Nayab key)
        coord_msgs = [
            {"role":"system","content": "You are the coordinator. Synthesize drafts into one clear answer with 2–5 next steps."},
            {"role":"system","content": f"CURRENT PROJECT SUMMARY:\n{room.project_summary or '(none)'}"},
            {"role":"system","content": sys_ctx},
            {"role":"user","content": f"Latest human message from {payload.user_name}:\n{payload.content}"},
        ]
        for who, text in drafts.items():
            label = next((m["name"] for m in TEAM if m["id"] == who), who.title())
            coord_msgs.append({"role":"assistant","content": f"{label} draft:\n{text}"})

        synth = chat(client_for("coordinator"), coord_msgs, temperature=0.35)
        room.messages.append(make_assistant_msg("coordinator","Coordinator", synth))

        if (upd := summary_update_from(synth)):
            room.project_summary = upd
            room.memory_summary  = upd
            append_memory_note(room, "Coordinator updated summary.")

    return RoomResponse(
        room_id=room.id,
        room_name=room.name,
        project_summary=room.project_summary,
        memory_summary=room.memory_summary,
        memory_count=len(room.memory_notes),
        messages=room.messages,
    )

@app.get("/rooms/{room_id}/memory")
def get_memory(room_id: str):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    # Return summary + last 20 notes
    return {
        "memory_summary": room.memory_summary,
        "notes": room.memory_notes[-20:],
        "count": len(room.memory_notes),
    }

@app.post("/rooms/{room_id}/memory/query")
def query_memory(room_id: str, payload: MemoryQueryRequest):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    # Simple QA over memory_summary + notes (concatenate for now)
    context = room.memory_summary + "\n\n" + "\n".join(room.memory_notes[-200:])
    msgs = [
        {"role":"system","content":"You are the project memory. Answer using only the provided memory context."},
        {"role":"system","content": f"MEMORY CONTEXT:\n{context or '(empty)'}"},
        {"role":"user","content": f"{payload.user_name} asks: {payload.question}"},
    ]
    answer = chat(client_for("coordinator"), msgs, temperature=0.2)
    append_memory_note(room, f"Memory was queried: {payload.question}")
    return {"answer": answer}
