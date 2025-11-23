import os
import uuid
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional, Tuple
import logging
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from passlib.context import CryptContext

from fastapi.responses import JSONResponse

from database import SessionLocal, engine, Base
from models import (
    AgentProfile as AgentORM,
    InboxTask as InboxTaskORM,
    MemoryRecord as MemoryORM,
    Message as MessageORM,
    Organization as OrganizationORM,
    Room as RoomORM,
    User as UserORM,
    UserCredential as UserCredentialORM,
    UserSentiment as UserSentimentORM,
)

from config import CLIENTS, OPENAI_MODEL
from openai import OpenAI

import httpx
from fastapi.responses import RedirectResponse

from dotenv import load_dotenv

load_dotenv()

# Which implementation to use:
#   official -> uses spoon_official.build_team_graph (Spoon OS StateGraph)
#   local    -> uses spoon_os ask_one/ask_team/synthesize (Windows-friendly)
SPOON_IMPL = os.getenv("SPOON_IMPL", "local").lower()
if SPOON_IMPL == "official":
    from spoon_official import build_team_graph
else:
    from spoon_os import ask_one, ask_team, synthesize

SUBSCRIBERS: list[tuple[asyncio.Queue, Dict[str, Optional[str]]]] = []
PROPAGATE_ERRORS = os.getenv("PROPAGATE_ERRORS", "false").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEBUG_ERRORS = os.getenv("DEBUG_ERRORS", "false").lower() == "true"
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "60"))        # max requests per window
RATE_LIMIT: defaultdict[str, deque] = defaultdict(deque)
BANNED_TERMS = [t.strip().lower() for t in os.getenv("BANNED_TERMS", "").split(",") if t.strip()]

TEAM = [
    {"id": "yug",     "name": "Yug"},
    {"id": "sean",    "name": "Sean"},
    {"id": "severin", "name": "Severin"},
    {"id": "nayab",   "name": "Nayab"},
]

# ============================================================
# API schemas
# ============================================================

