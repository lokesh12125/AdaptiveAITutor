"""
Confusion: Behavioral Confusion Estimator
"""

def calculate_confusion_signal(
    passed: bool,
    consecutive_fails: int,
    hints_used: int
) -> float:
    """
    Construct a normalized confusion signal.
    ConfusionSignal = 0.50 * RepeatError + 0.30 * Failure + 0.20 * HintDependence
    """
    if passed:
        # If passed, failure signal is 0. 
        # Hint dependence might still exist if hints were used, and repeat errors might have happened before.
        # But generally passing drastically reduces current interaction's confusion signal.
        failure_signal = 0.0
    else:
        failure_signal = 1.0

    # RepeatError represents repeated mistakes related to the same concept.
    repeat_error_signal = min((consecutive_fails) / 3.0, 1.0) if not passed else 0.0

    # Hint Dependence
    hint_dependence_signal = min(hints_used / 3.0, 1.0)

    signal = (
        0.50 * repeat_error_signal +
        0.30 * failure_signal +
        0.20 * hint_dependence_signal
    )
    
    return max(0.0, min(1.0, signal))


def update_confusion(prior_confusion: float, confusion_signal: float, alpha: float = 0.70) -> float:
    """
    Update confusion using an Exponentially Weighted Moving Average (EWMA).
    """
    prior = max(0.0, min(1.0, float(prior_confusion)))
    sig = max(0.0, min(1.0, float(confusion_signal)))
    
    updated = alpha * prior + (1.0 - alpha) * sig
    return max(0.0, min(1.0, updated))
