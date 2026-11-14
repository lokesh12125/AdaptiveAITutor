"""Reflection replies like a tutor beside the learner, its answers reach the other agents, and the planner sequences
practice by technique and moves forward through topics. See docs/agent-audit.md."""
from sqlalchemy import select

from app.db import session_scope
from app.models import Reflection
from app.tutoring import planner as P
from app.tutoring.reflection import decide_reflection, respond_to_answer

PROBLEM = "sum-to-n"
OFF_BY_ONE = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n"
RIGHT = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n + 1):\n        total += i\n    return total\n"
CONTEXT = {"issue_key": "logic:off_by_one", "input": "sum_to_n(3)", "got": "3", "expected": "6", "loop_source": "for i in range(1, n):", "loop_variable": "i", "result_name": "total", "line": 3}


# ---- the question names the learner's own code

def test_reflection_question_names_the_learners_loop_and_example():
    out = decide_reflection("partial", "logic:off_by_one", solved=False, load=None, events_since_last_prompt=None, pending=False, graded_attempts=3,
                            max_hint_level=1, hint_text="Look at where the loop stops.", context=CONTEXT)
    assert out.action == "ask" and out.kind == "logic:off_by_one"
    assert "`sum_to_n(3)`" in out.prompt and "`for i in range(1, n):`" in out.prompt and "`i`" in out.prompt


def test_reflection_after_a_solve_names_the_technique():
    out = decide_reflection("accepted", "accepted", solved=True, load=None, events_since_last_prompt=None, pending=False, graded_attempts=2,
                            max_hint_level=2, hint_text=None, context={"pattern": "Running totals"})
    assert out.kind == "solved:assisted" and "running totals" in out.prompt and out.context["solved"] is True


def test_reflection_waits_when_overloaded_and_skips_syntax_slips():
    assert decide_reflection("partial", "logic:off_by_one", False, "high", None, False, 5, 2, None, context=CONTEXT).action == "defer"
    assert decide_reflection("syntax", "syntax:missing_colon", False, None, None, False, 5, 2, None).action == "skip"


# ---- the reply listens for the key idea, and never grades or gives the fix

def test_a_clear_answer_is_confirmed_and_pushed_one_step_further():
    reply = respond_to_answer("logic:off_by_one", CONTEXT, "range(1, n) stops before n, so i never reaches 3 and the last value is missed", OFF_BY_ONE)
    assert reply.quality == "specific" and "where `range` stops" in reply.matched
    assert "Good thinking" in reply.feedback and "range(1, n + 1)" not in reply.feedback


def test_a_vague_answer_gets_a_concrete_next_step():
    reply = respond_to_answer("logic:off_by_one", CONTEXT, "I think something is wrong with the loop maybe", OFF_BY_ONE)
    assert reply.quality == "partial" and "`i`" in reply.feedback and "`sum_to_n(3)`" in reply.feedback


def test_an_unsure_answer_gets_kindness_and_one_small_thing_to_try():
    reply = respond_to_answer("logic:off_by_one", CONTEXT, "I don't know", OFF_BY_ONE)
    assert reply.quality == "unsure" and reply.feedback.startswith("That's honest") and "first and last value" in reply.feedback


def test_a_one_word_answer_is_asked_for_a_little_more():
    assert respond_to_answer("solved:default", {"pattern": "Running totals"}, "loops", RIGHT).quality == "brief"


def test_reply_to_a_solved_problem_names_the_technique_idea():
    reply = respond_to_answer("solved:assisted", {"pattern": "Running totals"}, "It works because total adds each value of i in the loop until n", RIGHT)
    assert reply.quality == "specific" and "keeping a running total" in reply.matched


def test_reply_after_a_first_try_solve_follows_its_question_about_a_tricky_input():
    unsure = respond_to_answer("solved:first_try", {"pattern": "Running totals"}, "not sure", RIGHT)
    assert unsure.quality == "unsure" and "smallest or emptiest input" in unsure.feedback
    clear = respond_to_answer("solved:first_try", {"pattern": "Running totals"}, "An empty input, n = 0, because the loop never runs so total stays 0", RIGHT)
    assert clear.quality == "specific" and "an empty input" in clear.matched and "Run" in clear.feedback


# ---- through the real API

def _solve_with_help(learner):
    learner.submit(PROBLEM, OFF_BY_ONE)
    learner.hint(PROBLEM, OFF_BY_ONE)
    return learner.submit(PROBLEM, RIGHT)["response"]


