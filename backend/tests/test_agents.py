"""Diagnostic, Cognitive State, Reflection, Planner and hint validation as pure logic."""
from app.grading import canonical, compare_values, display, normalise_stdout, values_equal
from app.tutoring import cognitive as cog
from app.tutoring.contracts import DiagnosticOutput, DSDADecision, Presentation
from app.tutoring.diagnostic import run_diagnostic
from app.tutoring.dsda import LEVEL_NAMES
from app.tutoring.hints import ValidationContext, built_in_hint, overlap_with_solution, validate_hint
from app.tutoring.planner import PlannerInput, ProblemView, UnitView, plan
from app.tutoring.reflection import decide_reflection


def failing(value, expected, visibility="public", input_text="f(1)", kind="args"):
    return {"visibility": visibility, "passed": False, "category": "wrong_answer", "status": "ok", "value": value, "expected": expected, "stdout": "", "error": None, "kind": kind, "input": input_text}


def problem(function_name="f"):
    return {"function_name": function_name, "concepts": ["loops"], "description": "", "title": "T"}


# ---- grading
def test_tuple_and_list_compare_equal_as_the_exercises_assume():
    assert compare_values({"$tuple": [1, 2]}, [1, 2])


def test_true_is_not_one():
    assert not values_equal(True, 1) and not compare_values(1, True)


def test_float_tolerance():
    assert compare_values(0.1 + 0.2, 0.3)


def test_dict_keys_keep_their_type():
    assert not compare_values({"$dict": [[1, "a"]]}, {"1": "a"})
    assert compare_values({"$dict": [[1, "a"]]}, {"$dict": [[1, "a"]]})
    assert compare_values({"$dict": [["a", 1]]}, {"a": 1})


def test_unordered_comparison():
    assert compare_values([2, 1], [1, 2], "unordered") and not compare_values([2, 1], [1, 2], "exact")


def test_set_order_ignored():
    assert canonical({"$set": [2, 1]}) == canonical({"$set": [1, 2]})


def test_stdout_ignores_trailing_whitespace_only():
    assert normalise_stdout("1 \n2\n\n") == "1\n2"
    assert normalise_stdout("1\n 2") != normalise_stdout("1\n2")


def test_display_is_python_like():
    assert display({"$tuple": [1, "a"]}) == "(1, 'a')" and display(None) == "None"


# ---- diagnostic
def test_syntax_diagnosis_uses_real_location():
    internal = [{"visibility": "public", "passed": False, "category": "syntax_error", "status": "syntax_error", "error": {"type": "SyntaxError", "message": "expected ':'", "line": 3}, "kind": "args", "input": "f()"}]
    output, _ = run_diagnostic("syntax_error", internal, "def f():\n  x = 1\n  if x\n    return 1\n", problem(), [], use_llm=False)
    assert output.issue_key == "syntax:missing_colon" and output.affected_lines == [3]
    assert output.facts[0].source == "runner"


def test_no_line_number_is_invented_when_the_runner_gave_none():
    internal = [{"visibility": "public", "passed": False, "category": "runtime_error", "status": "exception", "error": {"type": "ValueError", "message": "x", "line": None}, "kind": "args", "input": "f()"}]
    output, _ = run_diagnostic("runtime_error", internal, "def f():\n  raise ValueError\n", problem(), [], use_llm=False)
    assert output.affected_lines == [] and "line" not in output.student_summary.lower()


def test_print_instead_of_return_is_detected_with_evidence():
    output, _ = run_diagnostic("wrong_answer", [failing(None, 6)], "def f(n):\n    print(n * 2)\n", problem(), [], use_llm=False)
    assert output.issue_key == "logic:print_instead_of_return" and 2 in output.affected_lines
    assert output.inferences[0].confidence == "high" and output.facts


