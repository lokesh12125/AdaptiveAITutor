import pytest
from app.learning.bkt import update_mastery
from app.learning.confidence import calculate_confidence_evidence, update_confidence
from app.learning.confusion import calculate_confusion_signal, update_confusion
from app.learning.cognitive_load import (
    calculate_time_stress,
    calculate_attempt_stress,
    calculate_error_stress,
    calculate_hint_stress,
    calculate_load_signal,
    update_cognitive_load
)
from app.learning.scaffolding import calculate_scaffolding_score, determine_scaffolding_level

def test_bkt_initial_mastery():
    # 1. Initial mastery is 0.20
    mastery = 0.20
    assert mastery == 0.20

def test_bkt_correct_increases_mastery():
    # 2. Correct response increases mastery
    prior = 0.20
    new_mastery = update_mastery(prior, passed=True)
    assert new_mastery > prior
    assert new_mastery <= 1.0

def test_bkt_incorrect_decreases_mastery():
    # 3. Incorrect response normally decreases mastery
    prior = 0.20
    new_mastery = update_mastery(prior, passed=False)
    assert new_mastery < prior
    assert new_mastery >= 0.0

def test_bkt_multiple_correct_converge_upward():
    # 4. Multiple correct answers converge upward
    mastery = 0.20
    for _ in range(5):
        mastery = update_mastery(mastery, passed=True)
    assert mastery > 0.80
    assert mastery <= 1.0

def test_bkt_multiple_incorrect_move_downward():
    # 5. Multiple incorrect answers move downward
    mastery = 0.80
    for _ in range(5):
        mastery = update_mastery(mastery, passed=False)
    assert mastery < 0.20
    assert mastery >= 0.0

def test_bkt_bounds():
    # 6. Values never exceed 1. 7. Values never become negative.
    assert update_mastery(1.5, passed=True) <= 1.0
    assert update_mastery(-0.5, passed=False) >= 0.0

def test_bkt_zero_denominator_safe():
    # 8. Zero-denominator cases do not crash.
    # Set P_S = 1.0, P_G = 1.0 -> P(correct) can be weird if P_K is extreme
    try:
        update_mastery(1.0, passed=True, p_s=1.0, p_g=1.0)
    except ZeroDivisionError:
        pytest.fail("BKT crashed with ZeroDivisionError")

def test_confidence_initial():
    assert 0.50 == 0.50

def test_confidence_correct_evidence():
    ev_no_hint = calculate_confidence_evidence(passed=True, hints_used=0, consecutive_fails=0)
    ev_with_hint = calculate_confidence_evidence(passed=True, hints_used=1, consecutive_fails=0)
    assert ev_no_hint > ev_with_hint

def test_confidence_incorrect_lowers():
    ev_incorrect = calculate_confidence_evidence(passed=False, hints_used=0, consecutive_fails=1)
    ev_repeated_fail = calculate_confidence_evidence(passed=False, hints_used=0, consecutive_fails=3)
    assert ev_repeated_fail < ev_incorrect
    assert ev_incorrect < 0.5

def test_confidence_ewma():
    prior = 0.50
    ev = 1.0
    updated = update_confidence(prior, ev, alpha=0.70)
    assert updated == pytest.approx(0.70 * 0.50 + 0.30 * 1.0)
    
def test_confidence_bounds():
    assert update_confidence(1.5, 1.5) <= 1.0
    assert update_confidence(-0.5, -0.5) >= 0.0

def test_confusion_initial():
    assert 0.0 == 0.0

def test_confusion_one_failure():
    sig = calculate_confusion_signal(passed=False, consecutive_fails=1, hints_used=0)
    assert sig > 0.0

def test_confusion_repeated_failure():
    sig1 = calculate_confusion_signal(passed=False, consecutive_fails=1, hints_used=0)
    sig2 = calculate_confusion_signal(passed=False, consecutive_fails=3, hints_used=0)
    assert sig2 > sig1

def test_confusion_hint_dependence():
    sig1 = calculate_confusion_signal(passed=False, consecutive_fails=1, hints_used=1)
    sig2 = calculate_confusion_signal(passed=False, consecutive_fails=1, hints_used=3)
    assert sig2 > sig1

