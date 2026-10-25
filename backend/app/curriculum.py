"""Structured 49-concept Python curriculum across Foundations, Collections, Intermediate Python, and Problem Solving."""
import json
from pathlib import Path

_CURRICULUM_PATH = Path(__file__).resolve().parent / "curriculum.json"
CURRICULUM_CONCEPTS = json.loads(_CURRICULUM_PATH.read_text(encoding="utf-8"))
