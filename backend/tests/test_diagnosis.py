"""The tutor must find the real cause of an error in the learner's own code, not repeat the message.

Reported case: `for i in count(n, n)` with no import. The tutor said "add print(n, i) before line 4", which could
never run, when the cause was a missing `from itertools import count`.
"""
from __future__ import annotations

import pytest

from app.tutoring.contracts import DiagnosticOutput, ErrorDiagnosis, HintEvidence
from app.tutoring.diagnostic import _probe
from app.tutoring.dsda import POLICY, DSDADecision, Presentation, SolutionConstraints, ladder_for
from app.tutoring.error_analysis import analyse_name_error, analyse_other_error, name_hint
from app.tutoring.hints import ValidationContext, hint_similarity, validate_hint

PROBLEM = "sum-to-n"
WRONG_COUNT = "def sum_to_n(n):\n    total = 0\n    for i in count(1, 1):\n        if i <= n:\n            total += i\n        else:\n            break\n    return total\n"
STANDALONE_COUNT = "def sum_to_n(n):\n    return count(n)\n"
MISSPELLED = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return totl\n"
MISSING_IMPORT = "def sum_to_n(n):\n    return math.floor(n * (n + 1) / 2)\n"
METHOD_WRONG = "def sum_to_n(n):\n    values = []\n    append(values, n)\n    return n\n"
BEFORE_ASSIGNMENT = "def sum_to_n(n):\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
CORRECT = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n"


def analyse(code: str, name: str, line: int, problem: dict | None = None, kind: str = "NameError") -> ErrorDiagnosis:
    message = f"name '{name}' is not defined" if kind == "NameError" else f"cannot access local variable '{name}' where it is not associated with a value"
    result = analyse_name_error(code, {"type": kind, "message": message, "line": line}, problem or {"description": "", "function_name": "f"})
    assert result is not None
    return result


@pytest.mark.parametrize(("code", "name", "line", "cause", "detail"), [
    ("def f(nums):\n    return count(nums)\n", "count", 2, "method_as_function", "list or string"),
    ("def f(n, limit):\n    for i in count(n, n):\n        pass\n", "count", 2, "missing_import", "itertools"),
    ("def f(nums):\n    total = 0\n    return totel\n", "totel", 3, "misspelled", "total"),
    ("def f(nums):\n    return sum(num)\n", "num", 2, "parameter_typo", "nums"),
    ("def f(x):\n    return math.sqrt(x)\n", "math", 2, "missing_import", "math"),
    ("def f(x):\n    return sqrt(x)\n", "sqrt", 2, "missing_import", "math"),
    ("import itertools\ndef f():\n    return chain([1], [2])\n", "chain", 3, "missing_import", "itertools"),
    ("def f(words):\n    return length(words)\n", "length", 2, "builtin_misnamed", "len"),
    ("def f():\n    return Len([1])\n", "Len", 2, "builtin_misnamed", "len"),
    ("def f():\n    return true\n", "true", 2, "builtin_misnamed", "True"),
    ("def f(nums):\n    append(nums, 3)\n", "append", 2, "method_as_function", "list"),
    ("print(total)\ntotal = 1\n", "total", 1, "used_before_assignment", None),
    ("def g():\n    secret = 1\n\ndef f():\n    return secret\n", "secret", 5, "other_scope", "g"),
    ("def f(x):\n    return is_prime(x)\n", "is_prime", 2, "missing_function", None),
    ("def f(x):\n    return y + x\n", "y", 2, "undefined_variable", None),
])
def test_each_kind_of_missing_name_is_told_apart(code, name, line, cause, detail):
    result = analyse(code, name, line)
    assert result.cause == cause and result.error_class == "name_resolution" and result.name == name
    assert result.location == line and result.likely_cause and result.concept and result.evidence and result.explanation
    if detail:
        assert detail in (result.suggestion, result.module, result.where, result.owner)


def test_a_call_is_never_taken_for_a_typo_of_a_plain_variable():
    """The reported code has `counter = 0`. `count(n, n)` is a call, so it cannot be a misspelling of that variable."""
    result = analyse("def f(n, limit):\n    counter = 0\n    for i in count(n, n):\n        counter += 1\n    return counter\n", "count", 3)
    assert result.cause == "missing_import" and result.module == "itertools"


