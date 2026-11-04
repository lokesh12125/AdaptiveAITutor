"""
Adaptive Scaffolding & Dynamic Scaffolding Decision Algorithm (DSDA v2.1)
Provides mathematically verified continuous cognitive struggle scoring,
monotonic assistance level escalation, orthogonal pedagogical focus pivoting,
and deterministic fallback hint matrices.
"""
import ast
import math
from typing import Any, Dict, List, Optional, Tuple


def _sanitize_float(val: Any, default: float, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """Safely convert and clamp numeric inputs, rejecting NaN, Inf, None, and out-of-range values."""
    if val is None:
        num = default
    else:
        try:
            num = float(val)
            if math.isnan(num) or math.isinf(num):
                num = default
        except (TypeError, ValueError):
            num = default
    if min_val is not None:
        num = max(min_val, num)
    if max_val is not None:
        num = min(max_val, num)
    return num


def _sanitize_int(val: Any, default: int, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """Safely convert and clamp integer inputs, rejecting NaN, Inf, None, and negative counters."""
    if val is None:
        num = default
    else:
        try:
            f_val = float(val)
            if math.isnan(f_val) or math.isinf(f_val):
                num = default
            else:
                num = int(f_val)
        except (TypeError, ValueError):
            num = default
    if min_val is not None:
        num = max(min_val, num)
    if max_val is not None:
        num = min(max_val, num)
    return num


def is_code_stub(code: str) -> bool:
    """
    Explicitly analyze code AST and structure to detect starter-code stubs.
    Checks whether submission is empty or consists purely of 'pass', docstrings, comments, or ellipsis.
    Does NOT infer stubs merely from response time or missing returns.
    """
    cleaned = code.strip() if code else ""
    if not cleaned or len(cleaned) < 10:
        return True
    try:
        tree = ast.parse(cleaned)
        if not tree.body:
            return True
        for stmt in tree.body:
            if isinstance(stmt, ast.Pass):
                continue
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                # String docstrings or Ellipsis (...)
                if stmt.value.value is Ellipsis or isinstance(stmt.value.value, str):
                    continue
            if isinstance(stmt, ast.FunctionDef):
                # Check if function body is trivial (only pass, docstrings, or ellipsis)
                has_substance = False
                for s in stmt.body:
                    if isinstance(s, ast.Pass):
                        continue
                    if isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant):
                        continue
                    has_substance = True
                    break
                if has_substance:
                    return False
            else:
                # Top-level non-trivial code exists
                return False
        return True
    except SyntaxError:
        return False


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
    m = _sanitize_float(mastery, default=0.35, min_val=0.0, max_val=1.0)
    conf = _sanitize_float(confidence, default=0.50, min_val=0.0, max_val=1.0)
    confusion_val = _sanitize_float(confusion, default=0.00, min_val=0.0, max_val=1.0)
    load = _sanitize_float(cognitive_load, default=0.00, min_val=0.0, max_val=1.0)
    hint_dep = _sanitize_float(hint_dependence, default=0.00, min_val=0.0, max_val=1.0)
    t_stress = _sanitize_float(time_stress, default=0.00, min_val=0.0, max_val=1.0)

    s = (
        0.30 * (1.0 - m) +
        0.20 * (1.0 - conf) +
        0.20 * confusion_val +
        0.15 * load +
        0.10 * hint_dep +
        0.05 * t_stress
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
    score = _sanitize_float(scaffolding_score, default=0.25, min_val=0.0, max_val=1.0)
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
    t_safe = max(15.0, baseline_time if baseline_time is not None and baseline_time > 0 else 60.0)
    T_stress = clamp((response_time - 0.5 * t_safe) / (1.5 * t_safe), 0, 1)
    """
    t_resp = _sanitize_float(response_time, default=0.0, min_val=0.0)
    if baseline_time is None:
        t_base = 60.0
    else:
        raw_b = _sanitize_float(baseline_time, default=60.0)
        t_base = max(15.0, raw_b if raw_b > 0 else 15.0)

    if t_resp <= 0.5 * t_base:
        return 0.0
    val = (t_resp - 0.5 * t_base) / (1.5 * t_base)
    return max(0.0, min(1.0, val))


def calculate_csi_score(
    mastery: float,
    consecutive_fails: int,
    confidence: float,
    cognitive_load: float,
    hints_used: int,
    response_time: float,
    baseline_time: Optional[float] = 60.0,
    observations_count: int = 1
) -> Tuple[float, float, float]:
    """
    Continuous Cognitive Struggle Index (CSI):
    Raw = 0.25*(1-M) + 0.25*Phi(F) + 0.20*(1-Conf) + 0.15*L_cog + 0.10*H_sat + 0.05*T_stress
    Uncertainty U = exp(-N_obs / 3.0)
    CSI = (1 - U) * Raw + U * 0.35
    Returns (csi, raw, uncertainty) clamped strictly to [0.0, 1.0].
    """
    m = _sanitize_float(mastery, default=0.35, min_val=0.0, max_val=1.0)
    conf = _sanitize_float(confidence, default=0.50, min_val=0.0, max_val=1.0)
    load = _sanitize_float(cognitive_load, default=0.00, min_val=0.0, max_val=1.0)
    f = _sanitize_int(consecutive_fails, default=0, min_val=0)
    h = _sanitize_int(hints_used, default=0, min_val=0)
    n = _sanitize_int(observations_count, default=1, min_val=0)

    phi_f = min(1.0, (f ** 2) / 9.0)
    h_sat = min(1.0, h / 3.0)
    t_stress = calculate_time_stress(response_time, baseline_time)

    # C-06 fix: Struggle increases with lack of confidence (1.0 - conf), not high confidence!
    raw = (
        0.25 * (1.0 - m) +
        0.25 * phi_f +
        0.20 * (1.0 - conf) +
        0.15 * load +
        0.10 * h_sat +
        0.05 * t_stress
    )
    u = math.exp(-n / 3.0)
    csi = (1.0 - u) * raw + u * 0.35
    csi = max(0.0, min(1.0, csi))
    raw = max(0.0, min(1.0, raw))
    u = max(0.0, min(1.0, u))
    return round(csi, 4), round(raw, 4), round(u, 4)


def determine_base_level(csi_score: float) -> int:
    """Map continuous CSI score to base level 1-4 with exact half-open intervals."""
    score = _sanitize_float(csi_score, default=0.25, min_val=0.0, max_val=1.0)
    if score < 0.25:
        return 1
    elif score < 0.50:
        return 2
    elif score < 0.75:
        return 3
    else:
        return 4


def calculate_escalated_level(prev_level: int, base_level: int, consecutive_fails: int) -> int:
    """
    Monotonic Escalation Invariant:
    - Initial hint (prev_level == 0 or consecutive_fails <= 1): capped at min(2, base_level).
    - Repeated failure on same problem: L_next = min(4, max(L_prev, min(L_base, L_prev + 1))).
      - The level must not decrease solely because L_base is lower (max(L_prev, ...)).
      - The level increases by AT MOST ONE level per failure (min(L_base, L_prev + 1)).
      - The level cannot exceed Level 4 (min(4, ...)).
    """
    p_lvl = _sanitize_int(prev_level, default=0, min_val=0, max_val=4)
    b_lvl = _sanitize_int(base_level, default=1, min_val=1, max_val=4)
    c_fails = _sanitize_int(consecutive_fails, default=0, min_val=0)

    if p_lvl == 0 or c_fails <= 1:
        return min(2, b_lvl)

    # L_next = min(4, max(L_prev, min(L_base, L_prev + 1)))
    return min(4, max(p_lvl, min(b_lvl, p_lvl + 1)))


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


def select_guidance_focus(
    error_type: str,
    misconception: str = "",
    is_stub: bool = False,
    prev_focus: str = "",
    level_repeated: bool = False
) -> str:
    """
    Select guidance focus based on diagnostic evidence, test outcomes, and previous hint history.
    Rotates focus if the learner repeatedly receives the same focus or level to change instructional strategy.
    """
    err = str(error_type or "").lower().strip()

    if is_stub or err in ("syntax", "syntaxerror", "indentationerror", "security"):
        initial_focus = "Structural"
    elif err in ("assertion", "assertionerror", "valueerror", "indexerror"):
        initial_focus = "Tracing"
    elif err in ("timeout", "recursionerror", "zerodivisionerror", "overflowerror", "logic"):
        initial_focus = "Algorithmic"
    elif err in ("typeerror", "attributeerror", "nameerror", "keyerror", "runtime"):
        initial_focus = "Conceptual"
    else:
        initial_focus = "Algorithmic"

    # Strategy Pivot: If level repeated or candidate focus matches immediately preceding hint, pivot focus
    if prev_focus and (initial_focus == prev_focus or level_repeated):
        pivoted = FOCUS_ROTATION.get(prev_focus, FOCUS_ROTATION.get(initial_focus, "Tracing"))
        if pivoted and pivoted != prev_focus:
            return pivoted
        elif pivoted == prev_focus:
            # Further rotate if collision
            return FOCUS_ROTATION.get(pivoted, "Conceptual")

    return initial_focus


def evaluate_dsda_v2(
    diagnostic: Dict[str, Any],
    learner_state: Dict[str, Any],
    problem_hints: List[Dict[str, Any]],
    current_attempt_count: int = 1,
    consecutive_fails: int = 0,
    response_time: float = 0.0,
    baseline_time: Optional[float] = 60.0,
    observations_count: int = 1,
    code: str = "",
    passed: bool = False
) -> Dict[str, Any]:
    """
    Executes the DSDA v2.1 Decision Engine across all pedagogical gates:
    Gate 1: Success Gate (Level 0, clear scaffolding)
    Gate 2: Security Violation (Level 1, Structural)
    Gate 3: Stub/Empty Submission (Level 1, Structural, AST verified)
    Gate 4: Syntax Error (Level min(F_prob, 2), Structural)
    Gate 5: Persistent Failure / ZPD Saturation (Level 4, Algorithmic, Remediation Flag)
    Gate 6: Expert Blindspot (Level 2, Tracing)
    Gate 7: General CSI Scoring & Monotonic Escalation (L_next = min(4, max(L_prev, min(L_base, L_prev + 1))))
    Gate 8: Orthogonal Focus Dimension & Strategy Pivot
    """
    # Gate 1: Solution Passed
    if passed:
        return {
            "level": 0,
            "focus": "None",
            "reason": "Solution passed all assertions.",
            "rationale": "Solution passed all test assertions.",
            "csi": 0.0,
            "raw_csi": 0.0,
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "Success",
            "counters": {
                "F_prob": 0,
                "H_prob": 0,
                "N_obs": _sanitize_int(observations_count, default=1, min_val=0)
            }
        }

    diag_dict = diagnostic if isinstance(diagnostic, dict) else {}
    l_state = learner_state if isinstance(learner_state, dict) else {}
    hints_list = problem_hints if isinstance(problem_hints, list) else []

    error_type = str(diag_dict.get("error_type", "assertion")).lower().strip()
    misconception = str(diag_dict.get("misconception", "")).strip()
    c_fails = _sanitize_int(consecutive_fails, default=0, min_val=0)
    h_used = len(hints_list)
    n_obs = _sanitize_int(observations_count, default=1, min_val=0)

    # Gate 2: Security Violation (Explicit exception: Level 1, no BKT penalty)
    if error_type == "security":
        return {
            "level": 1,
            "focus": "Structural",
            "reason": "Execution restricted: disallowed import or dangerous function call.",
            "rationale": "Execution restricted: disallowed import or dangerous function call.",
            "csi": 0.20,
            "raw_csi": 0.20,
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "Security",
            "counters": {"F_prob": c_fails, "H_prob": h_used, "N_obs": n_obs}
        }

    # Gate 3: Stub / Empty Submission (AST inspection evidence)
    if is_code_stub(code):
        return {
            "level": 1,
            "focus": "Structural",
            "reason": "Incomplete code submission. Starter code stub or empty function detected.",
            "rationale": "Incomplete code submission. Provide a complete function definition.",
            "csi": 0.22,
            "raw_csi": 0.22,
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "StubCode",
            "counters": {"F_prob": c_fails, "H_prob": h_used, "N_obs": n_obs}
        }

    # Gate 4: Syntax Error
    if error_type in ("syntax", "syntaxerror", "indentationerror"):
        syntax_level = min(max(1, c_fails), 2)
        return {
            "level": syntax_level,
            "focus": "Structural",
            "reason": f"Syntax or indentation error detected (Level {syntax_level} guidance).",
            "rationale": f"Syntax or indentation error detected (Level {syntax_level} guidance).",
            "csi": round(0.20 * syntax_level, 2),
            "raw_csi": round(0.20 * syntax_level, 2),
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "SyntaxError",
            "counters": {"F_prob": c_fails, "H_prob": h_used, "N_obs": n_obs}
        }

    # Extract previous problem hint history
    prev_level = 0
    prev_focus = ""
    if hints_list:
        prev_level = _sanitize_int(hints_list[-1].get("level", 0), default=0, min_val=0, max_val=4)
        prev_focus = str(hints_list[-1].get("focus", "")).strip()

    mastery = _sanitize_float(l_state.get("mastery", 0.35), default=0.35, min_val=0.0, max_val=1.0)
    confidence = _sanitize_float(l_state.get("confidence", 0.50), default=0.50, min_val=0.0, max_val=1.0)
    cognitive_load = _sanitize_float(l_state.get("cognitive_load", 0.20), default=0.20, min_val=0.0, max_val=1.0)
    confusion = _sanitize_float(l_state.get("confusion", 0.0), default=0.0, min_val=0.0, max_val=1.0)

    # Gate 5: Persistent Failure / ZPD Saturation
    if prev_level == 4 and c_fails >= 4:
        return {
            "level": 4,
            "focus": "Algorithmic",
            "reason": "Persistent struggle at maximum scaffolding depth (ZPD saturation).",
            "rationale": "Persistent struggle at maximum scaffolding depth. Recommend foundational review or educator intervention.",
            "csi": 0.95,
            "raw_csi": 0.95,
            "uncertainty": 0.0,
            "remediation_flag": True,
            "gate_triggered": "ZpdSaturation",
            "counters": {"F_prob": c_fails, "H_prob": h_used, "N_obs": n_obs}
        }

    # Gate 6: Expert Blindspot
    if mastery >= 0.75 and c_fails == 1:
        return {
            "level": 2,
            "focus": "Tracing",
            "reason": "High-mastery learner on initial error. Bypassed elementary question to focus on state tracing.",
            "rationale": "High-mastery learner on initial error. Bypassed elementary question to focus directly on state tracing.",
            "csi": 0.40,
            "raw_csi": 0.40,
            "uncertainty": 0.0,
            "remediation_flag": False,
            "gate_triggered": "ExpertBlindspot",
            "counters": {"F_prob": c_fails, "H_prob": h_used, "N_obs": n_obs}
        }

    # Gate 7: Continuous CSI Calculation & Monotonic Escalation
    csi, raw_csi, u = calculate_csi_score(
        mastery=mastery,
        consecutive_fails=c_fails,
        confidence=confidence,
        cognitive_load=cognitive_load,
        hints_used=h_used,
        response_time=response_time,
        baseline_time=baseline_time,
        observations_count=n_obs
    )
    base_level = determine_base_level(csi)

    # Enforce exact escalation invariant
    final_level = calculate_escalated_level(
        prev_level=prev_level,
        base_level=base_level,
        consecutive_fails=c_fails
    )

    # Gate 8: Orthogonal Focus Dimension & Strategy Pivot
    level_repeated = (final_level == prev_level and prev_level > 0)
    focus = select_guidance_focus(
        error_type=error_type,
        misconception=misconception,
        is_stub=False,
        prev_focus=prev_focus,
        level_repeated=level_repeated
    )

    remediation_flag = (final_level == 4 and c_fails >= 3) or (confusion >= 0.60 and c_fails >= 3)
    reason = f"CSI struggle score {csi:.2f} (raw: {raw_csi:.2f}, uncertainty: {u:.2f}) mapped to Level {final_level} with {focus} focus."

    return {
        "level": final_level,
        "focus": focus,
        "reason": reason,
        "rationale": reason,
        "csi": csi,
        "raw_csi": raw_csi,
        "uncertainty": u,
        "remediation_flag": remediation_flag,
        "gate_triggered": "ContinuousCSI",
        "counters": {
            "F_prob": c_fails,
            "H_prob": h_used,
            "N_obs": n_obs
        }
    }
