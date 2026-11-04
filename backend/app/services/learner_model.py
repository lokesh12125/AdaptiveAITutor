"""
Helper functions for learner modeling that are still needed outside the new learning package.
(Heuristics have been moved to the exact mathematical formulations in backend.app.learning)
"""

DEFAULT_PRIOR = 0.20


def build_8d_profile_vector(learner_state: dict) -> list[float]:
    """Construct a normalized 8-dimensional learner profile vector for ChromaDB similarity matching.
    
    Dimensions:
    1. mastery [0-1]
    2. confidence [0-1]
    3. confusion [0-1]
    4. cognitive_load [0-1]
    5. progress [0-1]
    6. hints_ratio [0-1] (hints / attempts)
    7. error_frequency [0-1] (fails / attempts)
    8. normalized response time [0-1] (capped at 120s)
    """
    attempts = max(1, learner_state.get("attempts", 1))
    hints_used = learner_state.get("hints_used", 0)
    fails = max(0, attempts - learner_state.get("solved_count", 0))
    resp_time = learner_state.get("response_time", 0.0)
    
    return [
        round(max(0.0, min(1.0, float(learner_state.get("mastery", DEFAULT_PRIOR)))), 3),
        round(max(0.0, min(1.0, float(learner_state.get("confidence", 0.5)))), 3),
        round(max(0.0, min(1.0, float(learner_state.get("confusion", 0.2)))), 3),
        round(max(0.0, min(1.0, float(learner_state.get("cognitive_load", 0.3)))), 3),
        round(max(0.0, min(1.0, float(learner_state.get("progress", 0.0)))), 3),
        round(min(1.0, hints_used / attempts), 3),
        round(min(1.0, fails / attempts), 3),
        round(min(1.0, resp_time / 120.0), 3),
    ]
