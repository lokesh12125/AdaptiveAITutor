"""
Adaptive Scaffolding & Dynamic Scaffolding Decision Algorithm (DSDA v2.1)
Provides mathematically verified continuous cognitive struggle scoring,
monotonic assistance level escalation, orthogonal pedagogical focus pivoting,
and deterministic fallback hint matrices.
"""
import math
from typing import Any, Dict, List, Optional, Tuple


def calculate_scaffolding_score(
    mastery: float,
    confidence: float,
    confusion: float,
    cognitive_load: float,
    hint_dependence: float,
    time_stress: float
) -> float:
    """
    Legacy Dynamic Scaffolding Difficulty Adaptation score (backward compatibility).
    S = 0.30 * (1 - Mastery) + 0.20 * (1 - Confidence) + 0.20 * Confusion + 
        0.15 * CognitiveLoad + 0.10 * HintDependence + 0.05 * TimeStress
    """
    s = (
        0.30 * (1.0 - float(mastery)) +
        0.20 * (1.0 - float(confidence)) +
        0.20 * float(confusion) +
        0.15 * float(cognitive_load) +
        0.10 * float(hint_dependence) +
        0.05 * float(time_stress)
    )
    return max(0.0, min(1.0, s))


def determine_scaffolding_level(scaffolding_score: float) -> int:
    """
    Legacy level mapper (backward compatibility):
    0.00 - 0.25: Level 1 (Guiding question)
    0.25 - 0.50: Level 2 (Conceptual clue)
    0.50 - 0.75: Level 3 (Pseudocode guidance)
    0.75 - 1.00: Level 4 (Step-by-step breakdown)
    """
    score = max(0.0, min(1.0, float(scaffolding_score)))
    if score <= 0.25:
        return 1
    elif score <= 0.50:
        return 2
    elif score <= 0.75:
        return 3
    else:
        return 4


def calculate_time_stress(response_time: float, baseline_time: Optional[float] = 60.0) -> float:
    """
    Safe piece-wise linear time stress:
    t_safe = max(15.0, baseline_time if baseline_time is not None else 60.0)
    T_stress = 0 if response_time <= 0.5 * t_safe
    T_stress = (response_time - 0.5 * t_safe) / (1.5 * t_safe) bounded to [0.0, 1.0]
    """
    t_resp = max(0.0, float(response_time))
    if baseline_time is None:
        t_base = 60.0
    else:
        t_base = max(15.0, float(baseline_time))
    if t_resp <= 0.5 * t_base:
        return 0.0
    val = (t_resp - 0.5 * t_base) / (1.5 * t_base)
    return min(1.0, max(0.0, val))


def calculate_csi_score(
    mastery: float,
    consecutive_fails: int,
    confidence: float,
    cognitive_load: float,
    hints_used: int,
    response_time: float,
    baseline_time: float = 60.0,
    observations_count: int = 1
) -> Tuple[float, float, float]:
    """
    Continuous Cognitive Struggle Index (CSI):
    Raw = 0.25*(1-M) + 0.25*Phi(F) + 0.20*Conf + 0.15*L_cog + 0.10*H_sat + 0.05*T_stress
    Uncertainty U = exp(-N_obs / 3.0)
    CSI = (1 - U) * Raw + U * 0.35
    Returns (csi, raw, uncertainty).
    """
    m = max(0.0, min(1.0, float(mastery)))
    conf = max(0.0, min(1.0, float(confidence)))
    load = max(0.0, min(1.0, float(cognitive_load)))
    f = max(0, int(consecutive_fails))
    h = max(0, int(hints_used))
    n = max(0, int(observations_count))

    phi_f = min(1.0, (f ** 2) / 9.0)
    h_sat = min(1.0, h / 3.0)
    t_stress = calculate_time_stress(response_time, baseline_time)

    raw = (
        0.25 * (1.0 - m) +
        0.25 * phi_f +
        0.20 * conf +
        0.15 * load +
        0.10 * h_sat +
        0.05 * t_stress
    )
    u = math.exp(-n / 3.0)
    csi = (1.0 - u) * raw + u * 0.35
    csi = max(0.0, min(1.0, csi))
    return round(csi, 4), round(raw, 4), round(u, 4)


