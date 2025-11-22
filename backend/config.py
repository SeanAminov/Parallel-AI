# backend/config.py
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load .env that lives next to this file
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

# Map your four keys to teammates + a coordinator
# A → Yug, B → Sean, C → Severin, D → Nayab (also used as the coordinator)
YUG_KEY     = os.getenv("OPENAI_API_KEY_A")
SEAN_KEY    = os.getenv("OPENAI_API_KEY_B")
SEVERIN_KEY = os.getenv("OPENAI_API_KEY_C")
NAYAB_KEY   = os.getenv("OPENAI_API_KEY_D")  # also coordinator

def make_client(key: str | None) -> OpenAI:
    if not key:
        raise RuntimeError("Missing an API key for one of the clients")
    return OpenAI(api_key=key)

CLIENTS = {
    "yug": make_client(YUG_KEY),
    "sean": make_client(SEAN_KEY),
    "severin": make_client(SEVERIN_KEY),
    "nayab": make_client(NAYAB_KEY),     # used for both Nayab and Coordinator
    "coordinator": make_client(NAYAB_KEY),
}

# one model for all (you can change later)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
