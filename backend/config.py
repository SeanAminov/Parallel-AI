# config.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CLIENT_A_KEY = os.getenv("OPENAI_API_KEY_A")
CLIENT_B_KEY = os.getenv("OPENAI_API_KEY_B")
CLIENT_C_KEY = os.getenv("OPENAI_API_KEY_C")
CLIENT_D_KEY = os.getenv("OPENAI_API_KEY_D")  # coordinator

def make_client(key: str | None) -> OpenAI:
    if not key:
        raise RuntimeError("Missing an API key for one of the clients")
    return OpenAI(api_key=key)

CLIENT_A = make_client(CLIENT_A_KEY)
CLIENT_B = make_client(CLIENT_B_KEY)
CLIENT_C = make_client(CLIENT_C_KEY)
CLIENT_D = make_client(CLIENT_D_KEY)

# one model for all – change if your hackathon requires a specific one
OPENAI_MODEL = "gpt-4.1-mini"
