"""Configuration is loaded once from backend/.env without logging secrets."""
from pathlib import Path
import os

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
DATABASE_PATH = BACKEND_DIR / "tutor.db"


def api_key_configured() -> bool:
    """Return configuration status only; the secret itself is never returned."""
    return bool(OPENAI_API_KEY)
