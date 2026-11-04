"""
Progress calculations
"""

def calculate_concept_progress(mastery_probability: float) -> int:
    """
    ConceptProgress = MasteryProbability * 100
    """
    mastery = max(0.0, min(1.0, float(mastery_probability)))
    return int(round(mastery * 100.0))


def calculate_overall_progress(concept_states: list[dict]) -> float:
    """
    Overall learner progress is a weighted average over the learner's relevant concepts.
    We just use an equal weighting over all concepts they have interacted with.
    """
    if not concept_states:
        return 0.0

    total_mastery = sum(state.get("mastery", 0.0) for state in concept_states)
    average_mastery = total_mastery / len(concept_states)
    return round(average_mastery, 2)