def test_a_standalone_count_uses_the_task_to_work_out_the_goal():
    problem = {"description": "Write count_evens(nums). Count how many numbers are even.", "function_name": "count_evens"}
    result = analyse("def count_evens(nums):\n    return count(nums)\n", "count", 2, problem)
    assert result.goal == "Count how many numbers are even."
    joined = " ".join(result.evidence)
    assert "count_evens" in joined and "nums" in joined and "Count how many" in joined


def test_help_for_a_standalone_count_follows_the_brief():
    result = analyse("def f(nums):\n    return count(nums)\n", "count", 2)
    first = name_hint("conceptual_question", result, None)
    assert "cannot find a function named `count`" in first and "What are you trying to count" in first and "?" in first
    second = name_hint("targeted_hint", result, None)
    assert "standalone function" in second and "some_list.count(value)" in second and "loop and a counter" in second
    assert "some_list.count" not in first, "the first hint leaves the working out to the learner"


def test_used_before_assignment_points_at_the_real_lines():
    result = analyse("def f(n):\n    total += n\n    return total\n", "total", 2, kind="UnboundLocalError")
    assert result.cause == "used_before_assignment" and result.location == 2
    assert "`total` has no value yet when line 2 runs" in name_hint("targeted_hint", result, None)


@pytest.mark.parametrize(("code", "name", "line"), [
    ("def f(nums):\n    return count(nums)\n", "count", 2), ("def f(n, limit):\n    for i in count(n, n):\n        pass\n", "count", 2), ("def f(nums):\n    total = 0\n    return totel\n", "totel", 3),
    ("def f(nums):\n    return sum(num)\n", "num", 2), ("def f(x):\n    return math.sqrt(x)\n", "math", 2), ("def f(x):\n    return sqrt(x)\n", "sqrt", 2), ("import itertools\ndef f():\n    return chain([1], [2])\n", "chain", 3),
    ("def f(words):\n    return length(words)\n", "length", 2), ("def f(nums):\n    append(nums, 3)\n", "append", 2), ("print(total)\ntotal = 1\n", "total", 1),
    ("def g():\n    secret = 1\n\ndef f():\n    return secret\n", "secret", 5), ("def f(x):\n    return is_prime(x)\n", "is_prime", 2), ("def f(x):\n    return y + x\n", "y", 2),
])
def test_every_step_of_help_names_the_real_problem_and_is_different(code, name, line):
    result = analyse(code, name, line)
    texts = []
    for strategy in ("conceptual_question", "targeted_hint", "name_options", "step_outline", "analogous_example", "direct_pointer"):
        written = name_hint(strategy, result, "f(1)")
        assert written is not None, strategy
        text = "\n".join(written) if isinstance(written, tuple) else written
        assert name in text, (strategy, text)
        assert "the value" not in text.replace("the value it", "").split("{")[0] or "{" not in text, text
        assert "{" not in text.replace("{size}", ""), (strategy, text)
        texts.append(text)
    assert "?" in texts[0], "the first step asks"
    assert len(set(texts)) == len(texts)
    for a, b in zip(texts, texts[1:], strict=False):
        assert hint_similarity(a, b) < 0.8, (a, b)


@pytest.mark.parametrize(("kind", "message", "cause"), [
    ("TypeError", 'can only concatenate str (not "int") to str', "mix_text_number"),
    ("TypeError", "'int' object is not iterable", "not_iterable"),
    ("TypeError", "'int' object is not callable", "not_callable"),
    ("TypeError", "f() missing 1 required positional argument: 'x'", "wrong_arguments"),
    ("TypeError", "list indices must be integers or slices, not str", "bad_index_type"),
    ("TypeError", "'str' object does not support item assignment", "immutable"),
    ("TypeError", "unhashable type: 'list'", "unhashable"),
    ("AttributeError", "'list' object has no attribute 'length'", "wrong_method"),
    ("AttributeError", "'NoneType' object has no attribute 'append'", "none_attribute"),
    ("IndexError", "pop from empty list", "pop_empty"),
    ("ValueError", "invalid literal for int() with base 10: 'a'", "int_literal"),
])
def test_other_errors_are_classified_by_their_real_cause(kind, message, cause):
    result = analyse_other_error("x = 1\n", {"type": kind, "message": message, "line": 1}, True)
    assert result.cause == cause and result.likely_cause and result.concept and result.location == 1


