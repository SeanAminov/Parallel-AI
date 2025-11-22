# main.py
import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    CLIENT_A,
    CLIENT_B,
    CLIENT_C,
    CLIENT_D,
    OPENAI_MODEL,
)

# ============================================================
# Data models
# ============================================================

class Message(BaseModel):
    sender_id: str           # e.g. "user:severin", "agent:A"
    sender_name: str         # "Severin", "Client A", etc.
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime

class RoomState(BaseModel):
    id: str
    name: str
    project_summary: str = ""
    messages: List[Message] = []

ROOMS: Dict[str, RoomState] = {}  # in-memory store (fine for hackathon)


class AgentProfile(BaseModel):
    agent_id: str
    display_name: str
    description: str
    speciality: str
    client_name: str  # "A", "B", "C", or "D"


AGENTS: Dict[str, AgentProfile] = {
    "A": AgentProfile(
        agent_id="A",
        display_name="Client A",
        description="You are Client A, one of four collaborating AI clients.",
        speciality="You provide perspective A on the project.",
        client_name="A",
    ),
    "B": AgentProfile(
        agent_id="B",
        display_name="Client B",
        description="You are Client B, one of four collaborating AI clients.",
        speciality="You provide perspective B on the project.",
        client_name="B",
    ),
    "C": AgentProfile(
        agent_id="C",
        display_name="Client C",
        description="You are Client C, one of four collaborating AI clients.",
        speciality="You provide perspective C on the project.",
        client_name="C",
    ),
}

# Client D is the coordinator / shared agent
COORDINATOR_PROFILE = AgentProfile(
    agent_id="D",
    display_name="Client D",
    description=(
        "You are Client D, the coordinating client. You read Clients A, B, and C "
        "and synthesize one clear answer and plan for the humans."
    ),
    speciality="Synthesis, prioritization, and planning.",
    client_name="D",
)

# ============================================================
# API schemas
# ============================================================

class CreateRoomRequest(BaseModel):
    room_name: str

class CreateRoomResponse(BaseModel):
    room_id: str
    room_name: str

class PostMessageRequest(BaseModel):
    user_id: str
    user_name: str
    content: str

class PostMessageResponse(BaseModel):
    room_id: str
    room_name: str
    project_summary: str
    messages: List[Message]


# ============================================================
# FastAPI app + CORS
# ============================================================

app = FastAPI(title="Parallel Clients A–D")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # relax for hackathon; tighten later if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Helper: choose correct OpenAI client by agent
# ============================================================

def get_client_for_agent(agent: AgentProfile):
    if agent.client_name == "A":
        return CLIENT_A
    if agent.client_name == "B":
        return CLIENT_B
    if agent.client_name == "C":
        return CLIENT_C
    if agent.client_name == "D":
        return CLIENT_D
    # fallback (should not happen)
    return CLIENT_A


# ============================================================
# Prompt builders
# ============================================================

def build_twin_prompt(
    agent: AgentProfile,
    room: RoomState,
    user_message: Message,
) -> List[Dict[str, str]]:
    """
    Build messages for Clients A, B, and C.
    They see:
      - their persona
      - the project summary
      - recent conversation
      - the latest human message
    """
    recent_msgs = room.messages[-12:]

    system_instructions = f"""
You are {agent.display_name}, one of four AI clients collaborating on this project.

Your persona:
- {agent.description}
- Your speciality: {agent.speciality}

You are working together with Clients A, B, C, and D.
Clients A, B, and C each provide a different perspective.
Client D is the coordinator who synthesizes your ideas.

You all share a single project memory.

CURRENT PROJECT SUMMARY (may be rough or outdated):
{room.project_summary if room.project_summary else "(no project summary yet; help define it as you go.)"}

Your goals:
- React to the latest human message from your own perspective.
- Propose concrete next steps in YOUR domain (2–5 bullets).
- Optionally suggest an updated project summary at the end:

SUMMARY_UPDATE:
<1–3 sentences that refine or replace the summary>

Keep responses focused and relatively short (under ~300 words).
"""

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_instructions}
    ]

    for m in recent_msgs:
        messages.append({
            "role": m.role,
            "content": f"{m.sender_name}: {m.content}",
        })

    messages.append({
        "role": "user",
        "content": f"Latest human message from {user_message.sender_name}:\n{user_message.content}",
    })

    return messages