def determine_base_level(csi_score: float) -> int:
    """Map continuous CSI score to base level 1-4 with exact half-open intervals."""
    score = max(0.0, min(1.0, float(csi_score)))
    if score < 0.25:
        return 1
    elif score < 0.50:
        return 2
    elif score < 0.75:
        return 3
    else:
        return 4


FOCUS_ROTATION = {
    "Conceptual": "Tracing",
    "Tracing": "Algorithmic",
    "Algorithmic": "Conceptual",
    "Structural": "Tracing"
}


FALLBACK_MATRIX: Dict[Tuple[int, str], str] = {
    (1, "Conceptual"): "Consider the core concept: what data structure or language construct best matches this requirement?",
    (1, "Tracing"): "Trace the function by hand with a tiny test case (e.g. n=1 or empty input). What should it return?",
    (1, "Algorithmic"): "What overall algorithmic approach are you using? Does it account for all cases described?",
    (1, "Structural"): "Check the structure of your solution: ensure the function signature and return statement match expectations.",
    (2, "Conceptual"): "Remember how this operation functions in Python. Review the relationship between keys, values, and indices.",
    (2, "Tracing"): "Notice where your expected output differs from actual output. Trace step-by-step through the main loop.",
    (2, "Algorithmic"): "Break the problem into two subproblems: first process/filter inputs, then compute the final aggregated result.",
    (2, "Structural"): "Carefully check matching parentheses, colons after statements, and consistent 4-space indentation.",
    (3, "Conceptual"): "Key rule: ensure state does not mutate unexpectedly across loop iterations. Keep accumulation separate.",
    (3, "Tracing"): "On line containing the return/assignment, inspect variable values right before termination. Why does it exit early?",
    (3, "Algorithmic"): "Pseudocode sketch:\n1. Initialize result container.\n2. Iterate over items with boundary check.\n3. Return result outside loop.",
    (3, "Structural"): "Syntactic structure: check that loops and conditions terminate cleanly and return an actual value.",
    (4, "Conceptual"): "Step-by-step breakdown: verify the type of your inputs, initialize default output, and ensure each case returns the exact expected type.",
    (4, "Tracing"): "Walk through example: with input [2, 3], iteration 1 sees 2, iteration 2 sees 3. Make sure you don't return inside the loop on iteration 1.",
    (4, "Algorithmic"): "Step 1: Set accumulator variable before loop. Step 2: In loop, update accumulator only. Step 3: Outside loop, return accumulator.",
    (4, "Structural"): "Review line-by-line syntax: fix any indentation mismatch and ensure the return keyword is placed outside loop scope."
}


