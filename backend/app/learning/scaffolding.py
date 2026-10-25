"""
Adaptive Scaffolding
"""

def calculate_scaffolding_score(
    mastery: float,
    confidence: float,
    confusion: float,
    cognitive_load: float,
    hint_dependence: float,
    time_stress: float
) -> float:
    """
    Dynamic Scaffolding Difficulty Adaptation score.
    S = 0.30 * (1 - Mastery) + 0.20 * (1 - Confidence) + 0.20 * Confusion + 
        0.15 * CognitiveLoad + 0.10 * HintDependence + 0.05 * TimeStress
    """
    s = (
        0.30 * (1.0 - mastery) +
        0.20 * (1.0 - confidence) +
        0.20 * confusion +
        0.15 * cognitive_load +
        0.10 * hint_dependence +
        0.05 * time_stress
    )
    return max(0.0, min(1.0, s))


def determine_scaffolding_level(scaffolding_score: float) -> int:
    """
    Map score to scaffold levels:
    0.00 - 0.25: Level 1 (Conceptual hint)
    0.25 - 0.50: Level 2 (Structural guidance / pseudocode)
    0.50 - 0.75: Level 3 (Targeted debugging guidance)
    0.75 - 1.00: Level 4 (Detailed guidance without directly dumping the complete solution)
    """
    score = max(0.0, min(1.0, scaffolding_score))
    if score <= 0.25:
        return 1
    elif score <= 0.50:
        return 2
    elif score <= 0.75:
        return 3
    else:
        return 4
