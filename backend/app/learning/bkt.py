"""
Mastery: Bayesian Knowledge Tracing

Based on:
Corbett and Anderson, "Knowledge Tracing: Modeling the Acquisition of Procedural Knowledge,"
User Modeling and User-Adapted Interaction, 1995.
DOI: 10.1007/BF01099821
"""

# Initial Engineering Parameters
DEFAULT_P_L0 = 0.20
DEFAULT_P_T = 0.15
DEFAULT_P_G = 0.20
DEFAULT_P_S = 0.10


def update_mastery(
    prior_mastery: float,
    passed: bool,
    p_t: float = DEFAULT_P_T,
    p_g: float = DEFAULT_P_G,
    p_s: float = DEFAULT_P_S
) -> float:
    """
    Calculate posterior concept mastery using exact Bayesian Knowledge Tracing (BKT).
    """
    p_k = max(0.0, min(1.0, float(prior_mastery)))

    if passed:
        # P(correct) = P(K) * (1 - P(S)) + (1 - P(K)) * P(G)
        p_obs = p_k * (1.0 - p_s) + (1.0 - p_k) * p_g
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
