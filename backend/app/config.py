"""Configuration is loaded once from backend/.env without logging secrets."""
from pathlib import Path
import os

# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
DATABASE_PATH = BACKEND_DIR / "tutor.db"

# S-03: Centralized Pedagogical & Cognitive Algorithm Constants
CONFIG_VERSION = "2.1.0"

# Bayesian Knowledge Tracing (BKT) Parameters
BKT_P_L0 = float(os.getenv("BKT_P_L0", "0.20"))
BKT_P_T = float(os.getenv("BKT_P_T", "0.15"))
BKT_P_G = float(os.getenv("BKT_P_G", "0.20"))
BKT_P_S = float(os.getenv("BKT_P_S", "0.10"))

# EWMA Decay Factor
EWMA_ALPHA = float(os.getenv("EWMA_ALPHA", "0.70"))

# Composite Struggle Index (CSI) Component Weights
# (1-Mastery, Phi(Fails), (1-Confidence), CogLoad, HintSaturation, TimeStress)
CSI_WEIGHTS = {
    "mastery": 0.25,
    "consecutive_fails": 0.25,
    "confidence_lack": 0.20,
    "cognitive_load": 0.15,
    "hint_saturation": 0.10,
    "time_stress": 0.05,
}

# Learning Planner Adaptive Thresholds
PLANNER_ADVANCE_MASTERY = float(os.getenv("PLANNER_ADVANCE_MASTERY", "0.75"))
PLANNER_REMEDIATE_CONFUSION = float(os.getenv("PLANNER_REMEDIATE_CONFUSION", "0.60"))
PLANNER_REMEDIATE_LOAD = float(os.getenv("PLANNER_REMEDIATE_LOAD", "0.65"))
PLANNER_MAX_CONSECUTIVE_FAILS = int(os.getenv("PLANNER_MAX_CONSECUTIVE_FAILS", "3"))


def api_key_configured() -> bool:
    """Return configuration status only; the secret itself is never returned."""
    return bool(OPENAI_API_KEY)