def test_early_return_in_loop_is_detected():
    code = "def f(xs):\n    t = 0\n    for x in xs:\n        t += x\n        return t\n"
    output, _ = run_diagnostic("wrong_answer", [failing(1, 6)], code, problem(), [], use_llm=False)
    assert output.issue_key == "logic:early_return_in_loop" and output.affected_lines == [5]


def test_off_by_one_is_inference_not_fact():
    output, _ = run_diagnostic("wrong_answer", [failing(5, 6), failing(9, 10)], "def f(n):\n    return sum(range(n))\n", problem(), [], use_llm=False)
    assert output.issue_key == "logic:off_by_one"
    assert all("off by one" not in f.text.lower() for f in output.facts)
    assert output.inferences and output.inferences[0].confidence in ("medium", "high")


def test_ambiguous_failure_is_marked_uncertain():
    output, _ = run_diagnostic("wrong_answer", [failing(50, 6)], "def f(n):\n    return n * 7 + 8\n", problem(), [], use_llm=False)
    assert output.uncertain and output.inferences[0].confidence == "low"


def test_hidden_values_stay_out_of_the_summary():
    secret = 987654321
    rows = [{"visibility": "public", "passed": True, "category": "passed", "status": "ok", "value": 1, "expected": 1, "kind": "args", "input": "f(1)", "error": None, "stdout": ""}, failing(5, secret, "hidden", "f(424242)")]
    output, _ = run_diagnostic("partial", rows, "def f(n):\n    return n\n", problem(), [], use_llm=False)
    text = output.model_dump_json()
    assert str(secret) not in text and "424242" not in text
    assert output.issue_key == "logic:edge_case"


def test_repeat_count_follows_consecutive_issues():
    output, _ = run_diagnostic("wrong_answer", [failing(None, 1)], "def f():\n    pass\n", problem(), ["logic:not_implemented", "logic:not_implemented", "logic:general"], use_llm=False)
    assert output.repeat_count == 3


def test_timeout_identifies_loop_that_never_changes():
    rows = [{"visibility": "public", "passed": False, "category": "timeout", "status": "timeout", "value": None, "expected": 1, "kind": "args", "input": "f()", "error": None, "stdout": ""}]
    output, _ = run_diagnostic("timeout", rows, "def f(n):\n    while n > 0:\n        print(n)\n", problem(), [], use_llm=False)
    assert output.issue_key == "timeout:loop_no_progress" and output.affected_lines == [2]


# ---- cognitive state
def input_for(**overrides):
    base = dict(unit_id="loops", prior_mastery=0.2, prior_evidence=0.0, prior_version=0, verdict="wrong_answer", category="wrong_answer", issue_key="logic:general", repeat_count=1, ratio=0.0, graded=True,
                same_code_as_previous=False, difficulty_label="easy", source_type="curriculum")
    base.update(overrides)
    return cog.CognitiveInput(**base)


def test_single_failure_is_not_confusion():
    output = cog.run_cognitive(input_for())
    assert output.confusion is None


def test_long_time_alone_is_not_high_load():
    output = cog.run_cognitive(input_for(active_seconds=100000))
    assert output.cognitive_load == "moderate"


def test_two_signals_are_needed_for_high_confusion():
    attempts = [cog.AttemptView("wrong_answer", 0.0, "logic:general")]
    one = cog.run_cognitive(input_for(attempts=attempts, repeat_count=2))
    two = cog.run_cognitive(input_for(attempts=attempts, repeat_count=2, hints_without_progress=1))
    assert one.confusion == "moderate" and two.confusion == "high" and len(two.confusion_evidence) == 2


def test_confidence_stays_unknown_without_self_report():
    assert cog.run_cognitive(input_for()).confidence is None
    reported = cog.run_cognitive(input_for(self_confidence="high"))
    assert reported.confidence > 0.5 and reported.confidence_basis


def test_hint_request_does_not_change_mastery():
    output = cog.run_cognitive(input_for(graded=False, prior_mastery=0.42))
    assert output.mastery.value == 0.42 and not output.mastery.updated