def test_an_unsure_answer_holds_back_a_plan_that_was_moving_on(learner):
    response = learner.submit(PROBLEM, RIGHT)["response"]
    moving_on = response["plan"]
    assert learner.client.get(f"/api/problems/{moving_on['problem_id']}").json()["pattern"] != "Running totals", "a first-try solve moves to the next technique"
    reflection = response["reflection"]
    assert reflection, "a solve gets a question"
    reply = learner.client.post(f"/api/reflections/{reflection['id']}/answer", json={"answer": "not sure, I just changed it until it passed"}).json()
    assert reply["quality"] == "unsure" and reply["feedback"]
    assert reply["next"] and reply["next"]["reason_codes"] == ["REFLECTION_UNSURE"] and reply["next"]["problem_id"] != moving_on["problem_id"]
    nxt = learner.client.get(f"/api/problems/{reply['next']['problem_id']}").json()
    assert nxt["pattern"] == "Running totals" and nxt["unit_id"] == "loops"
    with session_scope() as db:
        row = db.get(Reflection, reflection["id"])
        assert row.quality == "unsure" and row.feedback == reply["feedback"] and row.kind == "solved:first_try"


def test_an_unsure_answer_does_not_repeat_a_plan_that_already_gives_one_more_problem(learner):
    response = _solve_with_help(learner)
    shown = learner.client.get(f"/api/problems/{response['plan']['problem_id']}").json()
    assert shown["pattern"] == "Running totals", "after a solve with help, the plan is already one more of the technique"
    reply = learner.client.post(f"/api/reflections/{response['reflection']['id']}/answer", json={"answer": "I don't know"}).json()
    assert reply["quality"] == "unsure" and reply["next"] is None


def test_a_short_answer_is_asked_for_more_and_leaves_the_plan_alone(learner):
    response = learner.submit(PROBLEM, RIGHT)["response"]
    reply = learner.client.post(f"/api/reflections/{response['reflection']['id']}/answer", json={"answer": "It works now."}).json()
    assert reply["quality"] == "brief" and "a little more" in reply["feedback"] and reply["next"] is None


def test_a_clear_answer_after_a_solve_leaves_the_plan_alone(learner):
    reflection = _solve_with_help(learner)["reflection"]
    reply = learner.client.post(f"/api/reflections/{reflection['id']}/answer", json={"answer": "range(1, n) stopped before n, so I added one to include the last value in total"}).json()
    assert reply["quality"] == "specific" and reply["next"] is None


def test_an_unsure_reflection_counts_as_one_sign_of_confusion_next_time(learner):
    for attempt in range(3):
        response = learner.submit(PROBLEM, OFF_BY_ONE + f"# try {attempt}\n")["response"]
    reflection = response["reflection"]
    assert reflection, "a question comes after three failed attempts"
    learner.client.post(f"/api/reflections/{reflection['id']}/answer", json={"answer": "no idea"})
    response = learner.submit(PROBLEM, OFF_BY_ONE + "# try again\n")["response"]
    assert any("not sure" in note for note in response["estimates"]["confusion_notes"])
    with session_scope() as db:
        assert db.scalar(select(Reflection.quality).where(Reflection.id == reflection["id"])) == "unsure"


# ---- the planner sequences practice like a teacher

def _units_and_problems(solved=()):
    units = [P.UnitView(id="a", title="A", order=1, track="foundations", optional=False, prerequisites=[], patterns=["First idea", "Second idea"]),
             P.UnitView(id="b", title="B", order=2, track="foundations", optional=False, prerequisites=["a"], patterns=["Third idea"]),
             P.UnitView(id="c", title="C", order=3, track="foundations", optional=False, prerequisites=["b"], patterns=["Fourth idea"])]
    spec = [("a1", "a", "easy", "First idea"), ("a2", "a", "easy", "Second idea"), ("a3", "a", "easy", "First idea"), ("a4", "a", "medium", "First idea"),
            ("a5", "a", "easy", "Second idea"), ("b1", "b", "easy", "Third idea"), ("c1", "c", "easy", "Fourth idea")]
    problems = [P.ProblemView(id=i, title=i.upper(), unit_id=u, difficulty=d, pattern=t, solved=i in solved, attempted=i in solved) for i, u, d, t in spec]
    return units, problems


def test_a_slow_solve_gets_a_second_problem_of_the_same_technique():
    units, problems = _units_and_problems(solved={"a1"})
    out = P.plan(P.PlannerInput(units=units, problems=problems, current_problem=problems[0], solved_now=True, graded_attempts_on_problem=3))
    assert out.problem_id == "a3" and out.reason_codes == ["CONSOLIDATE_TECHNIQUE"] and out.action == "similar_independent"


def test_a_fluent_solve_moves_to_the_next_technique_at_the_same_level():
    units, problems = _units_and_problems(solved={"a1"})
    out = P.plan(P.PlannerInput(units=units, problems=problems, current_problem=problems[0], solved_now=True, graded_attempts_on_problem=1))
    assert out.problem_id == "a2" and out.reason_codes == ["NEXT_TECHNIQUE"] and out.action == "similar_independent"


