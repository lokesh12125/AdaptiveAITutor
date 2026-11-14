"""Hints must be specific to the learner's own code, never generic advice. Found and fixed during the agent audit (docs/agent-audit.md)."""
import re

import pytest

from app.tutoring import dsda
from app.tutoring.contracts import DiagnosticOutput, FailingExample, HintEvidence
from app.tutoring.diagnostic import _loop_facts
from app.tutoring.dsda import POLICY, DSDAInput
from app.tutoring.hints import (
    ISSUE_HINTS,
    ValidationContext,
    _fill,
    built_in_hint,
    fit_to_presentation,
    validate_hint,
)

OFF_BY_ONE = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n"
EARLY_RETURN = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n        return total\n"


def decision(strategy: str, level: int, high_load: bool = False):
    base = dsda.decide(DSDAInput(trigger="hint_request", request_size=None, category="wrong_answer", issue_key="logic:general", repeat_count=1, mastery=0.3,
                                 mastery_evidence=2.0, confidence=None, confusion=None, load="high" if high_load else None, progress="unknown", attempts_on_problem=1))
    return base.model_copy(update={"strategy": strategy, "selected_level": level, "presentation": dsda._presentation(level, "high" if high_load else None, POLICY), "level_name": dsda.LEVEL_NAMES[level]})


def diagnosis(issue: str, affected: int = 3, loop: bool = True, got: str = "3") -> DiagnosticOutput:
    evidence = HintEvidence(failing_example=FailingExample(input="sum_to_n(3)", got=got, expected="6"))
    if loop:
        evidence.loop_line, evidence.loop_source, evidence.loop_variable, evidence.result_name = 3, "for i in range(1, n):", "i", "total"
    return DiagnosticOutput(category="wrong_answer", issue_key=issue, title="t", student_summary="s", affected_lines=[affected], confidence=0.8, evidence=evidence)


def context(chosen, code=OFF_BY_ONE, model=False, diag=None):
    return ValidationContext(decision=chosen, function_name="sum_to_n", reference_solution=None, student_code=code, diagnostic=diag, require_on_topic=model)


# ---- the validator

@pytest.mark.parametrize("text", ["Use a loop.", "Think carefully about your logic.", "Read the problem again.", "Try debugging your code.", "Check your logic and try again."])
def test_generic_advice_is_rejected(text):
    assert "vague_advice" in validate_hint(text, context(decision("targeted_hint", 2)))


def test_model_text_that_could_fit_any_program_is_rejected():
    generic = "Loops can be tricky. Consider how many times it repeats and whether that matches what you need."
    specific = "Your loop visits `i` from 1 up to n - 1. Should `total` include n itself?"
    chosen = decision("targeted_hint", 2)
    assert "names_nothing_concrete" in validate_hint(generic, context(chosen, model=True, diag=diagnosis("logic:off_by_one")))
    assert "names_nothing_concrete" not in validate_hint(specific, context(chosen, model=True, diag=diagnosis("logic:off_by_one")))


# ---- built-in wording points at the learner's own code

ANCHORED = [("logic:off_by_one", 3, "3"), ("logic:missing_return", 3, "None"), ("logic:early_return_in_loop", 5, "1")]


@pytest.mark.parametrize("issue,affected,got", ANCHORED, ids=[row[0] for row in ANCHORED])
@pytest.mark.parametrize("strategy,level", [("conceptual_question", 1), ("targeted_hint", 2), ("step_outline", 3)])
def test_logic_hints_quote_the_failing_example_and_the_learners_loop(issue, affected, got, strategy, level):
    chosen = decision(strategy, level)
    text = built_in_hint(chosen, diagnosis(issue, affected, got=got))
    assert "sum_to_n(3)" in text, text
    assert "line 3" in text or "line 5" in text or "`total`" in text, text
    assert not re.search(r"\{[a-z_]+\}|the failing example|your result|the expected answer|that line", text), f"placeholder or fallback wording: {text}"
    code = EARLY_RETURN if issue == "logic:early_return_in_loop" else OFF_BY_ONE
    assert validate_hint(text, context(chosen, code=code, diag=diagnosis(issue, affected, got=got))) == [], text
    assert fit_to_presentation(text, chosen) == text, "the wording fits the level's sentence limit, so nothing is cut"


def test_wording_falls_back_when_the_loop_was_not_found():
    chosen = decision("conceptual_question", 1)
    text = built_in_hint(chosen, diagnosis("logic:off_by_one", loop=False))
    assert text == _fill(ISSUE_HINTS["logic:off_by_one"][0], diagnosis("logic:off_by_one", loop=False))


def test_high_load_keeps_the_anchored_question_short():
    chosen = decision("conceptual_question", 1, high_load=True)
    text = built_in_hint(chosen, diagnosis("logic:off_by_one"))
    assert len(text.split()) <= chosen.presentation.max_words and text.endswith("?")


def test_trace_hint_fits_its_level_and_says_what_to_watch_for():
    chosen = decision("trace_failing_case", 2)
    text = built_in_hint(chosen, diagnosis("logic:early_return_in_loop", 5, got="1"))
    assert "`return`" in text and "loop" in text and text.endswith("?"), text
    assert fit_to_presentation(text, chosen) == text


def test_print_hint_for_an_early_return_asks_how_many_passes_run():
    chosen = decision("print_debugging", 2)
    diag = diagnosis("logic:early_return_in_loop", 5, got="1")
    diag.evidence.probe_names, diag.evidence.probe_line, diag.evidence.probe_inside_loop = ["i", "total"], 3, True
    text = built_in_hint(chosen, diag)
    assert "`print(i, total)`" in text and "`return`" in text and "passes" in text and text.endswith("?"), text
    assert fit_to_presentation(text, chosen) == text and not validate_hint(text, context(chosen, code=EARLY_RETURN, diag=diag))


def test_full_stops_inside_quoted_code_do_not_cut_a_hint():
    chosen = decision("conceptual_question", 1)
    text = "For `f('a. b')` you returned `'x. y'`, but `'a. b'` was expected. Compared character by character, what differs?"
    assert fit_to_presentation(text, chosen) == text


def test_diagnostic_finds_the_loop_and_what_it_builds():
    assert _loop_facts(OFF_BY_ONE) == (3, "i", "total")
    assert _loop_facts("def f(xs):\n    out = []\n    for x in xs:\n        out.append(x)\n    return out\n") == (3, "x", "out")
    assert _loop_facts("def f(n):\n    return n\n") == (None, None, None)


# ---- through the real pipeline

def test_first_hint_on_real_code_names_the_loop_the_example_and_the_concept(learner):
    run = learner.submit("sum-to-n", OFF_BY_ONE)
    tutor = run["response"]["tutor"]
    assert "`for i in range(1, n):`" in tutor["text"] and "line 3" in tutor["text"] and "sum_to_n(3)" in tutor["text"], tutor["text"]
    assert tutor["concept"] == "Loops and boundaries"


def test_diagnosed_cause_is_in_the_trace_even_when_held_back_from_the_learner(learner):
    run = learner.submit("sum-to-n", "def sum_to_n(n):\n    for i in range(1, n + 1):\n        total += i\n    return total\n")
    trace = learner.client.get(f"/api/runs/{run['id']}/trace").json()
    diagnostic = next(step for step in trace["steps"] if step["stage"] == "diagnostic")["output"]
    assert diagnostic["cause"] == "used_before_assignment" and diagnostic["cause_confidence"] >= 0.9