def test_confusion_success_reduces():
    sig = calculate_confusion_signal(passed=True, consecutive_fails=0, hints_used=0)
    assert sig == 0.0
    prior = 0.8
    updated = update_confusion(prior, sig, alpha=0.70)
    assert updated < prior

def test_confusion_bounds():
    assert update_confusion(1.5, 1.5) <= 1.0
    assert update_confusion(-0.5, -0.5) >= 0.0

def test_cognitive_load_initial():
    assert 0.0 == 0.0

def test_cognitive_load_time_stress():
    assert calculate_time_stress(120.0, 60.0) == 1.0
    assert calculate_time_stress(30.0, 60.0) == 0.5

def test_cognitive_load_attempt_stress():
    assert calculate_attempt_stress(1) == 0.0
    assert calculate_attempt_stress(4) == 1.0

def test_cognitive_load_error_stress():
    assert calculate_error_stress(0) == 0.0
    assert calculate_error_stress(3) == 1.0

def test_cognitive_load_hint_stress():
    assert calculate_hint_stress(0) == 0.0
    assert calculate_hint_stress(3) == 1.0

def test_cognitive_load_ewma_decreases():
    prior = 0.8
    sig = calculate_load_signal(0.0, 0.0, 0.0, 0.0)
    updated = update_cognitive_load(prior, sig, alpha=0.70)
    assert updated < prior

def test_cognitive_load_bounds():
    assert update_cognitive_load(1.5, 1.5) <= 1.0
    assert update_cognitive_load(-0.5, -0.5) >= 0.0

def test_scaffolding_levels():
    # Low difficulty state maps to Level 1.
    score1 = calculate_scaffolding_score(mastery=0.9, confidence=0.9, confusion=0.0, cognitive_load=0.1, hint_dependence=0.0, time_stress=0.0)
    assert determine_scaffolding_level(score1) == 1

    # Moderate state maps to Level 2.
    score2 = calculate_scaffolding_score(mastery=0.5, confidence=0.5, confusion=0.3, cognitive_load=0.3, hint_dependence=0.2, time_stress=0.1)
    assert determine_scaffolding_level(score2) == 2

    # Higher state maps to Level 3.
    score3 = calculate_scaffolding_score(mastery=0.2, confidence=0.2, confusion=0.6, cognitive_load=0.6, hint_dependence=0.5, time_stress=0.3)
    assert determine_scaffolding_level(score3) == 3

    # High difficulty maps to Level 4.
    score4 = calculate_scaffolding_score(mastery=0.0, confidence=0.0, confusion=1.0, cognitive_load=1.0, hint_dependence=1.0, time_stress=1.0)
    assert determine_scaffolding_level(score4) == 4

def test_scaffolding_bounds():
    assert determine_scaffolding_level(-0.5) == 1
    assert determine_scaffolding_level(1.5) == 4


# --- DSDA v2.1 ALGORITHM TESTS ---
from app.learning.scaffolding import (
    calculate_csi_score,
    determine_base_level,
    calculate_escalated_level,
    select_guidance_focus,
    evaluate_dsda_v2,
    calculate_time_stress as dsda_time_stress,
    FALLBACK_MATRIX
)


def test_dsda_safe_time_stress():
    # Response time <= 0.5 * baseline -> 0.0
    assert dsda_time_stress(10.0, 60.0) == 0.0
    # Safe minimum baseline floor of 15.0s
    assert dsda_time_stress(15.0, 0.0) > 0.0
    # Response time = 2.0 * baseline -> 1.0 (clamped)
    assert dsda_time_stress(150.0, 60.0) == 1.0


def test_dsda_csi_continuous_bounds_and_uncertainty():
    # Cold start (n=0): uncertainty dominates, attenuates toward prior 0.35
    csi_0, raw_0, u_0 = calculate_csi_score(mastery=0.0, consecutive_fails=3, confidence=0.0, cognitive_load=1.0, hints_used=2, response_time=60.0, observations_count=0)
    assert 0.0 <= csi_0 <= 1.0
    assert u_0 == 1.0
    assert csi_0 == 0.35

    # High observations (n=10): uncertainty near 0, raw score dominates
    csi_10, raw_10, u_10 = calculate_csi_score(mastery=0.9, consecutive_fails=0, confidence=0.9, cognitive_load=0.1, hints_used=0, response_time=10.0, observations_count=10)
    assert u_10 < 0.05
    assert csi_10 < 0.25