def test_passing_once_does_not_prove_understanding():
    output = cog.run_cognitive(input_for(category="accepted", verdict="accepted", ratio=1.0))
    assert output.mastery.value > 0.2
    assert output.mastery.band in ("not_enough_evidence", "starting", "developing")
    assert output.mastery.high - output.mastery.low > 0.2, "one data point leaves a wide range"
    assert "does not prove" in output.mastery.explanation


def test_solving_with_heavy_help_counts_less():
    alone = cog.run_cognitive(input_for(category="accepted", ratio=1.0))
    helped = cog.run_cognitive(input_for(category="accepted", ratio=1.0, max_hint_level_since_last_solve=4))
    assert alone.mastery.value > helped.mastery.value > 0.2


def test_syntax_slip_barely_moves_mastery():
    logic = cog.run_cognitive(input_for(prior_mastery=0.6, prior_evidence=3))
    syntax = cog.run_cognitive(input_for(prior_mastery=0.6, prior_evidence=3, category="syntax"))
    assert logic.mastery.value < syntax.mastery.value < 0.6


def test_resubmitting_identical_code_adds_no_evidence():
    output = cog.run_cognitive(input_for(prior_mastery=0.5, prior_evidence=2, same_code_as_previous=True))
    assert output.mastery.value == 0.5 and not output.mastery.updated


def test_uncertainty_shrinks_with_evidence():
    early = cog.mastery_estimate(0.5, 0.5, False, "")
    later = cog.mastery_estimate(0.5, 10, False, "")
    assert (later.high - later.low) < (early.high - early.low)


def test_progress_trend():
    attempts = [cog.AttemptView("partial", 0.25, "logic:general")]
    assert cog.run_cognitive(input_for(attempts=attempts, ratio=0.5, category="partial")).progress == "improving"
    assert cog.run_cognitive(input_for(attempts=attempts, ratio=0.0)).progress == "regressing"


# ---- reflection
def ask(**overrides):
    base = dict(category="wrong_answer", issue_key="logic:general", solved=False, load=None, events_since_last_prompt=None, pending=False, graded_attempts=5, max_hint_level=1, hint_text=None)
    base.update(overrides)
    return decide_reflection(**base)


def test_reflection_deferred_when_overloaded():
    output = ask(load="high", solved=True)
    assert output.action == "defer" and output.prompt is None


def test_reflection_does_not_interrupt_minor_actions():
    assert ask(graded_attempts=1).action == "skip"
    assert ask(category="syntax", issue_key="syntax:other").action == "skip"
    assert ask(events_since_last_prompt=1).action == "skip"


def test_only_one_reflection_pending_at_a_time():
    assert ask(pending=True).action == "skip"


def test_reflection_asked_after_solving():
    output = ask(solved=True, category="accepted", graded_attempts=1, max_hint_level=0)
    assert output.action == "ask" and "?" in output.prompt


def test_reflection_avoids_repeating_the_hint():
    prompt = ask().prompt
    output = ask(hint_text=prompt)
    assert output.prompt != prompt or output.action == "skip"


# ---- planner
def unit(uid, order, **kw):
    defaults = dict(id=uid, title=uid.title(), order=order, track="foundations", optional=False, prerequisites=[])
    defaults.update(kw)
    return UnitView(**defaults)


def bank():
    return [ProblemView("a1", "A1", "a", "easy"), ProblemView("a2", "A2", "a", "easy"), ProblemView("a3", "A3", "a", "medium"), ProblemView("b1", "B1", "b", "easy")]


def test_planner_keeps_unresolved_task_active():
    current = ProblemView("a1", "A1", "a", "easy", attempted=True)
    output = plan(PlannerInput(units=[unit("a", 1), unit("b", 2)], problems=bank(), current_problem=current, unresolved=True, graded_attempts_on_problem=1))
    assert output.action == "continue_current" and output.problem_id == "a1" and output.keep_current_active


