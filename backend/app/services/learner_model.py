"""Algorithmic learner-state engine: Bayesian Knowledge Tracing (BKT), confidence, confusion, and interaction-based cognitive-load proxy."""
import math

# Standard BKT Parameters
DEFAULT_PRIOR = 0.35
P_TRANSIT = 0.15   # P(T): Probability of learning transition after an attempt
P_SLIP = 0.10      # P(S): Probability of making an error despite knowing the concept
P_GUESS = 0.20     # P(G): Probability of answering correctly by chance


def update_bkt_mastery(prior_mastery: float, passed: bool, slip: float = P_SLIP, guess: float = P_GUESS, transit: float = P_TRANSIT) -> float:
    """Calculate posterior concept mastery using exact Bayesian Knowledge Tracing (BKT)."""
    p_l = max(0.01, min(0.99, prior_mastery))
    if passed:
        # P(L | correct) = (P(L) * (1 - S)) / (P(L) * (1 - S) + (1 - P(L)) * G)
        numerator = p_l * (1.0 - slip)
        denominator = numerator + (1.0 - p_l) * guess
    else:
        # P(L | incorrect) = (P(L) * S) / (P(L) * S + (1 - P(L)) * (1 - G))
        numerator = p_l * slip
        denominator = numerator + (1.0 - p_l) * (1.0 - guess)
    
    p_l_obs = numerator / (denominator or 1.0)
    # Transition to learned state: P(L_t) = P(L_obs) + (1 - P(L_obs)) * P(T)
    posterior = p_l_obs + (1.0 - p_l_obs) * transit
    return round(max(0.01, min(0.99, posterior)), 3)


def calculate_confidence(prior_confidence: float, passed: bool, hints_used: int, response_time: float) -> float:
    """Calculate confidence from interaction evidence (pass streak, hint-free success, pacing)."""
    p_conf = max(0.05, min(0.95, prior_confidence))
    if passed:
        boost = 0.12 if hints_used == 0 else 0.06
        # Quick, confident responses (10s - 90s) give a small bonus
        if 5.0 <= response_time <= 90.0:
            boost += 0.03
        updated = p_conf + boost * (1.0 - p_conf)
    else:
        penalty = 0.08 + (0.04 * min(hints_used, 3))
        updated = p_conf - penalty * p_conf
    return round(max(0.05, min(0.95, updated)), 3)


def calculate_confusion(prior_confusion: float, passed: bool, error_type: str, consecutive_fails: int, hints_used: int) -> float:
    """Estimate confusion from observable signals (repeated failures, recurring error types, high hint consumption)."""
    p_conf = max(0.0, min(1.0, prior_confusion))
    if passed:
        # Success dispels confusion
        updated = max(0.0, p_conf - 0.25)
    else:
        # Repeated failure or syntax/assertion error escalates confusion
        escalation = 0.12
        if consecutive_fails > 1:
            escalation += 0.08 * min(consecutive_fails, 4)
        if hints_used > 1:
            escalation += 0.05 * min(hints_used, 3)
        if error_type in ("syntax", "assertion"):
            escalation += 0.05
        updated = min(1.0, p_conf + escalation)
    return round(max(0.0, min(1.0, updated)), 3)


def calculate_cognitive_load_proxy(concept_mastery: float, difficulty: str, hints_used: int, response_time: float, passed: bool) -> float:
    """Calculate an interaction-based cognitive-load proxy from task difficulty, mastery gap, response time, and hints.
    
    NOTE: This is strictly an observable interaction-based proxy, NOT a psychological diagnosis.
    """
    diff_weights = {"easy": 0.20, "medium": 0.50, "hard": 0.85}
    diff_val = diff_weights.get(difficulty.lower(), 0.40)
    
    mastery_gap = max(0.0, 1.0 - concept_mastery)
    pacing_proxy = min(1.0, max(0.0, response_time / 150.0))
    hint_proxy = min(1.0, hints_used / 4.0)
    
    raw_load = (
        0.35 * mastery_gap +
        0.25 * diff_val +
        0.20 * hint_proxy +
        0.20 * pacing_proxy
    )
    if passed and hints_used == 0:
        raw_load = max(0.10, raw_load - 0.15)
    return round(max(0.05, min(0.98, raw_load)), 3)


def calculate_concept_progress(mastery: float, solved_count: int, total_problems: int = 2) -> int:
    """Calculate concept-wise progress percentage deterministically."""
    solved_ratio = min(1.0, solved_count / max(1, total_problems))
    # 60% weight on mastery, 40% on actual task completion
    val = (0.60 * mastery + 0.40 * solved_ratio) * 100.0
    return int(round(min(100, max(0, val))))


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