class MessageOut(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

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
    messages: List[MessageOut]

    class Config:
        from_attributes = True

class MemoryQueryRequest(BaseModel):
    question: str
    user_name: str = "System"

class CreateUserRequest(BaseModel):
    email: str
    name: str
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    preferences: Dict = {}
    created_at: datetime

    class Config:
        from_attributes = True

class AuthLoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class PreferencesUpdate(BaseModel):
    preferences: Dict

class SentimentOut(BaseModel):
    score: float
    note: str
    created_at: datetime

    class Config:
        from_attributes = True

class CreateOrgRequest(BaseModel):
    name: str
    owner_user_id: str

class OrgOut(BaseModel):
    id: str
    name: str
    owner_user_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class CreateAgentRequest(BaseModel):
    user_id: str
    name: str
    persona_json: Dict = {}

class AgentOut(BaseModel):
    id: str
    user_id: str
    name: str
    persona_json: Dict
    persona_embedding: Optional[List[float]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class InboxCreateRequest(BaseModel):
    content: str
    room_id: Optional[str] = None
    source_message_id: Optional[str] = None
    priority: Optional[str] = None
    tags: List[str] = []

class InboxUpdateRequest(BaseModel):
    status: Literal["open","done","archived"]
    priority: Optional[str] = None

class InboxTaskOut(BaseModel):
    id: str
    user_id: str
    content: str
    room_id: Optional[str] = None
    source_message_id: Optional[str] = None
    status: str
    priority: Optional[str] = None
    tags: List[str] = []
    created_at: datetime

    class Config:
        from_attributes = True

class PersonaImportRequest(BaseModel):
    raw_text: str

class MemoryOut(BaseModel):
    id: str
    agent_id: str
    room_id: Optional[str]
    content: str
    importance_score: float = 0.0
    embedding: Optional[List[float]] = None
    created_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# FastAPI app + CORS
# ============================================================

app = FastAPI(title="Parallel Workspace with Shared Memory")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    file_handler = logging.FileHandler("app.log")
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

# CORS (must not use "*" when allow_credentials=True)
# origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def debug_cors_and_errors(request: Request, call_next):
    origin = request.headers.get("origin")
    logger.info("REQ %s %s Origin=%s", request.method, request.url, origin)

    try:
        # Basic rate limiting by IP/user
        key = rate_limit_key(request)
        check_rate_limit(key)
        response = await call_next(request)
    except HTTPException as exc:
        # Normal HTTP errors (401/403/etc) – still wrap so we can attach CORS
        logger.warning(
            "HTTPException %s on %s %s: %s",
            exc.status_code,
            request.method,
            request.url,
            exc.detail,
        )
        response = JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    except Exception as exc:
        # Catch any crash so it doesn't look like random CORS
        logger.exception("Unhandled error on %s %s", request.method, request.url)
        if DEBUG_ERRORS:
            response = JSONResponse(
                status_code=500,
                content={"detail": str(exc), "type": exc.__class__.__name__},
            )
        else:
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error"},
            )

    # Force CORS for dev origins even when there was an error
    if origin in ("http://localhost:5173", "http://localhost"):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Vary"] = "Origin"

    return response

# ============================================================
# Helpers
# ============================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def decode_token_sub(token: str) -> Optional[str]:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return data.get("sub")
    except Exception:
        return None


def rate_limit_key(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    token = request.cookies.get("access_token")
    sub = decode_token_sub(token) if token else None
    # Prefer user-specific key when authenticated; fallback to IP for anonymous requests
    if sub:
        return f"user:{sub}"
    return f"ip:{ip}"


def check_rate_limit(key: str):
    now = datetime.utcnow().timestamp()
    window_start = now - RATE_LIMIT_WINDOW
    q = RATE_LIMIT[key]
    while q and q[0] < window_start:
        q.popleft()
    if len(q) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many requests, slow down.")
    q.append(now)


def ensure_agent(db: Session, agent_id: str, agent_name: str, user_id: Optional[str] = None):
    """
    Ensure an agent exists; create a system-backed agent if none exists.
    """
    existing = db.get(AgentORM, agent_id)
    if existing:
        return existing

    owner_id = user_id
    if not owner_id:
        first_user = db.query(UserORM).first()
        if first_user:
            owner_id = first_user.id
        else:
            # create a system user so the FK is satisfied
            system_user = UserORM(
                id=str(uuid.uuid4()),
                email="system@parallel.local",
                name="System",
                preferences={},
                created_at=datetime.utcnow(),
            )
            db.add(system_user)
            db.commit()
            owner_id = system_user.id
    agent = AgentORM(
        id=agent_id,
        user_id=owner_id,
        name=agent_name,
        persona_json={"role": agent_name},
        created_at=datetime.utcnow(),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent

@app.on_event("startup")
def seed_system_agents():
    db = SessionLocal()
    try:
        ensure_agent(db, "coordinator", "Coordinator")
    finally:
        db.close()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

def hash_password(password: str) -> str:
    return pwd_context.hash(password)   

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def is_abusive_text(text: str) -> bool:
    lower = text.lower()
    if any(term in lower for term in BANNED_TERMS):
        return True
    # naive prompt-injection guardrails
    if "ignore previous instructions" in lower:
        return True
    return False


def get_current_user(request: Request, db: Session) -> Optional[UserORM]:
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            return None
    except JWTError:
        return None
    return db.get(UserORM, user_id)


def require_current_user(request: Request, db: Session) -> UserORM:
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user




def get_or_create_org_for_user(db: Session, user: UserORM) -> OrganizationORM:
    org = db.query(OrganizationORM).filter(OrganizationORM.owner_user_id == user.id).first()
    if org:
        return org
    org = OrganizationORM(
        id=str(uuid.uuid4()),
        name=f"{user.name}'s Org",
        owner_user_id=user.id,
        created_at=datetime.utcnow(),
    )
    db.add(org)
    db.commit()
    return org

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    seed_demo(SessionLocal())

def seed_demo(db: Session):
    existing = db.query(UserORM).first()
    if existing:
        return
    demo_user = UserORM(id=str(uuid.uuid4()), email="demo@parallel.local", name="Demo User", preferences={"tone":"calm"})
    db.add(demo_user)
    cred = UserCredentialORM(
        user_id=demo_user.id,
        password_hash=hash_password("parallel-demo"),
        created_at=datetime.utcnow(),
    )
    db.add(cred)
    db.flush()
    org = OrganizationORM(id=str(uuid.uuid4()), name="Demo Org", owner_user_id=demo_user.id)
    db.add(org)
    agent = AgentORM(
        id=str(uuid.uuid4()),
        user_id=demo_user.id,
        name="Parallel Brain",
        persona_json={"tone": "calm", "detail_level": "medium"},
    )
    db.add(agent)
    room = RoomORM(id=str(uuid.uuid4()), org_id=org.id, name="Demo Room")
    db.add(room)
    db.commit()

def client_for(agent_id: str) -> OpenAI:
    if agent_id not in CLIENTS:
        raise HTTPException(400, f"Unknown agent '{agent_id}'")
    return CLIENTS[agent_id]

def summary_update_from(text: str) -> Optional[str]:
    marker = "SUMMARY_UPDATE:"
    if marker not in text:
        return None
    return text.split(marker, 1)[1].strip() or None

def persona_update_from(text: str) -> Optional[Dict]:
    marker = "PERSONA_UPDATE:"
    if marker not in text:
        return None
    payload = text.split(marker, 1)[1].strip()
    try:
        # Expect simple key: value per line
        updates = {}
        for line in payload.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                updates[k.strip()] = v.strip()
        return updates or None
    except Exception:
        return None

def memory_update_from(text: str) -> Optional[str]:
    marker = "MEMORY_UPDATE:"
    if marker not in text:
        return None
    return text.split(marker, 1)[1].strip() or None

def make_assistant_msg(agent_id: str, agent_name: str, content: str, room_id: Optional[str] = None) -> MessageORM:
    return MessageORM(
        id=str(uuid.uuid4()),
        room_id=room_id or "",
        sender_id=f"agent:{agent_id}",
        sender_name=agent_name,
        role="assistant",
        content=content,
        created_at=datetime.utcnow(),
    )

def append_memory_note(db: Session, room: RoomORM, note: str, agent_id: str = "coordinator"):
    if "ensure_agent" in globals():
        ensure_agent(db, agent_id, agent_id.title())
    timestamp = datetime.utcnow().isoformat(timespec="seconds")
    summary = room.memory_summary or ""
    room.memory_summary = summary
    # store as MemoryRecord with low importance
    mem = MemoryORM(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        room_id=room.id,
        content=f"[{timestamp}] {note}",
        importance_score=0.1,
        created_at=datetime.utcnow(),
    )
    return mem

def build_system_context(db: Session, room: RoomORM) -> str:
    personas = []
    agents = db.query(AgentORM).all()
    for agent in agents:
        if agent.persona_json:
            personas.append(f"{agent.name}: {agent.persona_json}")

    persona_block = "\n".join(personas) if personas else "(none)"

    return f"""Shared Memory Summary (not auto-shown to users unless asked):
{room.memory_summary or "(empty yet)"}

Known personas:
{persona_block}

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
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content
    except Exception as e:
        detail = str(e)
        resp = getattr(e, "response", None)
        if resp:
            try:
                detail = resp.json()
            except Exception:
                status = getattr(resp, "status_code", "?")
                detail = f"OpenAI error (status {status}): {e}"
        raise HTTPException(status_code=502, detail={"provider": "openai", "error": detail})


def fetch_user_and_prefs(db: Session, user_id: str) -> Tuple[Optional[UserORM], Dict]:
    if not user_id:
        return None, {}
    user = db.get(UserORM, user_id)
    prefs = user.preferences if user and user.preferences else {}
    return user, prefs


def retrieve_memories(db: Session, room_id: str, limit: int = 10) -> List[MemoryORM]:
    return (
        db.query(MemoryORM)
        .filter(MemoryORM.room_id == room_id)
        .order_by(MemoryORM.created_at.desc())
        .limit(limit)
        .all()
    )


def build_prompt(
    db: Session,
    room: RoomORM,
    user_id: str,
    user_name: str,
    content: str,
    mode: str,
) -> Tuple[str, List[Dict[str, str]], Dict]:
    user, prefs = fetch_user_and_prefs(db, user_id)
    memories = retrieve_memories(db, room.id, limit=8)
    memories_text = "\n".join(m.content for m in memories)

    sys_ctx = build_system_context(db, room)
    prefs_block = f"User preferences: {prefs}" if prefs else "User preferences: (none)"
    mode_block = f"Mode: {mode}"

    system_prompt = f"""{sys_ctx}

{prefs_block}
{mode_block}
Guidance:
- Answer concisely.
- Do not include next steps or extra commentary unless the user explicitly asks for them.
Recent memories:
{memories_text or "(none)"}"""

    msgs = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{user_name} asks:\n{content}"},
    ]
    return system_prompt, msgs, prefs


def parse_tasks_from_text(text: str) -> List[str]:
    tasks = []
    lowers = text.lower()
    markers = ["remind", "notify", "todo", "to-do", "follow up", "follow-up"]
    for marker in markers:
        if marker in lowers:
            tasks.append(text.strip())
            break
    return tasks


def compute_sentiment(text: str) -> float:
    lower = text.lower()
    positive = ["thanks", "great", "good", "love", "awesome", "nice", "helpful"]
    negative = ["bad", "hate", "angry", "upset", "frustrated", "terrible", "slow"]
    score = 0
    for p in positive:
        if p in lower:
            score += 1
    for n in negative:
        if n in lower:
            score -= 1
    return max(-1.0, min(1.0, score / 3.0))

def to_message_out(msg: MessageORM) -> MessageOut:
    return MessageOut(
        id=msg.id,
        sender_id=msg.sender_id,
        sender_name=msg.sender_name,
        role=msg.role,  # type: ignore
        content=msg.content,
        created_at=msg.created_at,
    )

def room_to_response(db: Session, room: RoomORM) -> RoomResponse:
    msgs = (
        db.query(MessageORM)
        .filter(MessageORM.room_id == room.id)
        .order_by(MessageORM.created_at.asc())
        .all()
    )
    memories = db.query(MemoryORM).filter(MemoryORM.room_id == room.id).count()
    return RoomResponse(
        room_id=room.id,
        room_name=room.name,
        project_summary=room.project_summary or "",
        memory_summary=room.memory_summary or "",
        memory_count=memories,
        messages=[to_message_out(m) for m in msgs],
    )

# ============================================================
# Event stream (SSE)
# ============================================================

def publish_event(payload: Dict):
    """Push events to SSE subscribers when propagation is enabled."""
    if not PROPAGATE_ERRORS:
        return
    for q, filters in list(SUBSCRIBERS):
        try:
            room_filter = filters.get("room_id")
            user_filter = filters.get("user_id")
            if room_filter and payload.get("room_id") not in (room_filter, None):
                continue
            if user_filter and payload.get("user_id") not in (user_filter, None):
                continue
            q.put_nowait(payload)
        except asyncio.QueueFull:
            continue

async def event_generator(filters: Dict):
    queue: asyncio.Queue = asyncio.Queue()
    SUBSCRIBERS.append((queue, filters))
    try:
        while True:
            data = await queue.get()
            yield f"data: {json.dumps(data)}\n\n"
    finally:
        if (queue, filters) in SUBSCRIBERS:
            SUBSCRIBERS.remove((queue, filters))

def run_graph(app_graph, inputs):
    """
    Runs a Spoon graph call whether the SDK returns a sync result or a coroutine.
    """
    try:
        res = app_graph.invoke(inputs)
        if hasattr(res, "__await__"):
            import asyncio
            return asyncio.run(res)
        return res
    except TypeError:
        import asyncio
        return asyncio.run(app_graph.ainvoke(inputs))

# ============================================================
# Routes
# ============================================================

def publish_status(room_id: str, step: str, meta: Optional[Dict] = None):
    publish_event({
        "type": "status",
        "room_id": room_id,
        "step": step,
        "meta": meta or {},
        "ts": datetime.utcnow().isoformat(),
    })

def publish_error(room_id: str, message: str, meta: Optional[Dict] = None):
    publish_event({
        "type": "error",
        "room_id": room_id,
        "message": message,
        "meta": meta or {},
        "ts": datetime.utcnow().isoformat(),
    })

@app.get("/events")
async def events(room_id: Optional[str] = None, user_id: Optional[str] = None):
    """
    Server-Sent Events stream for status/error propagation.
    """
    filters = {"room_id": room_id, "user_id": user_id}
    return StreamingResponse(event_generator(filters), media_type="text/event-stream")

@app.post("/users", response_model=UserOut)
def create_user(payload: CreateUserRequest, db: Session = Depends(get_db)):
    exists = db.query(UserORM).filter(UserORM.email == payload.email).first()
    if exists:
        raise HTTPException(400, "Email already registered")
    user = UserORM(
        id=str(uuid.uuid4()),
        email=payload.email,
        name=payload.name,
        created_at=datetime.utcnow(),
    )
    cred = UserCredentialORM(
        user_id=user.id,
        password_hash=hash_password(payload.password),
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.add(cred)
    db.commit()
    return user

@app.post("/auth/register", response_model=UserOut)
def register(payload: CreateUserRequest, response: Response, db: Session = Depends(get_db)):
    logger.info("Register attempt for email=%s", payload.email)
    user = create_user(payload, db)
    token = create_access_token({"sub": user.id})
    response.set_cookie("access_token", token, httponly=True, secure=False, samesite="lax")
    logger.info("Register success user_id=%s", user.id)
    return user

@app.post("/auth/login", response_model=TokenResponse)
def login(payload: AuthLoginRequest, response: Response, db: Session = Depends(get_db)):
    logger.info("Login attempt for email=%s", payload.email)
    user = db.query(UserORM).filter(UserORM.email == payload.email).first()
    if not user:
        logger.warning("Login failed, user not found email=%s", payload.email)
        raise HTTPException(401, "Invalid credentials")
    cred = db.get(UserCredentialORM, user.id)
    if not cred or not verify_password(payload.password, cred.password_hash):
        logger.warning("Login failed, bad password email=%s", payload.email)
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.id})
    response.set_cookie("access_token", token, httponly=True, secure=False, samesite="lax")
    logger.info("Login success user_id=%s", user.id)
    return TokenResponse(access_token=token)



@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    logger.info("Logout invoked")
    return {"ok": True}

@app.get("/me", response_model=UserOut)
def me(request: Request, db: Session = Depends(get_db)):
    return require_current_user(request, db)

@app.post("/organizations", response_model=OrgOut)
def create_org(payload: CreateOrgRequest, db: Session = Depends(get_db)):
    owner = db.get(UserORM, payload.owner_user_id)
    if not owner:
        raise HTTPException(404, "Owner user not found")
    org = OrganizationORM(
        id=str(uuid.uuid4()),
        name=payload.name,
        owner_user_id=payload.owner_user_id,
        created_at=datetime.utcnow(),
    )
    db.add(org)
    db.commit()
    return org

@app.post("/agents", response_model=AgentOut)
def create_agent(payload: CreateAgentRequest, db: Session = Depends(get_db)):
    user = db.get(UserORM, payload.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    agent = AgentORM(
        id=str(uuid.uuid4()),
        user_id=payload.user_id,
        name=payload.name,
        persona_json=payload.persona_json or {},
        created_at=datetime.utcnow(),
    )
    db.add(agent)
    db.commit()
    return agent

@app.get("/users/{user_id}/inbox", response_model=List[InboxTaskOut])
def list_inbox(user_id: str, request: Request, db: Session = Depends(get_db)):
    me = require_current_user(request, db)
    if me.id != user_id:
        raise HTTPException(403, "Forbidden")
    tasks = (
        db.query(InboxTaskORM)
        .filter(InboxTaskORM.user_id == user_id)
        .order_by(InboxTaskORM.created_at.desc())
        .all()
    )
    return tasks

@app.post("/users/{user_id}/inbox", response_model=InboxTaskOut)
def add_inbox(user_id: str, payload: InboxCreateRequest, request: Request, db: Session = Depends(get_db)):
    me = require_current_user(request, db)
    if me.id != user_id:
        raise HTTPException(403, "Forbidden")
    user = db.get(UserORM, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    task = InboxTaskORM(
        id=str(uuid.uuid4()),
        user_id=user_id,
        content=payload.content,
        room_id=payload.room_id,
        source_message_id=payload.source_message_id,
        priority=payload.priority,
        tags=payload.tags,
        created_at=datetime.utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@app.patch("/users/{user_id}/inbox/{task_id}", response_model=InboxTaskOut)
def update_inbox(user_id: str, task_id: str, payload: InboxUpdateRequest, request: Request, db: Session = Depends(get_db)):
    me = require_current_user(request, db)
    if me.id != user_id:
        raise HTTPException(403, "Forbidden")
    task = db.get(InboxTaskORM, task_id)
    if not task or task.user_id != user_id:
        raise HTTPException(404, "Task not found")
    task.status = payload.status
    task.priority = payload.priority or task.priority
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

@app.post("/users/{user_id}/import_persona")
def import_persona(user_id: str, payload: PersonaImportRequest, db: Session = Depends(get_db)):
    user = db.get(UserORM, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    # Placeholder parser: derive tone/detail_level heuristically
    text = payload.raw_text
    tone = "calm"
    if any(word in text.lower() for word in ["urgent", "asap", "fast"]):
        tone = "direct"
    persona = {
        "tone": tone,
        "detail_level": "medium",
        "likes": [],
        "dislikes": [],
        "source": "import_persona_stub",
    }
    embedding = None  # placeholder until vector service is added
    return {"persona_json": persona, "persona_embedding": embedding}

@app.post("/rooms/{room_id}/memories", response_model=MemoryOut)
def add_memory(room_id: str, payload: MemoryQueryRequest, db: Session = Depends(get_db)):
    room = db.get(RoomORM, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    ensure_agent(db, "coordinator", "Coordinator")
    memory = MemoryORM(
        id=str(uuid.uuid4()),
        agent_id="coordinator",
        room_id=room_id,
        content=payload.question,
        importance_score=0.1,
        embedding=None,
        created_at=datetime.utcnow(),
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory

@app.get("/rooms/{room_id}/memories", response_model=List[MemoryOut])
def list_memories(room_id: str, db: Session = Depends(get_db)):
    room = db.get(RoomORM, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    memories = db.query(MemoryORM).filter(MemoryORM.room_id == room_id).all()
    return memories

@app.get("/users/{user_id}/sentiments", response_model=List[SentimentOut])
def list_sentiments(user_id: str, db: Session = Depends(get_db)):
    user = db.get(UserORM, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    sentiments = (
        db.query(UserSentimentORM)
        .filter(UserSentimentORM.user_id == user_id)
        .order_by(UserSentimentORM.created_at.desc())
        .all()
    )
    return sentiments

@app.patch("/me/preferences", response_model=UserOut)
def update_preferences(payload: PreferencesUpdate, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request, db)
    prefs = payload.preferences or {}
    user.preferences = prefs
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@app.post("/rooms", response_model=CreateRoomResponse)
def create_room(payload: CreateRoomRequest, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request, db)
    org = get_or_create_org_for_user(db, user)
    if is_abusive_text(payload.room_name):
        raise HTTPException(400, "Room name rejected by safety filter.")
    room_id = str(uuid.uuid4())
    room = RoomORM(id=room_id, name=payload.room_name, org_id=org.id)
    db.add(room)
    db.commit()
    logger.info("Room created room_id=%s org_id=%s user_id=%s", room_id, org.id, user.id)
    return CreateRoomResponse(room_id=room_id, room_name=room.name)

@app.get("/rooms/{room_id}", response_model=RoomResponse)
def get_room(room_id: str, request: Request, db: Session = Depends(get_db)):
    user = require_current_user(request, db)
    room = db.get(RoomORM, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    owner_org = db.query(OrganizationORM).filter(OrganizationORM.owner_user_id == user.id).first()
    if owner_org and room.org_id != owner_org.id:
        raise HTTPException(403, "Forbidden")
    return room_to_response(db, room)

@app.post("/rooms/{room_id}/ask", response_model=RoomResponse)
def ask(room_id: str, payload: AskModeRequest, request: Request, db: Session = Depends(get_db)):
    user_obj = require_current_user(request, db)
    room = db.get(RoomORM, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    owner_org = db.query(OrganizationORM).filter(OrganizationORM.owner_user_id == user_obj.id).first()
    if owner_org and room.org_id != owner_org.id:
        raise HTTPException(403, "Forbidden")

    publish_status(room_id, "ask_received", {"mode": payload.mode, "user": payload.user_name})
    logger.info("Ask received room_id=%s user_id=%s mode=%s", room_id, payload.user_id, payload.mode)

    if is_abusive_text(payload.content):
        logger.warning("Blocked abusive prompt room_id=%s user_id=%s", room_id, payload.user_id)
        raise HTTPException(400, "Prompt blocked by safety filters.")

    if len(payload.content) > 4000:
        raise HTTPException(413, "Prompt too large. Please shorten your request.")

    # 1) store human message
    human = MessageORM(
        id=str(uuid.uuid4()),
        room_id=room.id,
        sender_id=f"user:{payload.user_id}",
        sender_name=payload.user_name,
        role="user",
        content=payload.content,
        created_at=datetime.utcnow(),
    )
    db.add(human)
    db.commit()

    sys_ctx = build_system_context(db, room)
    mode = payload.mode or "self"

    try:
        sys_ctx, base_msgs, prefs = build_prompt(db, room, payload.user_id, payload.user_name, payload.content, mode)
        # 2) routing (official Spoon OS vs. local orchestrator)
        if SPOON_IMPL == "official":
            graph = build_team_graph()

            if mode in ("self", "teammate"):
                target = payload.target_agent or "yug"
                publish_status(room_id, "routing_agent", {"agent": target})

                # ask_one
                graph.set_entry_point("ask_one")
                app_graph = graph.compile()
                res = run_graph(app_graph, {
                    "asker": payload.user_name,
                    "prompt": payload.content,
                    "sys_ctx": sys_ctx,
                    "mode": mode,
                    "target": target,
                })
                drafts = res["drafts"]
                db.add(make_assistant_msg(target, target.title(), drafts[target], room.id))
                publish_status(room_id, "agent_reply", {"agent": target})

                # synthesize
                graph.set_entry_point("synthesize")
                app_graph = graph.compile()
                synth = run_graph(app_graph, {
                    "asker": payload.user_name,
                    "prompt": payload.content,
                    "sys_ctx": sys_ctx,
                    "drafts": drafts
                })["synthesis"]

                if (upd := summary_update_from(synth)):
                    room.project_summary = upd
                    room.memory_summary = upd
                    mem = append_memory_note(db, room, "Coordinator updated summary (from single-ask).")
                    db.add(mem)
                if (pers := persona_update_from(synth)):
                    agent = db.query(AgentORM).first()
                    if agent:
                        existing = agent.persona_json or {}
                        existing.update(pers)
                        agent.persona_json = existing
                        db.add(agent)
                if (mem_upd := memory_update_from(synth)):
                    ensure_agent(db, "coordinator", "Coordinator")
                    mem = MemoryORM(
                        id=str(uuid.uuid4()),
                        agent_id="coordinator",
                        room_id=room.id,
                        content=mem_upd,
                        importance_score=0.5,
                        created_at=datetime.utcnow(),
                    )
                    db.add(mem)

            else:  # mode == "team"
                publish_status(room_id, "team_fanout_start", {"agents": [m["id"] for m in TEAM]})
                # ask_team
                graph.set_entry_point("ask_team")
                app_graph = graph.compile()
                res = run_graph(app_graph, {
                    "asker": payload.user_name,
                    "prompt": payload.content,
                    "sys_ctx": sys_ctx,
                })
                drafts: Dict[str, str] = res["drafts"]

                for member, text in drafts.items():
                    msg = make_assistant_msg(member, member.title(), text, room.id)
                    db.add(msg)

                # synthesize
                publish_status(room_id, "synthesizing", {"agent": "Coordinator"})
                graph.set_entry_point("synthesize")
                app_graph = graph.compile()
                synth = run_graph(app_graph, {
                    "asker": payload.user_name,
                    "prompt": payload.content,
                    "sys_ctx": sys_ctx,
                    "drafts": drafts
                })["synthesis"]

                synth_msg = make_assistant_msg("coordinator", "Coordinator", synth, room.id)
                db.add(synth_msg)
                publish_status(room_id, "synthesis_complete", {"agent": "Coordinator"})

                if (upd := summary_update_from(synth)):
                    room.project_summary = upd
                    room.memory_summary = upd
                    mem = append_memory_note(db, room, "Coordinator updated summary.")
                    db.add(mem)
                if (pers := persona_update_from(synth)):
                    agent = db.query(AgentORM).first()
                    if agent:
                        existing = agent.persona_json or {}
                        existing.update(pers)
                        agent.persona_json = existing
                        db.add(agent)
                if (mem_upd := memory_update_from(synth)):
                    ensure_agent(db, "coordinator", "Coordinator")
                    mem = MemoryORM(
                        id=str(uuid.uuid4()),
                        agent_id="coordinator",
                        room_id=room.id,
                        content=mem_upd,
                        importance_score=0.5,
                        created_at=datetime.utcnow(),
                    )
                    db.add(mem)

        else:
            # Local orchestrator (Windows friendly)
            if mode in ("self", "teammate"):
                agent_id = payload.target_agent or "yug"
                publish_status(room_id, "routing_agent", {"agent": agent_id})
                drafts = ask_one(payload.user_name, payload.content, sys_ctx, agent_id)
                msg = make_assistant_msg(agent_id, agent_id.title(), drafts[agent_id], room.id)
                db.add(msg)
                publish_status(room_id, "agent_reply", {"agent": agent_id})

                synth = synthesize(payload.user_name, payload.content, sys_ctx, drafts)
                if (upd := summary_update_from(synth)):
                    room.project_summary = upd
                    room.memory_summary = upd
                    mem = append_memory_note(db, room, "Coordinator updated summary (from single-ask).")
                    db.add(mem)
                if (pers := persona_update_from(synth)):
                    agent = db.query(AgentORM).first()
                    if agent:
                        existing = agent.persona_json or {}
                        existing.update(pers)
                        agent.persona_json = existing
                        db.add(agent)
                if (mem_upd := memory_update_from(synth)):
                    ensure_agent(db, "coordinator", "Coordinator")
                    mem = MemoryORM(
                        id=str(uuid.uuid4()),
                        agent_id="coordinator",
                        room_id=room.id,
                        content=mem_upd,
                        importance_score=0.5,
                        created_at=datetime.utcnow(),
                    )
                    db.add(mem)

            else:  # mode == "team"
                publish_status(room_id, "team_fanout_start", {"agents": [m["id"] for m in TEAM]})
                drafts = ask_team(payload.user_name, payload.content, sys_ctx)
                for member, text in drafts.items():
                    msg = make_assistant_msg(member, member.title(), text, room.id)
                    db.add(msg)

                publish_status(room_id, "synthesizing", {"agent": "Coordinator"})
                synth = synthesize(payload.user_name, payload.content, sys_ctx, drafts)
                synth_msg = make_assistant_msg("coordinator", "Coordinator", synth, room.id)
                db.add(synth_msg)
                publish_status(room_id, "synthesis_complete", {"agent": "Coordinator"})

                if (upd := summary_update_from(synth)):
                    room.project_summary = upd
                    room.memory_summary = upd
                    mem = append_memory_note(db, room, "Coordinator updated summary.")
                    db.add(mem)
                if (pers := persona_update_from(synth)):
                    agent = db.query(AgentORM).first()
                    if agent:
                        existing = agent.persona_json or {}
                        existing.update(pers)
                        agent.persona_json = existing
                        db.add(agent)
                if (mem_upd := memory_update_from(synth)):
                    ensure_agent(db, "coordinator", "Coordinator")
                    mem = MemoryORM(
                        id=str(uuid.uuid4()),
                        agent_id="coordinator",
                        room_id=room.id,
                        content=mem_upd,
                        importance_score=0.5,
                        created_at=datetime.utcnow(),
                    )
                    db.add(mem)
        db.add(room)

        # Inbox auto-routing + sentiment after assistant reply
        latest = (
            db.query(MessageORM)
            .filter(MessageORM.room_id == room.id, MessageORM.role == "assistant")
            .order_by(MessageORM.created_at.desc())
            .first()
        )
        if latest:
            tasks = parse_tasks_from_text(latest.content)
            for t in tasks:
                task = InboxTaskORM(
                    id=str(uuid.uuid4()),
                    user_id=payload.user_id,
                    content=t,
                    room_id=room.id,
                    source_message_id=latest.id,
                    status="open",
                    created_at=datetime.utcnow(),
                )
                db.add(task)

        if payload.user_id:
            score = compute_sentiment(payload.content)
            sentiment = UserSentimentORM(
                id=str(uuid.uuid4()),
                user_id=payload.user_id,
                score=score,
                note="",
                created_at=datetime.utcnow(),
            )
            db.add(sentiment)

        db.commit()
    except Exception as exc:
        logger.exception("Ask failed room_id=%s user_id=%s", room_id, payload.user_id)
        publish_error(room_id, str(exc), {"mode": mode})
        raise

    db.refresh(room)
    return room_to_response(db, room)

@app.get("/rooms/{room_id}/memory")
def get_memory(room_id: str, db: Session = Depends(get_db)):
    room = db.get(RoomORM, room_id)
    if not room:
        raise HTTPException(404, "Room not found")
    memories = (
        db.query(MemoryORM)
        .filter(MemoryORM.room_id == room_id)
        .order_by(MemoryORM.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "memory_summary": room.memory_summary,
        "notes": [m.content for m in memories],
        "count": len(memories),
    }

@app.post("/rooms/{room_id}/memory/query")
def query_memory(room_id: str, payload: MemoryQueryRequest):
    db = SessionLocal()
    room = db.get(RoomORM, room_id)
    if not room:
        db.close()
        raise HTTPException(404, "Room not found")
    memories = (
        db.query(MemoryORM)
        .filter(MemoryORM.room_id == room_id)
        .order_by(MemoryORM.created_at.desc())
        .all()
    )
    context_block = "\n".join(m.content for m in memories[-200:])
    context = (room.memory_summary or "") + "\n\n" + context_block
    msgs = [
        {"role": "system", "content": "You are the project memory. Answer using only the provided memory context."},
        {"role": "system", "content": f"MEMORY CONTEXT:\n{context or '(empty)'}"},
        {"role": "user", "content": f"{payload.user_name} asks: {payload.question}"},
    ]
    answer = chat(client_for("coordinator"), msgs, temperature=0.2)
    note = append_memory_note(db, room, f"Memory was queried: {payload.question}")
    if note:
        db.add(note)
    db.commit()
    db.close()
    return {"answer": answer}


FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

@app.get("/auth/google/login")
def google_login():
    """
    Redirects the user to Google's OAuth consent screen.
    """
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }

    from urllib.parse import urlencode
    authorize_url = "https://accounts.google.com/o/oauth2/v2/auth"
    return RedirectResponse(f"{authorize_url}?{urlencode(params)}")


@app.get("/auth/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    """
    Handles Google's redirect, exchanges code for tokens,
    finds/creates a user, sets our normal JWT cookie, and
    redirects back to the frontend.
    """
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI"),
        "grant_type": "authorization_code",
    }

    # Exchange code for tokens
    with httpx.Client() as client:
        resp = client.post(token_url, data=data)
    if resp.status_code != 200:
        raise HTTPException(400, f"Google token error: {resp.text}")

    token_data = resp.json()
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(400, "No id_token from Google")

    # Decode ID token to get user info.
    # (We’re not doing full crypto verification here; for dev it's fine.)
    from jose import jwt as jose_jwt
    claims = jose_jwt.get_unverified_claims(id_token)
    email = claims.get("email")
    name = claims.get("name") or email

    if not email:
        raise HTTPException(400, "Google account has no email")

    # Find or create user in our DB
    user = db.query(UserORM).filter(UserORM.email == email).first()
    if not user:
        user = UserORM(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Issue our normal JWT and cookie (same as /auth/login)
    token = create_access_token({"sub": user.id})

    response = RedirectResponse(FRONTEND_BASE_URL)  # e.g. homepage or /app
    response.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=False,  # set True in production with HTTPS
        samesite="lax",
    )
    return response