def test_a_method_that_does_not_exist_gets_the_right_alternative():
    result = analyse_other_error("x = 1\n", {"type": "AttributeError", "message": "'list' object has no attribute 'length'", "line": 1}, True)
    assert result.details["alternative"] == "use `len(items)`"


def test_the_print_hint_only_names_values_that_exist_on_that_line():
    """`i` is created by the loop on line 2, so printing it before line 2 could never work."""
    line, names = _probe("def f(n, limit):\n    for i in range(n, limit):\n        pass\n    return n\n", 2)
    assert line == 2 and names == ["n", "limit"] and "i" not in names


def test_a_missing_name_never_gets_print_or_trace_help():
    ladder = [step.strategy for step in ladder_for("runtime", "runtime:NameError:missing_import", True, POLICY)]
    assert "print_debugging" not in ladder and "trace_failing_case" not in ladder
    assert ladder == ["conceptual_question", "targeted_hint", "name_options", "step_outline", "analogous_example", "direct_pointer"]


# ---------------------------------------------------------------- validation

def _context(known: ErrorDiagnosis | None, message: str | None = None, level: int = 2, prior: list[str] | None = None) -> ValidationContext:
    decision = DSDADecision(
        action="give_help", selected_level=level, level_name="Targeted hint", strategy="targeted_hint", focus_issue="runtime:NameError:missing_import", timing="show_now", theme="error_tracing",
        presentation=Presentation(format="hint", max_sentences=3, max_words=70), constraints=SolutionConstraints(), policy_version="test", reason_codes=[], reason_student="",
    )
    diagnostic = DiagnosticOutput(category="runtime", issue_key="runtime:NameError:missing_import", title="t", student_summary="s", confidence=0.9, diagnosis=known, evidence=HintEvidence(error_type="NameError", message=message, line=2))
    return ValidationContext(decision=decision, function_name="f", reference_solution=None, student_code="a\nb\nc\n", prior_hints=prior or [], diagnostic=diagnostic)


KNOWN = ErrorDiagnosis(error_class="name_resolution", cause="missing_import", likely_cause="x", concept="y", location=2, name="count", module="itertools")
MESSAGE = "name 'count' is not defined"


@pytest.mark.parametrize("text", [
    f"NameError: {MESSAGE}.",
    f"Python says: {MESSAGE}.",
])
def test_repeating_the_error_message_is_rejected(text):
    assert "repeats_error_message" in validate_hint(text, _context(KNOWN, MESSAGE))


def test_the_old_generic_syntax_message_is_rejected():
    assert "repeats_error_message" in validate_hint('Python stopped reading at line 3 and reported: "invalid syntax". Read that line slowly.', _context(None))


def test_a_hint_that_ignores_the_diagnosed_name_is_rejected():
    assert "ignores_diagnosis" in validate_hint("Check that your loop stops at the right `value` on line 2.", _context(KNOWN))


def test_a_hint_with_nothing_specific_is_rejected():
    assert "too_vague" in validate_hint("Something on that part of the code needs another look, so go through it again carefully.", _context(None))


def test_a_good_hint_passes_validation():
    assert validate_hint("`count` lives in the `itertools` module, so line 2 needs an import above it. Which line would do that?", _context(KNOWN)) == []


def test_invented_lines_are_still_rejected():
    assert "invented_line_number" in validate_hint("`count` on line 99 needs an import.", _context(KNOWN))


# ---------------------------------------------------------------- through the real pipeline and sandbox

def strategies_for(learner, code: str, count: int = 8) -> list[dict]:
    seen = []
    for _ in range(count):
        response = learner.hint(PROBLEM, code, request_size="more" if seen else None)["response"]
        if response["tutor"] is None:
            break
        seen.append(response["tutor"])
    return seen


