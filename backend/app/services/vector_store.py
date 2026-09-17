"""Local ChromaDB vector service for storing and querying 8D learner profile similarity vectors."""
import logging
from pathlib import Path
import chromadb

from ..config import BACKEND_DIR

logger = logging.getLogger("tutor.vector_store")
CHROMA_DIR = BACKEND_DIR / "chroma_db"

# Consistent 8-feature dimensions:
# [mastery, confidence, confusion, cognitive_load, progress, hints_ratio, error_frequency, response_time]
FEATURE_KEYS = [
    "mastery",
    "confidence",
    "confusion",
    "cognitive_load",
    "progress",
    "hints_ratio",
    "error_frequency",
    "response_time",
]

DEFAULT_PROFILES = [
    {
        "id": "synthetic-struggling-syntax",
        "vector": [0.25, 0.30, 0.75, 0.70, 0.15, 0.80, 0.70, 0.40],
        "metadata": {
            "archetype": "struggling-syntax",
            "concept": "syntax-errors",
            "intervention": "Break down syntax rules, isolate the offending line, and check matching delimiters."
        }
    },
    {
        "id": "synthetic-moderate-logic",
        "vector": [0.55, 0.50, 0.45, 0.40, 0.50, 0.40, 0.35, 0.30],
        "metadata": {
            "archetype": "moderate-logic",
            "concept": "loops-and-conditions",
            "intervention": "Provide pseudocode structure and prompt tracing on small sample inputs."
        }
    },
    {
        "id": "synthetic-advanced-optimization",
        "vector": [0.85, 0.80, 0.15, 0.20, 0.85, 0.10, 0.10, 0.20],
        "metadata": {
            "archetype": "advanced-optimization",
            "concept": "algorithms",
            "intervention": "Challenge with edge cases and prompt explanation of algorithmic time complexity."
        }
    },
    {
        "id": "synthetic-rapid-guessing",
        "vector": [0.30, 0.60, 0.65, 0.55, 0.25, 0.20, 0.80, 0.05],
        "metadata": {
            "archetype": "rapid-guessing",
            "concept": "debugging",
            "intervention": "Slow down the pace: prompt prediction of program state before running code."
        }
    }
]


class VectorStoreService:
    def __init__(self) -> None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        try:
            self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            self._collection = self._client.get_or_create_collection(
                name="learner_profiles",
                metadata={"description": "8D learner profile similarity vectors and interventions"}
            )
            self._seed_defaults_if_empty()
            self._initialized = True
        except Exception as e:
            logger.error("Failed to initialize local ChromaDB client: %s", e)
            self._client = None
            self._collection = None
            self._initialized = False

    def _seed_defaults_if_empty(self) -> None:
        if self._collection is None:
            return
        count = self._collection.count()
        if count == 0:
            ids = [p["id"] for p in DEFAULT_PROFILES]
            embeddings = [p["vector"] for p in DEFAULT_PROFILES]
            metadatas = [p["metadata"] for p in DEFAULT_PROFILES]
            documents = [p["metadata"]["intervention"] for p in DEFAULT_PROFILES]
            self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)
            logger.info("Seeded %d default learner profiles in ChromaDB.", len(ids))

    def status(self) -> str:
        if self._initialized and self._collection is not None:
            return "ok"
        return "error"

    def count(self) -> int:
        return self._collection.count() if self._collection is not None else 0

    def query_similar_learners(self, vector: list[float], n_results: int = 2) -> list[dict]:
        """Query top-k nearest learner profile vectors and return their interventions."""
        if not self._initialized or self._collection is None:
            return []
        try:
            norm_vector = (vector + [0.0] * 8)[:8]
            results = self._collection.query(
                query_embeddings=[norm_vector],
                n_results=min(n_results, max(1, self._collection.count()))
            )
            items = []
            if results and "ids" in results and results["ids"]:
                ids = results["ids"][0]
                distances = results.get("distances", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                for i, profile_id in enumerate(ids):
                    dist = distances[i] if i < len(distances) else 0.0
                    sim = max(0.0, min(1.0, round(1.0 - (dist / 2.0), 2)))
                    meta = metadatas[i] if i < len(metadatas) else {}
                    items.append({
                        "id": profile_id,
                        "similarity": sim,
                        "intervention": meta.get("intervention", "Provide targeted guidance based on error context."),
                        "archetype": meta.get("archetype", "learner"),
                        "concept": meta.get("concept", "general")
                    })
            return items
        except Exception as e:
            logger.warning("ChromaDB query failed: %s", e)
            return []

    def record_learner_profile(self, profile_id: str, vector: list[float], intervention: str, archetype: str = "custom") -> None:
        """Store or update a learner profile feature vector in ChromaDB."""
        if not self._initialized or self._collection is None:
            return
        try:
            norm_vector = (vector + [0.0] * 8)[:8]
            self._collection.upsert(
                ids=[profile_id],
                embeddings=[norm_vector],
                metadatas=[{"archetype": archetype, "intervention": intervention}],
                documents=[intervention]
            )
        except Exception as e:
            logger.warning("Failed to upsert learner profile to ChromaDB: %s", e)


vector_store = VectorStoreService()