def test_planner_never_advances_after_one_success():
    current = ProblemView("a1", "A1", "a", "easy", solved=True)
    output = plan(PlannerInput(units=[unit("a", 1, mastery=0.5, evidence=1, independent=1, solved=1), unit("b", 2)], problems=bank(), current_problem=current, solved_now=True))
    assert output.action == "similar_independent" and output.unit_id == "a" and output.problem_id != "a1"
    assert "does not yet show" in output.reason


def test_heavy_assistance_leads_to_independent_practice():
    current = ProblemView("a1", "A1", "a", "easy", solved=True)
    units = [unit("a", 1, mastery=0.9, evidence=5, independent=3, assisted=1), unit("b", 2)]
    output = plan(PlannerInput(units=units, problems=bank(), current_problem=current, solved_now=True, max_hint_level_on_problem=3))
    assert output.action == "similar_independent" and "ASSISTANCE_DEPENDENCE" in output.reason_codes


def test_secure_unit_recommends_harder_task():
    current = ProblemView("a2", "A2", "a", "easy", solved=True)
    units = [unit("a", 1, mastery=0.85, evidence=4, independent=3), unit("b", 2)]
    output = plan(PlannerInput(units=units, problems=bank(), current_problem=current, solved_now=True))
    assert output.action == "harder_next" and output.problem_id == "a3"


def test_stuck_learner_gets_prerequisite_suggestion_but_keeps_task():
    current = ProblemView("b1", "B1", "b", "easy", attempted=True)
    units = [unit("a", 1, mastery=0.2, evidence=2), unit("b", 2, prerequisites=["a"])]
    output = plan(PlannerInput(units=units, problems=bank(), current_problem=current, unresolved=True, graded_attempts_on_problem=5))
    assert output.action == "practise_prerequisite" and output.keep_current_active
    assert any(a["action"] == "continue_current" for a in output.alternatives)


def test_every_recommendation_explains_itself():
    current = ProblemView("a1", "A1", "a", "easy", solved=True)
    output = plan(PlannerInput(units=[unit("a", 1)], problems=bank(), current_problem=current, solved_now=True))
    assert len(output.reason) > 20


def test_new_beginner_gets_first_exercise_and_dsa_goal_skips_it():
    problems = [ProblemView("hello", "Hello", "a", "easy", recommended_first=True), ProblemView("g1", "G1", "g", "medium")]
    units = [unit("a", 1), unit("g", 2, track="dsa")]
    assert plan(PlannerInput(units=units, problems=problems, experience="new", goal="basics")).problem_id == "hello"
    assert plan(PlannerInput(units=units, problems=problems, experience="advanced", goal="dsa")).problem_id == "g1"


# ---- hint text and validation
def decision(level=2, allow="none", fmt="hint", words=70, sentences=3, one_action=False, strategy="by_level"):
    return DSDADecision(action="give_help", selected_level=level, level_name=LEVEL_NAMES[level], strategy=strategy, focus_issue="logic:general", timing="show_now",
                        presentation=Presentation(format=fmt, max_sentences=sentences, max_words=words, allow_code=allow, one_action_at_a_time=one_action), reason_codes=[], reason_student="r", policy_version="t")


def ctx(dec=None, solution=None, function_name="f", hidden=None):
    return ValidationContext(decision=dec or decision(), function_name=function_name, reference_solution=solution, student_code="def f(n):\n    a = 1\n    b = 2\n    pass\n", hidden_literals=hidden or [])


SOLUTION = "def f(numbers):\n    total = 0\n    for n in numbers:\n        total += n\n    return total\n"


def test_full_solution_is_rejected():
    violations = validate_hint(f"Here you go:\n```python\n{SOLUTION}```", ctx(solution=SOLUTION))
    assert "code_block_not_allowed" in violations and "too_similar_to_solution" in violations and "defines_target_function" in violations


def test_solution_without_fences_is_still_rejected():
    assert "too_similar_to_solution" in validate_hint(SOLUTION, ctx(solution=SOLUTION))