def test_the_reported_case_gets_the_real_cause_and_rising_help(learner):
    hints = strategies_for(learner, WRONG_COUNT)
    assert [h["strategy"] for h in hints] == ["conceptual_question", "targeted_hint", "name_options", "step_outline", "analogous_example", "direct_pointer"]
    texts = [h["text"] for h in hints]
    assert all("`count" in t or "count" in t for t in texts), "every hint is about the actual name"
    assert not any("print(" in t for t in texts), "printing cannot help when the line never runs"
    assert "itertools" not in texts[0], "the first hint asks, rather than tells"
    assert "itertools.count" in texts[1]
    assert "from itertools import count" in texts[-1]
    levels = [h["level"] for h in hints]
    assert levels == sorted(levels), "help only rises while nothing changes"
    for index, text in enumerate(texts):
        for earlier in texts[:index]:
            assert hint_similarity(text, earlier) < 0.8, (text, earlier)


def test_the_diagnosis_is_returned_but_not_before_the_help_reaches_it(learner):
    diagnostics = learner.hint(PROBLEM, WRONG_COUNT)["response"]["diagnostics"]
    assert diagnostics["issue_key"] == "runtime:NameError:missing_import"
    known = diagnostics["diagnosis"]
    assert known["error_class"] == "name_resolution" and known["location"] == 3 and known["confidence"] >= 0.8
    assert "itertools" not in str(diagnostics), "the first response must not give away what the first hint asks"
    later = learner.hint(PROBLEM, WRONG_COUNT, request_size="more")["response"]["diagnostics"]["diagnosis"]
    assert later["concept"] and "itertools" in later["likely_cause"]


@pytest.mark.parametrize(("code", "issue", "first_phrase", "last_phrase"), [
    (STANDALONE_COUNT, "runtime:NameError:method_as_function", "What are you trying to count", "Replace `count(n)`"),
    (MISSPELLED, "runtime:NameError:misspelled", "`totl`", "change `totl` to `total`"),
    (MISSING_IMPORT, "runtime:NameError:missing_import", "has not been loaded", "`import math`"),
    (METHOD_WRONG, "runtime:NameError:method_as_function", "Python cannot find a function named `append`", "`values.append(...)`"),
    (BEFORE_ASSIGNMENT, "runtime:UnboundLocalError:used_before_assignment", "does it have a value yet", "starting value"),
])
def test_help_is_specific_and_gets_more_specific(learner, code, issue, first_phrase, last_phrase):
    hints = strategies_for(learner, code)
    assert len(hints) >= 5
    assert any(first_phrase in h["text"] for h in hints[:2]), [h["text"] for h in hints[:2]]
    assert last_phrase in hints[-1]["text"], hints[-1]["text"]
    assert learner.hint(PROBLEM, code)["response"]["diagnostics"]["issue_key"] == issue
    assert len({h["text"] for h in hints}) == len(hints), "no hint repeats"
    assert not any(CORRECT.strip() in h["text"] for h in hints), "the solution is never given"


def test_fixing_the_name_is_acknowledged_and_the_new_issue_starts_fresh(learner):
    learner.hint(PROBLEM, WRONG_COUNT)
    learner.hint(PROBLEM, WRONG_COUNT, request_size="more")
    off_by_one = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n"
    response = learner.hint(PROBLEM, off_by_one)["response"]
    assert response["diagnostics"]["issue_key"] == "logic:off_by_one"
    assert response["progress_note"], "progress is acknowledged"
    assert response["tutor"]["hint_number"] == 1, "a new issue starts again, small"
    assert "count" not in response["tutor"]["text"], "it is about the new issue"


def test_solving_it_records_that_the_issue_was_resolved(learner):
    from sqlalchemy import select

    from app.db import session_scope
    from app.models import InteractionRecord

    learner.hint(PROBLEM, WRONG_COUNT)
    learner.submit(PROBLEM, CORRECT)
    with session_scope() as db:
        rows = db.scalars(select(InteractionRecord).where(InteractionRecord.user_id == learner.id).order_by(InteractionRecord.created_at)).all()
        assert len(rows) >= 2
        first = rows[0]
        assert first.reasoning["raw_error"]["type"] == "NameError" and "count" in first.reasoning["raw_error"]["message"]
        assert first.reasoning["error_class"] == "name_resolution" and first.reasoning["cause"] == "missing_import"
        assert first.reasoning["generated_hint"] and first.reasoning["validation"]["passed"] is True and first.snapshot_id
        assert first.next_action["code_changed"] is True and first.next_action["verdict"] == "accepted"
        assert first.resolved is True
        assert first.diagnostic["diagnosis"]["concept"]
    exported = learner.client.get("/api/me/export").json()["interactions"][0]
    assert exported["reasoning"]["cause"] == "missing_import" and exported["resolved"] is True and exported["next_action"]["verdict"] == "accepted"