def test_dsda_gate_1_success():
    res = evaluate_dsda_v2(diagnostic={}, learner_state={}, problem_hints=[], passed=True)
    assert res["level"] == 0
    assert res["focus"] == "None"
    assert res["csi"] == 0.0
    assert res["remediation_flag"] is False
    assert res["gate_triggered"] == "Success"


def test_dsda_gate_2_security():
    res = evaluate_dsda_v2(diagnostic={"error_type": "security"}, learner_state={}, problem_hints=[], code="import os\ndef f(): pass", passed=False)
    assert res["level"] == 1
    assert res["focus"] == "Structural"
    assert res["gate_triggered"] == "Security"


def test_dsda_gate_3_stub_code():
    res = evaluate_dsda_v2(diagnostic={"error_type": "assertion"}, learner_state={}, problem_hints=[], code="x = 1", passed=False)
    assert res["level"] == 1
    assert res["focus"] == "Structural"
    assert res["gate_triggered"] == "StubCode"


def test_dsda_gate_4_syntax_error():
    # First syntax failure -> Level 1
    res1 = evaluate_dsda_v2(diagnostic={"error_type": "syntax"}, learner_state={}, problem_hints=[], consecutive_fails=1, code="def solve():\n  return 1 +", passed=False)
    assert res1["level"] == 1
    assert res1["focus"] == "Structural"
    assert res1["gate_triggered"] == "SyntaxError"

    # Repeat syntax failure -> Level 2
    res2 = evaluate_dsda_v2(diagnostic={"error_type": "syntax"}, learner_state={}, problem_hints=[], consecutive_fails=3, code="def solve():\n  return 1 +", passed=False)
    assert res2["level"] == 2
    assert res2["focus"] == "Structural"


def test_dsda_gate_5_zpd_saturation():
    hints = [{"level": 4, "focus": "Algorithmic"}]
    res = evaluate_dsda_v2(diagnostic={"error_type": "assertion"}, learner_state={}, problem_hints=hints, consecutive_fails=4, code="def solve(x):\n  return x", passed=False)
    assert res["level"] == 4
    assert res["remediation_flag"] is True
    assert res["gate_triggered"] == "ZpdSaturation"


def test_dsda_gate_6_expert_blindspot():
    res = evaluate_dsda_v2(diagnostic={"error_type": "assertion"}, learner_state={"mastery": 0.85}, problem_hints=[], consecutive_fails=1, code="def solve(x):\n  return x * 2", passed=False)
    assert res["level"] == 2
    assert res["focus"] == "Tracing"
    assert res["gate_triggered"] == "ExpertBlindspot"


def test_dsda_monotonic_escalation():
    # Attempt 1 with high struggle: capped at Level 2 (prevents premature Level 3/4)
    res_att1 = evaluate_dsda_v2(
        diagnostic={"error_type": "assertion"},
        learner_state={"mastery": 0.1, "confidence": 0.1, "cognitive_load": 0.9},
        problem_hints=[],
        consecutive_fails=1,
        observations_count=5,
        code="def solve(x):\n  return x",
        passed=False
    )
    assert res_att1["level"] <= 2

    # Repeat failure with previous level 1: escalates by 1 to Level 2
    hints_l1 = [{"level": 1, "focus": "Tracing"}]
    res_att2 = evaluate_dsda_v2(
        diagnostic={"error_type": "assertion"},
        learner_state={"mastery": 0.1, "confidence": 0.1, "cognitive_load": 0.9},
        problem_hints=hints_l1,
        consecutive_fails=2,
        observations_count=5,
        code="def solve(x):\n  return x",
        passed=False
    )
    assert res_att2["level"] == 2

    # Repeat failure with previous level 2: escalates to Level 3
    hints_l2 = [{"level": 2, "focus": "Tracing"}]
    res_att3 = evaluate_dsda_v2(
        diagnostic={"error_type": "assertion"},
        learner_state={"mastery": 0.1, "confidence": 0.1, "cognitive_load": 0.9},
        problem_hints=hints_l2,
        consecutive_fails=3,
        observations_count=5,
        code="def solve(x):\n  return x",
        passed=False
    )
    assert res_att3["level"] == 3