def test_medium_comes_after_every_technique_is_practised_at_easy():
    units, problems = _units_and_problems(solved={"a1", "a3", "a2", "a5"})
    out = P.plan(P.PlannerInput(units=units, problems=problems, current_problem=problems[4], solved_now=True, graded_attempts_on_problem=2))
    assert out.problem_id == "a4" and out.reason_codes == ["STEP_UP_DIFFICULTY"] and out.action == "harder_next"


def test_the_next_topic_is_forward_never_back_to_a_skipped_one():
    units, problems = _units_and_problems(solved={"b1"})
    units[1].mastery, units[1].independent, units[1].evidence = 0.9, 3, 3.0
    out = P.plan(P.PlannerInput(units=units, problems=problems, current_problem=problems[5], solved_now=True, graded_attempts_on_problem=1))
    assert out.unit_id == "c" and out.reason_codes == ["READY_NEXT_UNIT"]
    assert [step["unit_id"] for step in out.route] == ["b", "c"] and out.route[0]["status"] == "secure"


def test_home_continues_the_topic_being_worked_on():
    units, problems = _units_and_problems(solved={"b1"})
    problems.insert(0, problems.pop(5))  # most recent work first, as the planner receives it
    units[1].evidence = 1.0
    out = P.plan(P.PlannerInput(units=units, problems=problems))
    assert out.unit_id in ("b", "c") and out.unit_id != "a", "a learner working in B is not sent back to A"


def test_unsure_reflection_on_a_solve_earns_one_more_of_the_same_technique():
    units, problems = _units_and_problems(solved={"a1"})
    data = P.PlannerInput(units=units, problems=problems, current_problem=problems[0], solved_now=True)
    assert P.after_reflection(data, "unsure").problem_id == "a3"
    assert P.after_reflection(data, "specific") is None
    assert P.after_reflection(data, "brief") is None, "a short answer is not evidence the idea is unsettled"


def test_home_and_the_plan_after_a_fluent_solve_suggest_the_same_next_step():
    units, problems = _units_and_problems(solved={"a1"})
    after_submit = P.plan(P.PlannerInput(units=units, problems=problems, current_problem=problems[0], solved_now=True, graded_attempts_on_problem=1))
    problems[0].fluent = True  # what load_planner_views records for a first-try solve without hints
    home = P.plan(P.PlannerInput(units=units, problems=problems))
    assert after_submit.problem_id == home.problem_id == "a2"


def test_a_technique_solved_with_help_still_gets_its_second_problem_after_a_fluent_one_elsewhere():
    units, problems = _units_and_problems(solved={"a1", "a2"})
    out = P.plan(P.PlannerInput(units=units, problems=problems, current_problem=problems[1], solved_now=True, graded_attempts_on_problem=1))
    assert out.problem_id == "a3" and out.reason_codes == ["NEXT_TECHNIQUE"]
    assert "comes earlier in the lesson and needs one more solve" in out.reason


def test_home_agrees_with_the_plan_after_a_first_try_solve(learner):
    plan = learner.submit(PROBLEM, RIGHT)["response"]["plan"]
    home = learner.client.get("/api/home").json()["recommendation"]
    assert plan["problem_id"] == home["problem_id"], (plan["title"], home["title"])
    assert learner.client.get(f"/api/problems/{plan['problem_id']}").json()["pattern"] != "Running totals"


def test_a_hint_before_the_first_submit_means_the_solve_was_not_fluent(learner):
    learner.hint(PROBLEM, OFF_BY_ONE)
    learner.submit(PROBLEM, RIGHT)
    home = learner.client.get("/api/home").json()["recommendation"]
    assert learner.client.get(f"/api/problems/{home['problem_id']}").json()["pattern"] == "Running totals"


def test_the_route_shows_the_next_topic_even_while_the_current_one_is_not_secure():
    units, problems = _units_and_problems(solved={"a1"})
    units[0].mastery, units[0].evidence = 0.3, 3.0  # working in A, and A is weak for now
    out = P.plan(P.PlannerInput(units=units, problems=problems, current_problem=problems[0], solved_now=True, graded_attempts_on_problem=3))
    assert [step["unit_id"] for step in out.route] == ["a", "b", "c"], "B comes after A, and C after B"


def test_the_planner_never_jumps_past_a_held_back_topic_to_one_that_needs_it():
    units, problems = _units_and_problems()
    units[0].mastery, units[0].evidence = 0.3, 3.0  # A is weak and still has problems, so B is held back
    data = P.PlannerInput(units=units, problems=problems)
    assert P._next_unit(data, units[0]) is None, "C builds on B, so it is not offered in B's place"


def test_home_calls_a_second_problem_of_the_same_technique_consolidation_not_a_new_technique():
    units, problems = _units_and_problems(solved={"a1"})
    problems.insert(0, problems.pop(0))
    out = P.plan(P.PlannerInput(units=units, problems=problems))
    assert out.problem_id == "a3" and "CONSOLIDATE_TECHNIQUE" in out.reason_codes and out.title.startswith("One more first idea problem")