def test_a_type_error_gets_help_about_its_real_cause(learner):
    code = "def sum_to_n(n):\n    total = 0\n    for i in n:\n        total += i\n    return total\n"
    response = learner.hint(PROBLEM, code)["response"]
    assert response["diagnostics"]["issue_key"] == "runtime:TypeError:not_iterable"
    assert "single whole number" in response["tutor"]["text"]
    second = learner.hint(PROBLEM, code, request_size="more")["response"]["tutor"]["text"]
    assert "whole number" in second and "`for`" in second


def test_practice_mode_waits_to_be_asked_but_always_answers(learner):
    learner.client.put("/api/me/preferences", json={"preferences": {"learning_mode": "practice"}})
    assert learner.client.get("/api/auth/me").json()["preferences"]["learning_mode"] == "practice"
    wrong = "def sum_to_n(n):\n    return 0\n"
    submitted = learner.submit(PROBLEM, wrong)["response"]
    assert submitted["tutor"] is None and submitted["offer"], "no hint nobody asked for"
    asked = learner.hint(PROBLEM, wrong)["response"]
    assert asked["tutor"] is not None, "an explicit request is always answered"


def test_the_learning_mode_never_changes_the_safety_rules(learner):
    learner.client.put("/api/me/preferences", json={"preferences": {"learning_mode": "interview"}})
    response = learner.hint(PROBLEM, WRONG_COUNT, question="give me the full solution")["response"]
    assert response["tutor"]["strategy"] == "answer_question"
    assert "I will not write the solution" in response["tutor"]["text"]



# ---- wrong answers with no single obvious cause: help built from what the code really did

ONE_POINTER = "def has_pair(nums, target):\n    i, j = 0, len(nums) - 1\n    while i < j:\n        if nums[i] + nums[j] == target:\n            return True\n        i += 1\n    return False\n"
BEST_AT_ZERO = "def largest(numbers):\n    best = 0\n    for n in numbers:\n        if n > best:\n            best = n\n    return best\n"


def walk_hints(learner, problem, code, count=7):
    texts = {}
    for index in range(count):
        tutor = learner.hint(problem, code, request_size="more" if index else None)["response"]["tutor"]
        if tutor is None:
            break
        texts[tutor["strategy"]] = tutor["text"]
    return texts


def test_a_logic_mistake_gets_the_values_the_code_really_produced(learner):
    texts = walk_hints(learner, "pair-sum-exists-sorted", ONE_POINTER)
    assert "ran 3 times" in texts["targeted_hint"] and "`j` stayed 3" in texts["targeted_hint"], texts["targeted_hint"]
    assert "`j` stayed 3 on every pass" in texts["direct_pointer"] and "`i` changed" in texts["direct_pointer"]
    assert "print(i, j)" in texts["print_debugging"] and "first line inside the loop" in texts["print_debugging"]
    assert "has_pair([1, 2, 4, 7], 6)" in texts["conceptual_question"]


def test_a_variable_stuck_at_its_start_value_is_pointed_out(learner):
    texts = walk_hints(learner, "largest-in-list", BEST_AT_ZERO)
    assert "`best` stayed 0 on every pass" in texts["direct_pointer"], texts["direct_pointer"]
    assert "numbers" not in texts["direct_pointer"].split("stayed")[0], "a parameter staying the same is not the clue"
    assert "largest" not in texts.get("analogous_example", "").split("```")[1 if "```" in texts.get("analogous_example", "") else 0].lower(), "the worked example is a different task"


def test_a_print_hint_never_has_empty_brackets_or_bad_grammar(learner):
    texts = walk_hints(learner, "largest-in-list", BEST_AT_ZERO)
    text = texts["print_debugging"]
    assert "print(...)" not in text and "Do `" in text and "hold what you expected on each pass" in text


def test_a_type_error_gets_a_worked_example_about_that_error(learner):
    code = 'def format_greeting(name, age):\n    return "Hello " + name + ", you are " + age + " years old."\n'
    texts = walk_hints(learner, "format-greeting", code)
    assert "str(age)" in texts["analogous_example"] and "converting" in texts["analogous_example"]