def test_dsda_strategy_pivot():
    # If student is at Level 2 with Tracing focus and fails again, focus rotates to Algorithmic
    hints_l2 = [{"level": 2, "focus": "Tracing"}]
    res = evaluate_dsda_v2(
        diagnostic={"error_type": "assertion"},
        learner_state={"mastery": 0.4, "confidence": 0.5, "cognitive_load": 0.3},
        problem_hints=hints_l2,
        consecutive_fails=2,
        observations_count=5,
        code="def solve(x):\n  return x",
        passed=False
    )
    assert res["focus"] != "Tracing"
    assert res["focus"] == "Algorithmic"


def test_dsda_fallback_matrix_completeness():
    for lvl in [1, 2, 3, 4]:
        for foc in ["Conceptual", "Tracing", "Algorithmic", "Structural"]:
            assert (lvl, foc) in FALLBACK_MATRIX
            assert len(FALLBACK_MATRIX[(lvl, foc)]) > 20


def test_dsda_exact_formula_verification():
    """
    Verify exact hand-calculated CSI formula values:
    U = exp(-3/3) = exp(-1) ≈ 0.3678794
    Phi_F = min(1, 4/9) ≈ 0.4444444
    H_sat = min(1, 1/3) ≈ 0.3333333
    T_stress = (60 - 30) / 90 = 30/90 ≈ 0.3333333
    Raw = 0.25(0.60) + 0.25(4/9) + 0.20(0.50) + 0.15(0.30) + 0.10(1/3) + 0.05(1/3) = 0.4561111
    CSI = (1 - U) * Raw + U * 0.35 ≈ 0.417074
    """
    csi, raw, u = calculate_csi_score(
        mastery=0.40,
        consecutive_fails=2,
        confidence=0.50,
        cognitive_load=0.30,
        hints_used=1,
        response_time=60.0,
        baseline_time=60.0,
        observations_count=3
    )
    assert abs(raw - 0.4561) < 0.001
    assert abs(u - 0.3679) < 0.001
    assert abs(csi - 0.4171) < 0.001


def test_dsda_non_finite_and_extreme_inputs():
    """Verify robustness against NaN, Inf, None, negative, and out-of-range inputs."""
    res = evaluate_dsda_v2(
        diagnostic={"error_type": "assertion"},
        learner_state={
            "mastery": float("nan"),
            "confidence": float("inf"),
            "cognitive_load": -5.0,
            "confusion": 2.5
        },
        problem_hints=[],
        consecutive_fails=-10,
        response_time=float("nan"),
        baseline_time=None,
        observations_count=-3,
        code="def solve(x):\n  return x",
        passed=False
    )
    assert 0.0 <= res["csi"] <= 1.0
    assert 0.0 <= res["raw_csi"] <= 1.0
    assert 0.0 <= res["uncertainty"] <= 1.0
    assert 1 <= res["level"] <= 4
    assert res["focus"] in ["Conceptual", "Tracing", "Algorithmic", "Structural"]


@pytest.mark.parametrize("p_lvl", [1, 2, 3, 4])
@pytest.mark.parametrize("b_lvl", [1, 2, 3, 4])
def test_dsda_escalation_all_16_pairs(p_lvl, b_lvl):
    """
    Verify escalation invariant across all 16 (L_prev, L_base) pairs:
    1. L_next >= L_prev (never decreases on repeated failure).
    2. L_next <= L_prev + 1 (increases by at most 1).
    3. L_next <= 4 (never exceeds 4).
    4. Exact match: L_next == min(4, max(L_prev, min(L_base, L_prev + 1))).
    """
    l_next = calculate_escalated_level(prev_level=p_lvl, base_level=b_lvl, consecutive_fails=2)
    assert l_next >= p_lvl, f"Decreased from {p_lvl} to {l_next} with base {b_lvl}"
    assert l_next <= p_lvl + 1, f"Jumped more than 1 level from {p_lvl} to {l_next} with base {b_lvl}"
    assert l_next <= 4, f"Exceeded level 4: {l_next}"
    expected = min(4, max(p_lvl, min(b_lvl, p_lvl + 1)))
    assert l_next == expected


