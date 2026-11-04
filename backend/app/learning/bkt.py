"""
Mastery: Bayesian Knowledge Tracing

Based on:
Corbett and Anderson, "Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge,"
User Modeling and User-Adapted Interaction, 1995.
DOI: 10.1007/BF01099821
"""

from ..config import BKT_P_G, BKT_P_L0, BKT_P_S, BKT_P_T

# Initial Engineering Parameters (configured via app.config)
DEFAULT_P_L0 = BKT_P_L0
DEFAULT_P_T = BKT_P_T
DEFAULT_P_G = BKT_P_G
DEFAULT_P_S = BKT_P_S


def update_mastery(
    prior_mastery: float,
    passed: bool,
    p_t: float = DEFAULT_P_T,
    p_g: float = DEFAULT_P_G,
    p_s: float = DEFAULT_P_S,
    hints_used: int = 0
) -> float:
    """
    Calculate posterior concept mastery using exact Bayesian Knowledge Tracing (BKT).

    V-01: When hints_used > 0 on a passed attempt, effective guess probability P(G)
    is elevated proportionally to reflect external scaffolding assistance, dampening
    unearned mastery jumps.
    """
    p_k = max(0.0, min(1.0, float(prior_mastery)))
    effective_p_g = min(0.60, p_g + 0.05 * max(0, hints_used)) if (passed and hints_used > 0) else p_g

    if passed:
        # P(correct) = P(K) * (1 - P(S)) + (1 - P(K)) * P(G)
        p_obs = p_k * (1.0 - p_s) + (1.0 - p_k) * effective_p_g
        # P(K | correct) = [P(K) * (1 - P(S))] / P(correct)
        if p_obs > 0.0:
            p_k_given_obs = (p_k * (1.0 - p_s)) / p_obs
        else:
            p_k_given_obs = 0.0
    else:
        # P(incorrect) = P(K) * P(S) + (1 - P(K)) * (1 - P(G))
        p_obs = p_k * p_s + (1.0 - p_k) * (1.0 - p_g)
        # P(K | incorrect) = [P(K) * P(S)] / P(incorrect)
        if p_obs > 0.0:
            p_k_given_obs = (p_k * p_s) / p_obs
        else:
            p_k_given_obs = 0.0

    # P(K_new) = P(K | obs) + (1 - P(K | obs)) * P(T)
    p_k_new = p_k_given_obs + (1.0 - p_k_given_obs) * p_t

    return max(0.0, min(1.0, p_k_new))
