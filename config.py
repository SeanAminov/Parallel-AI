# config.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Load all four keys (they can be the same in practice)
OPENAI_API_KEY_A = os.getenv("OPENAI_API_KEY_A")
OPENAI_API_KEY_B = os.getenv("OPENAI_API_KEY_B")
OPENAI_API_KEY_C = os.getenv("OPENAI_API_KEY_C")
OPENAI_API_KEY_D = os.getenv("OPENAI_API_KEY_D")
OPENAI_API_KEY_DEFAULT = os.getenv("OPENAI_API_KEY_DEFAULT")  # optional fallback

def _client_for(key: str | None) -> OpenAI:
    if not key:
        if not OPENAI_API_KEY_DEFAULT:
            raise RuntimeError("Missing OpenAI API key and no OPENAI_API_KEY_DEFAULT fallback set.")
        return OpenAI(api_key=OPENAI_API_KEY_DEFAULT)
    return OpenAI(api_key=key)

# One client per role
CLIENT_A = _client_for(OPENAI_API_KEY_A)
CLIENT_B = _client_for(OPENAI_API_KEY_B)
CLIENT_C = _client_for(OPENAI_API_KEY_C)
CLIENT_D = _client_for(OPENAI_API_KEY_D)

# Model to use (change if hackathon requires a specific one)
OPENAI_MODEL_TWIN = "gpt-4.1-mini"
OPENAI_MODEL_COORDINATOR = "gpt-4.1-mini"
