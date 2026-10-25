"""
Cognitive Load: Behavior-Based Cognitive Load Indicator
"""

def calculate_time_stress(response_time: float, baseline_response_time: float = 60.0) -> float:
    """
    TimeStress = min(response_time / baseline_response_time, 1.0)
    """
    if baseline_response_time <= 0:
        baseline_response_time = 60.0
    if response_time < 0:
        response_time = 0.0
        
    return min(response_time / baseline_response_time, 1.0)


def calculate_attempt_stress(attempt_count: int) -> float:
    """
    AttemptStress = min((attempt_count - 1) / 3.0, 1.0)
    """
    if attempt_count < 1:
        attempt_count = 1
    return min((attempt_count - 1) / 3.0, 1.0)


def calculate_error_stress(recent_errors: int) -> float:
    """
    ErrorStress = min(recent_errors_for_concept / 3.0, 1.0)
    """
    if recent_errors < 0:
        recent_errors = 0
    return min(recent_errors / 3.0, 1.0)


def calculate_hint_stress(hints_used: int) -> float:
    """
    HintStress = min(hints_used / 3.0, 1.0)
    """
    if hints_used < 0:
        hints_used = 0
    return min(hints_used / 3.0, 1.0)


def calculate_load_signal(
    time_stress: float,
    attempt_stress: float,
    error_stress: float,
    hint_stress: float
) -> float:
    """
    LoadSignal = 0.35 * TimeStress + 0.25 * AttemptStress + 0.20 * ErrorStress + 0.20 * HintStress
    """
    signal = (
        0.35 * time_stress +
        0.25 * attempt_stress +
        0.20 * error_stress +
        0.20 * hint_stress
    )
    return max(0.0, min(1.0, signal))


def update_cognitive_load(prior_load: float, load_signal: float, alpha: float = 0.70) -> float:
    """
    CognitiveLoad_t = alpha * CognitiveLoad_previous + (1 - alpha) * LoadSignal
    """
    prior = max(0.0, min(1.0, float(prior_load)))
    sig = max(0.0, min(1.0, float(load_signal)))
    
    updated = alpha * prior + (1.0 - alpha) * sig
    return max(0.0, min(1.0, updated))
