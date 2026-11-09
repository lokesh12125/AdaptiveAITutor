"""Similar Learner Retrieval: ChromaDB finds similar situations, PostgreSQL holds what happened next.

No LLM is involved. Results are aggregates, so they never contain identities or code.
A high similarity is not a guarantee: the output is a suggestion with its support and provenance, and
the agent reports "no reliable match" rather than stretching thin evidence. Synthetic records can be
excluded by configuration, and they are always labelled.
"""
from __future__ import annotations

import hashlib
import logging
import math
import threading
from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import InterventionCase
from .contracts import RetrievalOutput

log = logging.getLogger("csmasf.retrieval")

VECTOR_VERSION = "sv-1"
COLLECTION = "situations_sv1"
CATEGORIES = ["syntax", "runtime", "wrong_answer", "partial", "timeout", "resource"]
PROGRESS_VALUE = {"regressing": 0.0, "stalled": 0.2, "unknown": 0.5, "steady": 0.5, "improving": 0.9, "solved": 1.0}
LEVEL_VALUE = {"low": 0.15, "moderate": 0.5, "high": 0.9}
MIN_SIMILARITY = 0.72
MIN_SUPPORT = 3
MIN_CANDIDATES = 5


def _center(value: float | None) -> float:
    """Map 0..1 to -1..1. Cosine ignores magnitude, so without centring a weak and a strong learner look identical."""
    return 0.0 if value is None else (value - 0.5) * 2


def category_group(category: str) -> str:
    return "resource" if category in ("memory", "output_limit") else ("wrong_answer" if category in ("missing_function", "no_attempt") else category)


def situation_vector(mastery: float, confidence: float | None, confusion: str | None, load: str | None,
                     progress: str, difficulty: float, attempts: int, hints: int, category: str) -> list[float]:
    group = category_group(category)
    return [
        round(x, 4) for x in (
            _center(mastery),
            _center(confidence),
            _center(LEVEL_VALUE.get(confusion or "")),
            _center(LEVEL_VALUE.get(load or "")),
            _center(PROGRESS_VALUE.get(progress, 0.5)),
            _center(difficulty),
            _center(min(attempts, 6) / 6),
            _center(min(hints, 4) / 4),
            *[0.8 if group == c else -0.1 for c in CATEGORIES],
        )
    ]


def anonymise(user_id: str) -> str:
    return hashlib.sha256(f"csmasf-owner:{user_id}".encode()).hexdigest()


class VectorStore:
    def __init__(self) -> None:
        self._collection = None
        self._lock = threading.Lock()
        self._failed: str | None = None

    def collection(self):
        with self._lock:
            if self._collection is None:
                import chromadb

                settings.chroma_path.mkdir(parents=True, exist_ok=True)
                client = chromadb.PersistentClient(path=str(settings.chroma_path), settings=chromadb.Settings(anonymized_telemetry=False))
                # Embeddings are supplied directly. No embedding model is downloaded.
                self._collection = client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"}, embedding_function=None)
            return self._collection

    def upsert_case(self, case: InterventionCase) -> None:
        self.collection().upsert(
            ids=[case.id], embeddings=[case.vector],
            metadatas=[{"provenance": case.provenance, "category": case.category, "unit_id": case.unit_id}],
        )

    def query(self, vector: list[float], category: str, allow_synthetic: bool, n_results: int = 40) -> list[tuple[str, float]]:
        where: dict[str, Any] = {"category": category}
        if not allow_synthetic:
            where = {"$and": [where, {"provenance": "live"}]}
        collection = self.collection()
        count = collection.count()
        if count == 0:
            return []
        result = collection.query(query_embeddings=[vector], n_results=min(n_results, count), where=where, include=["distances"])
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        return [(i, 1.0 - d) for i, d in zip(ids, distances)]  # Chroma cosine distance = 1 - cosine similarity

    def clear(self) -> None:
        collection = self.collection()
        existing = collection.get(include=[])
        if existing["ids"]:
            collection.delete(ids=existing["ids"])

    def count(self) -> int:
        return self.collection().count()


store = VectorStore()


def run_retrieval(db: Session, vector: list[float], category: str, issue_key: str, unit_id: str, difficulty: float,
                  user_id: str, allow_synthetic: bool | None = None) -> RetrievalOutput:
    allow = settings.retrieval_allow_synthetic if allow_synthetic is None else allow_synthetic
    group = category_group(category)
    try:
        hits = store.query(vector, group, allow)
    except Exception as exc:  # noqa: BLE001 - retrieval must never block tutoring
        log.warning("vector query failed: %s", type(exc).__name__)
        return RetrievalOutput(reliable=False, reason="The vector store is unavailable, so no similar situations were used.")
    if not hits:
        return RetrievalOutput(reliable=False, reason="No past situations are stored for this kind of issue yet.")

    similarity = dict(hits)
    cases = db.scalars(select(InterventionCase).where(InterventionCase.id.in_(similarity))).all()
    owner = anonymise(user_id)
    scored: list[tuple[float, InterventionCase]] = []
    for case in cases:
        if case.owner_hash == owner:  # similar *other* learners only
            continue
        base = similarity.get(case.id, 0.0)
        if base < MIN_SIMILARITY:
            continue
        quality = 1.0 if case.issue_key == issue_key else 0.85
        quality *= 1.0 if case.unit_id == unit_id else 0.9
        quality *= 1.0 - 0.5 * min(1.0, abs(case.difficulty - difficulty))
        scored.append((base * quality, case))
    if len(scored) < MIN_CANDIDATES:
        return RetrievalOutput(reliable=False, reason="Too few closely similar situations to rely on.", candidates_considered=len(scored))

    # Prefer measured outcomes. Synthetic cases are only used if no live evidence is available.
    live = [item for item in scored if item[1].provenance == "live"]
    pool = live if len(live) >= MIN_CANDIDATES else scored
    groups: dict[tuple[int, str], list[tuple[float, InterventionCase]]] = defaultdict(list)
    for item in pool:
        groups[(item[1].level, item[1].strategy)].append(item)

    def lower_bound(items: list[tuple[float, InterventionCase]]) -> float:
        n = len(items)
        wins = sum(1 for _, case in items if case.outcome in ("progress", "solved"))
        p = (wins + 1) / (n + 2)
        return p - 1.0 * math.sqrt(p * (1 - p) / (n + 2))

    (level, strategy), items = max(groups.items(), key=lambda kv: lower_bound(kv[1]))
    wins = sum(1 for _, case in items if case.outcome in ("progress", "solved"))
    effectiveness = (wins + 1) / (len(items) + 2)
    provenances = {case.provenance for _, case in items}
    provenance = "live" if provenances == {"live"} else ("synthetic" if provenances == {"synthetic"} else "mixed")
    if len(items) < MIN_SUPPORT:
        return RetrievalOutput(reliable=False, reason="No single approach has enough support among similar situations.", candidates_considered=len(pool))
    return RetrievalOutput(
        reliable=True, reason="Similar situations were found.", candidates_considered=len(pool),
        suggested_level=level, suggested_strategy=strategy, effectiveness=round(effectiveness, 3), support=len(items),
        provenance=provenance, mean_similarity=round(sum(s for s, _ in items) / len(items), 3),
        evidence=[{
            "level": lvl, "strategy": strat, "cases": len(group_items),
            "successes": sum(1 for _, c in group_items if c.outcome in ("progress", "solved")),
        } for (lvl, strat), group_items in sorted(groups.items())],
    )