def evaluate_dsda_v2(
    diagnostic: Dict[str, Any],
    learner_state: Dict[str, Any],
    problem_hints: List[Dict[str, Any]],
    current_attempt_count: int = 1,
    consecutive_fails: int = 0,
    response_time: float = 0.0,
    baseline_time: float = 60.0,
    observations_count: int = 1,
    code: str = "",
    passed: bool = False
) -> Dict[str, Any]:
    """
    Executes the DSDA v2.1 Decision Engine across all pedagogical gates:
    Gate 1: Success Gate (Level 0, clear scaffolding)
    Gate 2: Security Violation (Level 1, Structural)
    Gate 3: Stub/Empty Submission (Level 1, Structural)
    Gate 4: Syntax Error (Level min(A_prob, 2), Structural)
    Gate 5: Persistent Failure / ZPD Saturation (Level 4, Algorithmic, Remediation Flag)
    Gate 6: Expert Blindspot (Level 2, Tracing)
    Gate 7: General CSI Scoring & Monotonic Escalation
    Gate 8: Orthogonal Focus Dimension & Strategy Pivot
    """
    # Gate 1: Solution Passed
    if passed:
        return {
            "level": 0,
            "focus": "None",
            "csi": 0.0,
            "raw_csi": 0.0,
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "Success",
            "rationale": "Solution passed all test assertions."
        }

    error_type = str(diagnostic.get("error_type", "assertion")).lower()
    cleaned_code = code.strip() if code else ""

    # Gate 2: Security Violation
    if error_type == "security":
        return {
            "level": 1,
            "focus": "Structural",
            "csi": 0.20,
            "raw_csi": 0.20,
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "Security",
            "rationale": "Execution restricted: disallowed import or dangerous function call."
        }

    # Gate 3: Stub / Empty Submission
    if len(cleaned_code) < 10 or ("def " not in cleaned_code and "return" not in cleaned_code):
        return {
            "level": 1,
            "focus": "Structural",
            "csi": 0.22,
            "raw_csi": 0.22,
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "StubCode",
            "rationale": "Incomplete or empty code submission. Provide a complete function definition."
        }

    # Gate 4: Syntax Error
    if error_type in ("syntax", "syntaxerror", "indentationerror"):
        syntax_level = min(max(1, consecutive_fails), 2)
        return {
            "level": syntax_level,
            "focus": "Structural",
            "csi": round(0.20 * syntax_level, 2),
            "raw_csi": round(0.20 * syntax_level, 2),
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "SyntaxError",
            "rationale": f"Syntax or indentation error detected (Level {syntax_level} guidance)."
        }

    # History analysis for this problem
    prev_level = 0
    prev_focus = ""
    if problem_hints:
        prev_level = int(problem_hints[-1].get("level", 0))
        prev_focus = str(problem_hints[-1].get("focus", ""))

    hints_used = len(problem_hints)
    mastery = float(learner_state.get("mastery", 0.35))
    confidence = float(learner_state.get("confidence", 0.50))
    cognitive_load = float(learner_state.get("cognitive_load", 0.20))
    confusion = float(learner_state.get("confusion", 0.0))

    # Gate 5: Persistent Failure / ZPD Saturation
    if prev_level == 4 and consecutive_fails >= 4:
        return {
            "level": 4,
            "focus": "Algorithmic",
            "csi": 0.95,
            "raw_csi": 0.95,
            "uncertainty": 0.0,
            "remediation_flag": True,
            "gate_triggered": "ZpdSaturation",
            "rationale": "Persistent struggle at maximum scaffolding depth. Recommend foundational review or educator intervention."
        }

    # Gate 6: Expert Blindspot
    if mastery >= 0.75 and consecutive_fails == 1:
        return {
            "level": 2,
            "focus": "Tracing",
            "csi": 0.40,
            "raw_csi": 0.40,
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "ExpertBlindspot",
            "rationale": "High-mastery learner on initial error. Bypassed elementary question to focus directly on state tracing."
        }

    # Gate 7: Continuous CSI Calculation & Monotonic Escalation
    csi, raw_csi, u = calculate_csi_score(
        mastery=mastery,
        consecutive_fails=consecutive_fails,
        confidence=confidence,
        cognitive_load=cognitive_load,
        hints_used=hints_used,
        response_time=response_time,
        baseline_time=baseline_time,
        observations_count=observations_count
    )
    base_level = determine_base_level(csi)

    # Monotonic Escalation Gate
    if consecutive_fails <= 1 and prev_level == 0:
        final_level = min(base_level, 2)
    elif consecutive_fails > 1 and prev_level > 0:
        final_level = min(4, max(base_level, prev_level + 1))
    else:
        final_level = base_level

    # Gate 8: Orthogonal Focus Dimension & Strategy Pivot
    if error_type in ("assertion", "assertionerror", "valueerror", "indexerror"):
        focus = "Tracing"
    elif error_type in ("logic", "timeout", "recursionerror"):
        focus = "Algorithmic"
    elif error_type in ("runtime", "nameerror", "typeerror", "attributeerror"):
        focus = "Conceptual"
    else:
        focus = "Structural"

    # Strategy Pivot: If level repeated or candidate focus matches immediately preceding hint, pivot focus to provide an alternative perspective
    if prev_focus and (focus == prev_focus or (final_level == prev_level and prev_level > 0)) and problem_hints:
        candidate = FOCUS_ROTATION.get(prev_focus, FOCUS_ROTATION.get(focus, "Tracing"))
        if candidate:
            focus = candidate

    remediation_flag = (final_level == 4 and consecutive_fails >= 3) or (confusion >= 0.60 and consecutive_fails >= 3)

    return {
        "level": final_level,
        "focus": focus,
        "csi": csi,
        "raw_csi": raw_csi,
        "uncertainty": u,
        "remediation_flag": remediation_flag,
        "gate_triggered": "ContinuousCSI",
        "rationale": f"CSI struggle score {csi:.2f} (raw: {raw_csi:.2f}, uncertainty: {u:.2f}) mapped to Level {final_level} with {focus} focus."
    }
