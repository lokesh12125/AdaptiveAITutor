"""IBM Project CodeNet integration module providing authentic curated programming challenges, reference solutions, and common error patterns."""
import json
from pathlib import Path

_CODENET_PATH = Path(__file__).resolve().parent / "codenet.json"
CODENET_PROBLEMS = json.loads(_CODENET_PATH.read_text(encoding="utf-8"))


def get_codenet_subset() -> list[dict]:
    """Return the curated subset of IBM Project CodeNet problems with metadata."""
    return CODENET_PROBLEMS
