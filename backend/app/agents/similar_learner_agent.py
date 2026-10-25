"""Similar Learner Retrieval Agent for querying nearest 8D profile vectors from ChromaDB."""
from typing import Any, Dict

from ..graph.state import TutorState
from ..services.learner_model import build_8d_profile_vector
from ..services.vector_store import vector_store


class SimilarLearnerAgent:
    """Agent responsible for constructing 8D learner profile feature vectors

    and querying ChromaDB for nearest historical student profiles and intervention strategies.
    """

    def execute(self, state: TutorState) -> Dict[str, Any]:
        """Construct profile vector, perform k-NN vector search in ChromaDB, and retrieve intervention."""
        learner = state.get("learner_state", {})
        vector_8d = build_8d_profile_vector(learner)
        retrieved = vector_store.query_similar_learners(vector_8d, n_results=2)

        active_intervention = (
            retrieved[0]["intervention"]
            if retrieved
            else "Provide structured Socratic guidance based on observable test evidence."
        )

        return {
            "similar_learners": retrieved,
            "active_intervention": active_intervention,
            "agent_activity": ["Similar Learner Retrieval Agent"],
        }