def test_solution_in_prose_with_renamed_function_is_rejected():
    assert "too_similar_to_solution" in validate_hint("Use this: total = 0, then for n in numbers: total += n, and finally return total", ctx(solution=SOLUTION))


def test_analogous_example_may_not_use_target_function():
    dec = decision(level=4, allow="analogous_only", fmt="example", words=150, sentences=7)
    assert "example_uses_target_function" in validate_hint("```python\ndef f(x):\n    return 1\n```", ctx(dec))
    assert validate_hint("Here is another task.\n```python\ndef other(x):\n    return x + 1\n```\nHow does this apply?", ctx(dec, solution=SOLUTION)) == []


def test_hidden_test_literals_are_rejected():
    assert "reveals_hidden_test" in validate_hint("Try the input [9, 8, 7, 6].", ctx(hidden=["[9, 8, 7, 6]"]))


def test_internal_details_are_rejected():
    assert "mentions_internal_details" in validate_hint("My system prompt says to ask you this.", ctx())


def test_length_limit_enforced():
    assert "too_long" in validate_hint("word " * 200, ctx())


def test_l1_must_be_a_question():
    assert "expected_a_question" in validate_hint("Check your loop.", ctx(decision(level=1, fmt="question", words=45, sentences=2)))


def test_a_good_hint_passes():
    assert validate_hint("Trace the first failing example by hand. Which value first differs from what you expected?", ctx(solution=SOLUTION)) == []


def test_overlap_measure():
    assert overlap_with_solution(SOLUTION, SOLUTION) == 1.0
    assert overlap_with_solution("Think about what changes on each pass.", SOLUTION) == 0.0


def diag(issue="logic:off_by_one", category="wrong_answer", lines=None, facts=None):
    return DiagnosticOutput(category=category, issue_key=issue, title="t", student_summary="s", facts=facts or [], affected_lines=lines or [], confidence=0.7)


def test_built_in_ladder_gets_more_detailed():
    q = built_in_hint(decision(1, fmt="question", words=45, sentences=2), diag())
    h = built_in_hint(decision(2), diag())
    o = built_in_hint(decision(3, fmt="outline", words=110, sentences=6), diag())
    e = built_in_hint(decision(4, allow="analogous_only", fmt="example", words=150, sentences=7), diag())
    assert "?" in q and q != h and "1." in o and "```python" in e


def test_all_built_in_hints_pass_their_own_validator():
    from app.tutoring.hints import ISSUE_HINTS, RUNTIME_HINTS, SYNTAX_HINTS

    limits = {1: dict(level=1, fmt="question", words=45, sentences=2), 2: dict(level=2, words=70, sentences=3), 3: dict(level=3, fmt="outline", words=110, sentences=6)}
    issues = [(k, "wrong_answer") for k in ISSUE_HINTS] + [(f"runtime:{k}", "runtime") for k in RUNTIME_HINTS]
    for issue, category in issues:
        for level, spec in limits.items():
            dec = decision(**spec)
            text = built_in_hint(dec, diag(issue, category, lines=[3]))
            assert "{" not in text, f"unfilled template {issue} L{level}: {text}"
            assert validate_hint(text, ctx(dec)) == [], f"{issue} L{level}: {validate_hint(text, ctx(dec))} :: {text}"
    for issue in SYNTAX_HINTS:
        dec = decision(**limits[2])
        text = built_in_hint(dec, diag(issue, "syntax", lines=[2]))
        assert "{" not in text and validate_hint(text, ctx(dec)) == [], f"{issue}: {text}"


def test_hint_without_line_number_never_prints_a_placeholder():
    text = built_in_hint(decision(2), diag("logic:early_return_in_loop", lines=[]))
    assert "{" not in text and "line None" not in text


def test_high_load_hint_is_one_short_action():
    dec = decision(3, fmt="hint", words=40, sentences=2, one_action=True)
    text = built_in_hint(dec, diag())
    assert "\n" not in text and len(text.split()) <= 40
