"""
Confidence: EWMA Behavioral Confidence Estimator
"""

def calculate_confidence_evidence(
    passed: bool,
    hints_used: int,
    consecutive_fails: int
) -> float:
    """
    Calculate confidence evidence based on observable interaction behavior.
    """
    if passed:
        if hints_used == 0:
            return 1.00
        else:
            return max(0.40, 0.70 - 0.10 * (hints_used - 1))
    else:
        evidence = 0.20
        if consecutive_fails > 1:
            evidence = max(0.0, evidence - 0.10 * (consecutive_fails - 1))
        return evidence


def update_confidence(prior_confidence: float, evidence: float, alpha: float = 0.70) -> float:
    """
    Update confidence using an Exponentially Weighted Moving Average (EWMA).
    """
    prior = max(0.0, min(1.0, float(prior_confidence)))
    ev = max(0.0, min(1.0, float(evidence)))
    
    updated = alpha * prior + (1.0 - alpha) * ev
    return max(0.0, min(1.0, updated))