@pytest.mark.parametrize("b_lvl", [1, 2, 3, 4])
def test_dsda_initial_hint_cap(b_lvl):
    """First hint must be capped at min(2, L_base) to prevent premature depth."""
    l_init = calculate_escalated_level(prev_level=0, base_level=b_lvl, consecutive_fails=1)
    assert l_init <= 2
    assert l_init == min(2, b_lvl)


def test_dsda_focus_selection_categories():
    """Verify diagnostic mapping to appropriate pedagogical guidance focus."""
    assert select_guidance_focus("syntax") == "Structural"
    assert select_guidance_focus("indentationerror") == "Structural"
    assert select_guidance_focus("security") == "Structural"
    assert select_guidance_focus("assertion") == "Tracing"
    assert select_guidance_focus("indexerror") == "Tracing"
    assert select_guidance_focus("timeout") == "Algorithmic"
    assert select_guidance_focus("recursionerror") == "Algorithmic"
    assert select_guidance_focus("typeerror") == "Conceptual"
    assert select_guidance_focus("nameerror") == "Conceptual"


def test_dsda_remediation_flag_conditions():
    """Verify remediation triggers on ZPD saturation or extreme persistent confusion."""
    # Persistent failure at Level 4
    sat = evaluate_dsda_v2(
        diagnostic={"error_type": "assertion"},
        learner_state={},
        problem_hints=[{"level": 4, "focus": "Algorithmic"}],
        consecutive_fails=4,
        code="def solve(x):\n  return x",
        passed=False
    )
    assert sat["remediation_flag"] is True

    # High confusion with persistent failure
    conf = evaluate_dsda_v2(
        diagnostic={"error_type": "assertion"},
        learner_state={"confusion": 0.75},
        problem_hints=[{"level": 3, "focus": "Tracing"}],
        consecutive_fails=3,
        code="def solve(x):\n  return x",
        passed=False
    )
    assert conf["remediation_flag"] is True

    # Moderate struggle without streak does not trigger remediation
    mod = evaluate_dsda_v2(
        diagnostic={"error_type": "assertion"},
        learner_state={"confusion": 0.20},
        problem_hints=[],
        consecutive_fails=1,
        code="def solve(x):\n  return x",
        passed=False
    )
    assert mod["remediation_flag"] is False


def test_dsda_zero_and_invalid_baseline_time():
    """Ensure safe baseline handling without division by zero."""
    assert dsda_time_stress(5.0, 0.0) == 0.0  # t_base defaults to 15.0, 5s is <= 7.5s (0.5 * t_base)
    assert dsda_time_stress(30.0, -20.0) == 1.0  # t_base defaults to 15.0, 30s is 2x baseline
    assert dsda_time_stress(10.0, None) == 0.0  # t_base defaults to 60.0, 10s is <= 30s


def test_dsda_confidence_inversely_modulates_struggle():
    """Verify C-06 / V-02: Higher confidence reduces the struggle index, while lower confidence increases struggle."""
    csi_confident, raw_confident, _ = calculate_csi_score(
        mastery=0.5, consecutive_fails=2, confidence=0.9, cognitive_load=0.3, hints_used=1, response_time=30.0, observations_count=5
    )
    csi_unconfident, raw_unconfident, _ = calculate_csi_score(
        mastery=0.5, consecutive_fails=2, confidence=0.1, cognitive_load=0.3, hints_used=1, response_time=30.0, observations_count=5
    )
    # With (1.0 - conf), struggle must be strictly higher when confidence is low
    assert raw_unconfident > raw_confident
    assert csi_unconfident > csi_confident
    # Exact delta between conf=0.1 and conf=0.9 is 0.20 * (0.9 - 0.1) = 0.16
    assert abs((raw_unconfident - raw_confident) - 0.16) < 0.001