def build_coordinator_prompt(
    room: RoomState,
    user_message: Message,
    twin_outputs: Dict[str, str],
) -> List[Dict[str, str]]:
    """
    Build messages for Client D (coordinator).
    It sees:
      - project summary
      - latest human message
      - A/B/C drafts
    and must create ONE unified answer.
    """

    system_instructions = f"""
You are {COORDINATOR_PROFILE.display_name}, the coordinating client (Client D).

You receive:
- The current project summary.
- The latest human message.
- Draft responses from:
  - Client A
  - Client B
  - Client C

Your job:
1. Synthesize their input into ONE clear, structured answer for the humans.
2. Resolve contradictions, highlight tradeoffs where relevant.
3. Propose a short, concrete plan (2–5 next steps).
4. Be practical and concise; avoid repeating the same idea three times.

If you think the project summary should be updated, include at the end:

SUMMARY_UPDATE:
<1–3 sentences that summarize the current project and direction>

The human team mostly sees YOUR response as the main answer.
"""

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_instructions},
        {
            "role": "system",
            "content": f"CURRENT PROJECT SUMMARY:\n{room.project_summary or '(none yet)'}",
        },
        {
            "role": "user",
            "content": f"Latest human message from {user_message.sender_name}:\n{user_message.content}",
        },
    ]

    label_map = {
        "A": "Client A",
        "B": "Client B",
        "C": "Client C",
    }

    for agent_id, text in twin_outputs.items():
        label = label_map.get(agent_id, f"Client {agent_id}")
        messages.append({
            "role": "assistant",
            "content": f"{label} draft response:\n{text}",
        })

    return messages


# ============================================================
# OpenAI call helpers
# ============================================================

def call_twin_agent(
    agent: AgentProfile,
    room: RoomState,
    user_message: Message,
) -> str:
    client = get_client_for_agent(agent)
    messages = build_twin_prompt(agent, room, user_message)

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.4,
    )
    return resp.choices[0].message.content


def call_coordinator_agent(
    room: RoomState,
    user_message: Message,
    twin_outputs: Dict[str, str],
) -> str:
    client = get_client_for_agent(COORDINATOR_PROFILE)
    messages = build_coordinator_prompt(room, user_message, twin_outputs)

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.35,
    )
    return resp.choices[0].message.content


# ============================================================
# Summary helpers
# ============================================================

def extract_summary_update(text: str) -> Optional[str]:
    marker = "SUMMARY_UPDATE:"
    if marker not in text:
        return None
    idx = text.index(marker)
    part = text[idx + len(marker):].strip()
    return part or None


def maybe_update_summary_from_twins(room: RoomState, twin_outputs: Dict[str, str]) -> None:
    # simple priority: A > B > C
    for agent_id in ["A", "B", "C"]:
        text = twin_outputs.get(agent_id, "") or ""
        new_summary = extract_summary_update(text)
        if new_summary:
            room.project_summary = new_summary
            return


def maybe_update_summary_from_coordinator(room: RoomState, coord_text: str) -> None:
    new_summary = extract_summary_update(coord_text)
    if new_summary:
        room.project_summary = new_summary


# ============================================================
# Routes
# ============================================================

@app.post("/rooms", response_model=CreateRoomResponse)
def create_room(payload: CreateRoomRequest):
    room_id = str(uuid.uuid4())
    room = RoomState(id=room_id, name=payload.room_name)
    ROOMS[room_id] = room
    return CreateRoomResponse(room_id=room_id, room_name=room.name)


@app.get("/rooms/{room_id}", response_model=PostMessageResponse)
def get_room(room_id: str):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return PostMessageResponse(
        room_id=room.id,
        room_name=room.name,
        project_summary=room.project_summary,
        messages=room.messages,
    )


@app.post("/rooms/{room_id}/message", response_model=PostMessageResponse)
def post_message(room_id: str, payload: PostMessageRequest):
    room = ROOMS.get(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # 1) human message
    user_msg = Message(
        sender_id=f"user:{payload.user_id}",
        sender_name=payload.user_name,
        role="user",
        content=payload.content,
        created_at=datetime.utcnow(),
    )
    room.messages.append(user_msg)

    # 2) Clients A, B, C
    twin_outputs: Dict[str, str] = {}
    for agent_id, agent in AGENTS.items():
        print(f"[room {room_id}] Calling {agent.display_name}...")
        reply_text = call_twin_agent(agent, room, user_msg)
        twin_outputs[agent_id] = reply_text

        agent_msg = Message(
            sender_id=f"agent:{agent_id}",
            sender_name=agent.display_name,
            role="assistant",
            content=reply_text,
            created_at=datetime.utcnow(),
        )
        room.messages.append(agent_msg)

    maybe_update_summary_from_twins(room, twin_outputs)

    # 3) Client D (coordinator)
    print(f"[room {room_id}] Calling Client D (coordinator)...")
    coord_text = call_coordinator_agent(room, user_msg, twin_outputs)
    coord_msg = Message(
        sender_id="agent:D",
        sender_name=COORDINATOR_PROFILE.display_name,
        role="assistant",
        content=coord_text,
        created_at=datetime.utcnow(),
    )
    room.messages.append(coord_msg)

    maybe_update_summary_from_coordinator(room, coord_text)

    return PostMessageResponse(
        room_id=room.id,
        room_name=room.name,
        project_summary=room.project_summary,
        messages=room.messages,
    )
