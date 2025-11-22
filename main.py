# main.py
import uuid
from datetime import datetime
from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from config import (
    CLIENT_A,
    CLIENT_B,
    CLIENT_C,
    CLIENT_D,
    OPENAI_MODEL_TWIN,
    OPENAI_MODEL_COORDINATOR,
)

# ============================================================
# Data models
# ============================================================

class Message(BaseModel):
    sender_id: str           # e.g. "user:severin", "agent:quant"
    sender_name: str         # "Severin", "Quant Twin", etc.
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
    client_name: str  # which OpenAI client to use


AGENTS: Dict[str, AgentProfile] = {
    "quant": AgentProfile(
        agent_id="quant",
        display_name="Quant Twin",
        description="You are the quant & modeling AI twin. Focus on trading logic, risk, modeling, and numerics.",
        speciality="Quant research, trading systems, ML models.",
        client_name="quant",
    ),
    "backend": AgentProfile(
        agent_id="backend",
        display_name="Backend Twin",
        description="You are the backend & infra AI twin. Own APIs, data stores, services, security, devops.",
        speciality="APIs, infra, databases, deployment.",
        client_name="backend",
    ),
    "frontend": AgentProfile(
        agent_id="frontend",
        display_name="Frontend Twin",
        description="You are the frontend & UX AI twin. Design UI, flows, components, and copy.",
        speciality="React, UX, product thinking.",
        client_name="frontend",
    ),
}

# Coordinator (shared agent)
COORDINATOR_PROFILE = AgentProfile(
    agent_id="coordinator",
    display_name="Project Copilot",
    description=(
        "You are the coordinating AI that synthesizes the three twins' ideas "
        "into one clear plan and answer for the humans."
    ),
    speciality="Synthesis, prioritization, breaking work into concrete steps.",
    client_name="coordinator",
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
# FastAPI app
# ============================================================

app = FastAPI(title="Shared Trio Project Copilot")


# ============================================================
# Helper: choose correct OpenAI client by agent
# ============================================================

def get_client_for_agent(agent: AgentProfile):
    if agent.client_name == "quant":
        return CLIENT_A
    if agent.client_name == "backend":
        return CLIENT_B
    if agent.client_name == "frontend":
        return CLIENT_C
    if agent.client_name == "coordinator":
        return CLIENT_D
    # Fallback if misconfigured (shouldn't happen)
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
    Build messages for a specialist twin (quant/backend/frontend).
    They see:
      - their persona
      - the project summary
      - recent conversation
      - the latest human message
    """
    # Take last N messages for context
    recent_msgs = room.messages[-12:]

    system_instructions = f"""
You are {agent.display_name}, one of three specialist AI twins working on this project.

Your persona:
- {agent.description}
- Your speciality: {agent.speciality}

You are collaborating with:
- Quant Twin
- Backend Twin
- Frontend Twin

You operate within a shared project memory.

CURRENT PROJECT SUMMARY (may be rough or outdated):
{room.project_summary if room.project_summary else "(no project summary yet; help define it as you go.)"}

Your goals:
- React to the latest human message from your domain perspective.
- Propose concrete next steps in YOUR domain (not generic fluff).
- Optionally suggest an updated project summary in a section at the end:

SUMMARY_UPDATE:
<1–3 sentences that refine or replace the summary>

Keep your responses focused and fairly short (under ~300 words if possible).
"""

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_instructions}
    ]

    # Add some recent conversation context
    for m in recent_msgs:
        messages.append({
            "role": m.role,
            "content": f"{m.sender_name}: {m.content}",
        })

    # Latest human message as the main question
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
    Build messages for the Coordinator.
    It sees:
      - project summary
      - latest human message
      - all three twins' drafts
    and must create ONE unified answer.
    """

    system_instructions = f"""
You are {COORDINATOR_PROFILE.display_name}, the coordinating AI for this room.

You receive:
- The current project summary.
- The latest human message.
- Draft responses from three specialist AI twins:
  - Quant Twin
  - Backend Twin
  - Frontend Twin

Your job:
1. Synthesize their input into ONE clear, well-structured answer for the humans.
2. Resolve contradictions and highlight trade-offs.
3. Propose a short, concrete plan (2–5 next steps).
4. Be practical and concise; avoid repeating the same idea three times.

If you think the project summary should be updated, include at the end:

SUMMARY_UPDATE:
<1–3 sentences that summarize the current project and direction>

The human team will mostly see YOUR response as the main "Project Copilot" answer.
"""

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_instructions},
        {"role": "system", "content": f"CURRENT PROJECT SUMMARY:\n{room.project_summary or '(none yet)'}"},
        {"role": "user", "content": f"Latest human message from {user_message.sender_name}:\n{user_message.content}"},
    ]

    # Inject each twin's draft as assistant messages
    label_map = {
        "quant": "Quant Twin",
        "backend": "Backend Twin",
        "frontend": "Frontend Twin",
    }

    for agent_id, text in twin_outputs.items():
        label = label_map.get(agent_id, agent_id)
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
        model=OPENAI_MODEL_TWIN,
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
        model=OPENAI_MODEL_COORDINATOR,
        messages=messages,
        temperature=0.35,
    )
    return resp.choices[0].message.content


# ============================================================
# Summary updater
# ============================================================

def extract_summary_update(text: str) -> Optional[str]:
    marker = "SUMMARY_UPDATE:"
    if marker not in text:
        return None
    idx = text.index(marker)
    part = text[idx + len(marker):].strip()
    return part or None


def maybe_update_summary_from_twins(room: RoomState, twin_outputs: Dict[str, str]) -> None:
    """
    Look for SUMMARY_UPDATE in any twin's response.
    Priority order: quant > backend > frontend.
    """
    priority = ["quant", "backend", "frontend"]
    for agent_id in priority:
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

    # 1) Store the human message
    user_msg = Message(
        sender_id=f"user:{payload.user_id}",
        sender_name=payload.user_name,
        role="user",
        content=payload.content,
        created_at=datetime.utcnow(),
    )
    room.messages.append(user_msg)

    # 2) Call each twin
    twin_outputs: Dict[str, str] = {}
    for agent_id, agent in AGENTS.items():
        print(f"[room {room_id}] Calling {agent.display_name}...")
        reply_text = call_twin_agent(agent, room, user_msg)
        twin_outputs[agent_id] = reply_text

        # Store twin message (you can hide these in the UI if you want)
        agent_msg = Message(
            sender_id=f"agent:{agent_id}",
            sender_name=agent.display_name,
            role="assistant",
            content=reply_text,
            created_at=datetime.utcnow(),
        )
        room.messages.append(agent_msg)

    # 3) Optionally update project summary from twins
    maybe_update_summary_from_twins(room, twin_outputs)

    # 4) Call coordinator to synthesize ONE main answer
    print(f"[room {room_id}] Calling coordinator (Project Copilot)...")
    coord_text = call_coordinator_agent(room, user_msg, twin_outputs)
    coord_msg = Message(
        sender_id="agent:coordinator",
        sender_name=COORDINATOR_PROFILE.display_name,
        role="assistant",
        content=coord_text,
        created_at=datetime.utcnow(),
    )
    room.messages.append(coord_msg)

    # 5) Optionally update project summary from coordinator
    maybe_update_summary_from_coordinator(room, coord_text)

    return PostMessageResponse(
        room_id=room.id,
        room_name=room.name,
        project_summary=room.project_summary,
        messages=room.messages,
    )
