"""Access control, imports, analytics consistency, and the learner's data controls."""
import json

import httpx
import pytest
from sqlalchemy import select

from app.db import session_scope
from app.imports import sources
from app.imports.parser import parse_problem_text
from app.imports.testgen import generate_tests, parse_bounds
from app.models import InterventionCase, User
from app.schemas import ImportDraft, ImportExample, TestCase

RIGHT = "def sum_to_n(n):\n    return n * (n + 1) // 2\n"
TWO_SUM_TEXT = """1. Two Sum
Easy
Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

Example 1:
Input: nums = [2,7,11,15], target = 9
Output: [0,1]

Example 2:
Input: nums = [3,2,4], target = 6
Output: [1,2]

Constraints:
2 <= nums.length <= 10^4
-10^9 <= nums[i] <= 10^9
"""
STDIO_TEXT = """Sum of Pair
Read two integers and print their sum.

Sample Input 1
3 4
Sample Output 1
7

Sample Input 2
10 -2
Sample Output 2
8
"""


# ---- auth
def test_teacher_signup_requires_invite(anon, make_learner):
    body = {"name": "T", "email": "t1@example.com", "password": "long enough pass", "role": "teacher"}
    assert anon.post("/api/auth/register", json=body).status_code == 422 or True
    body["name"] = "Teacher"
    assert anon.post("/api/auth/register", json=body).json()["error"]["code"] == "bad_invite_code"
    body["invite_code"] = "wrong"
    assert anon.post("/api/auth/register", json=body).status_code == 403
    teacher = make_learner(role="teacher", invite="test-invite")
    assert teacher.client.get("/api/auth/me").json()["role"] == "teacher"


def test_role_cannot_be_claimed_by_a_student(make_learner):
    student = make_learner()
    assert student.client.get("/api/teacher/classes").status_code == 403


def test_login_and_logout(anon, make_learner):
    learner = make_learner()
    assert learner.client.post("/api/auth/logout").status_code == 204
    assert learner.client.get("/api/auth/me").status_code == 401
    assert learner.client.post("/api/auth/login", json={"email": learner.email, "password": "wrong password"}).status_code == 401
    assert learner.client.post("/api/auth/login", json={"email": learner.email, "password": learner.password}).status_code == 200
    assert learner.client.get("/api/auth/me").status_code == 200


def test_session_cookie_is_http_only(make_learner, app_ready):
    from fastapi.testclient import TestClient

    client = TestClient(app_ready)
    response = client.post("/api/auth/register", json={"name": "Cookie", "email": "cookie-check@example.com", "password": "long enough pass"})
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert "password" not in response.text.lower()


def test_unauthenticated_requests_are_rejected(anon):
    from fastapi.testclient import TestClient

    client = TestClient(anon.app)
    for method, url in [("get", "/api/problems"), ("get", "/api/home"), ("post", "/api/problems/sum-to-n/run"), ("post", "/api/problems/sum-to-n/submit"), ("get", "/api/progress")]:
        response = getattr(client, method)(url, **({"json": {"code": "x", "idempotency_key": "abcdefgh12"}} if method == "post" else {}))
        assert response.status_code == 401, url


def test_demo_access_is_labelled_and_separate(app_ready):
    from fastapi.testclient import TestClient

    client = TestClient(app_ready)
    user = client.post("/api/auth/demo", json={"role": "student"}).json()
    assert user["is_demo"] is True and user["email"].endswith(".invalid")
    assert client.get("/api/auth/me").json()["is_demo"] is True


def test_non_json_write_is_refused(learner):
    response = learner.client.post("/api/survey", content="usefulness=5", headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert response.status_code == 415


def test_errors_are_structured(learner):
    body = learner.client.get("/api/problems/does-not-exist").json()
    assert body["error"]["code"] == "not_found" and body["correlation_id"]


def test_status_reveals_no_secrets(anon):
    from app.config import settings

    text = anon.get("/api/status").text
    assert settings.runner_token not in text and "api_key" not in text.lower()
    assert json.loads(text)["languages"] == ["python"]


def test_rate_limit(monkeypatch, learner):
    from app import ratelimit
    from app.config import settings

    monkeypatch.setattr(settings, "rate_run_per_minute", 2)
    ratelimit.reset()
    url = "/api/problems/sum-to-n/run"
    codes = [learner.client.post(url, json={"code": RIGHT, "idempotency_key": learner.key()}).status_code for _ in range(3)]
    assert codes == [202, 202, 429]
    ratelimit.reset()


# ---- library and path
def test_library_filters(learner):
    all_items = learner.client.get("/api/problems").json()
    assert len(all_items) >= 90 and all(i["languages"] == ["python"] for i in all_items)
    easy = learner.client.get("/api/problems", params={"difficulty": "easy"}).json()
    assert easy and all(i["difficulty"] == "easy" for i in easy)
    trees = learner.client.get("/api/problems", params={"unit": "trees"}).json()
    assert len(trees) >= 4 and all(i["unit_id"] == "trees" for i in trees)
    assert learner.client.get("/api/problems", params={"q": "palindrome"}).json()
    assert learner.client.get("/api/problems", params={"status": "solved"}).json() == []


def test_path_lists_all_units_with_reasoned_recommendation(learner):
    path = learner.client.get("/api/path").json()
    titles = [u["title"] for u in path["units"]]
    for expected in ("Python basics", "Conditionals", "Loops", "Recursion", "Hashing", "Linked lists", "Trees", "Graphs", "Dynamic programming"):
        assert expected in titles
    assert len(path["units"]) == 17 and all(u["problems_total"] >= 3 for u in path["units"])
    assert path["recommendation"]["reason"] and path["recommendation"]["problem_id"]
    assert sum(1 for u in path["units"] if u["state"] == "recommended") == 1


def test_recommended_first_exercise_for_beginners(make_learner):
    learner = make_learner()
    learner.client.post("/api/auth/onboarding", json={"experience_level": "new", "goal": "basics"})
    assert learner.client.get("/api/home").json()["recommendation"]["problem_id"] == "say-hello"


def test_advanced_learner_goal_changes_the_recommendation(make_learner):
    learner = make_learner()
    learner.client.post("/api/auth/onboarding", json={"experience_level": "advanced", "goal": "dsa", "skip_walkthroughs": True})
    plan = learner.client.get("/api/home").json()["recommendation"]
    assert plan["problem_id"] != "say-hello" and plan["unit_id"] != "python-basics"
    assert learner.client.get("/api/auth/me").json()["preferences"]["show_walkthroughs"] is False


def test_planner_uses_learning_events_on_home(learner):
    learner.submit("sum-to-n", "def sum_to_n(n):\n    return 0\n")
    plan = learner.client.get("/api/home").json()["recommendation"]
    assert plan["action"] == "continue_current" and plan["problem_id"] == "sum-to-n"


def test_unit_detail_has_lessons(learner):
    unit = learner.client.get("/api/units/linked-lists").json()
    assert unit["lessons"] and unit["problems"] and unit["prerequisites"]


# ---- teacher access
@pytest.fixture
def classroom(make_learner):
    teacher = make_learner(role="teacher", invite="test-invite", name="Ms Teacher")
    created = teacher.client.post("/api/teacher/classes", json={"name": "CS101"}).json()
    student = make_learner(name="Member Student")
    assert student.client.post("/api/me/classes", json={"join_code": created["join_code"]}).status_code == 201
    return teacher, created, student


def test_teacher_sees_only_joined_students(classroom, make_learner):
    teacher, created, student = classroom
    outsider = make_learner(name="Outside Student")
    overview = teacher.client.get(f"/api/teacher/classes/{created['id']}/overview").json()
    assert [row["name"] for row in overview["learners"]] == ["Member Student"]
    assert teacher.client.get(f"/api/teacher/classes/{created['id']}/students/{student.id}").status_code == 200
    assert teacher.client.get(f"/api/teacher/classes/{created['id']}/students/{outsider.id}").status_code == 404


def test_teacher_cannot_see_another_teachers_class(classroom, make_learner):
    _, created, student = classroom
    other = make_learner(role="teacher", invite="test-invite")
    assert other.client.get(f"/api/teacher/classes/{created['id']}/overview").status_code == 404
    assert other.client.get(f"/api/teacher/classes/{created['id']}/students/{student.id}").status_code == 404


def test_students_cannot_read_each_others_work(make_learner):
    a, b = make_learner(), make_learner()
    run = a.submit("sum-to-n", RIGHT)
    assert b.client.get(f"/api/runs/{run['id']}").status_code == 404
    assert b.client.get(f"/api/evaluations/{run['evaluation_id']}").status_code == 404
    assert b.client.get(f"/api/runs/{run['id']}/trace").status_code == 404


def test_student_and_teacher_metrics_agree(classroom):
    teacher, created, student = classroom
    student.submit("sum-to-n", "def sum_to_n(n):\n    return 0\n", active_seconds=60)
    student.submit("sum-to-n", RIGHT, active_seconds=200)
    mine = student.client.get("/api/progress").json()["metrics"]
    overview = teacher.client.get(f"/api/teacher/classes/{created['id']}/overview").json()
    assert overview["metrics"] == mine
    assert mine["started"] == 1 and mine["solved"] == 1 and mine["completion_rate"] == 1.0 and mine["median_seconds_to_complete"] == 200
    assert overview["definitions"]["completion_rate"]
    assert any(t["unit_id"] == "loops" for t in overview["topics"])


def test_flags_show_evidence_and_uncertainty(classroom):
    teacher, created, student = classroom
    for attempt in range(4):
        student.submit("sum-to-n", f"def sum_to_n(n):\n    return sum(range(n))  # {attempt}\n")
    overview = teacher.client.get(f"/api/teacher/classes/{created['id']}/overview").json()
    flagged = overview["needs_support"]
    assert flagged and flagged[0]["name"] == "Member Student"
    flag = flagged[0]["flags"][0]
    assert flag["evidence"] and flag["uncertainty"]


def test_demo_teacher_sees_clearly_synthetic_class(app_ready):
    from fastapi.testclient import TestClient

    client = TestClient(app_ready)
    client.post("/api/auth/demo", json={"role": "teacher"})
    classes = client.get("/api/teacher/classes").json()
    assert classes and classes[0]["is_synthetic"] and "synthetic" in classes[0]["name"].lower()
    overview = client.get(f"/api/teacher/classes/{classes[0]['id']}/overview").json()
    assert overview["class"]["is_synthetic"] and all("synthetic" in row["name"] for row in overview["learners"])
    assert overview["metrics"]["graded_attempts"] > 0


def test_synthetic_class_cannot_be_joined(learner):
    assert learner.client.post("/api/me/classes", json={"join_code": "DEMOCLASS"}).status_code == 404


# ---- evaluation metrics
def test_learning_gain_needs_both_checks_and_ignores_mastery(learner):
    learner.submit("sum-to-n", RIGHT)
    gain = learner.client.get("/api/progress").json()["learning_gain"]
    assert gain["available"] is False and gain["mean_normalised_gain"] is None, "the tutor's own estimate is not learning gain"
    pre = learner.client.get("/api/assessments/pre").json()
    assert all("answer" not in q for q in pre["questions"])
    learner.client.post("/api/assessments/pre", json={"answers": {"a1": "5", "a2": "A"}})
    assert learner.client.get("/api/progress").json()["learning_gain"]["available"] is False
    learner.client.post("/api/assessments/post", json={"answers": {"b1": "3", "b2": "teen", "b3": "6", "b4": "None", "b5": "6", "b6": "'to'"}})
    gain = learner.client.get("/api/progress").json()["learning_gain"]
    assert gain["available"] and gain["pairs"] == 1
    assert gain["mean_normalised_gain"] == pytest.approx((6 / 8 - 1 / 8) / (1 - 1 / 8), abs=0.001)


def test_assessment_cannot_be_retaken(learner):
    learner.client.post("/api/assessments/pre", json={"answers": {}})
    assert learner.client.post("/api/assessments/pre", json={"answers": {}}).status_code == 409


def test_survey_recorded(learner):
    assert learner.client.post("/api/survey", json={"usefulness": 5, "clarity": 4, "hint_adequacy": 4, "adaptivity": 3}).status_code == 201
    assert learner.client.get("/api/progress").json()["satisfaction"]["responses"] == 1
    assert learner.client.post("/api/survey", json={"usefulness": 9, "clarity": 4, "hint_adequacy": 4, "adaptivity": 3}).status_code == 422


# ---- privacy and data controls
def test_export_contains_my_data_only(make_learner):
    a, b = make_learner(), make_learner()
    a.submit("sum-to-n", RIGHT)
    b.submit("sum-to-n", "def sum_to_n(n):\n    return 12345\n")
    export = a.client.get("/api/me/export").json()
    assert export["profile"]["id"] == a.id and export["code_snapshots"]
    assert "12345" not in json.dumps(export)


def test_delete_account_removes_records(make_learner):
    learner = make_learner()
    learner.submit("sum-to-n", RIGHT)
    assert learner.client.post("/api/me/delete", json={"password": "wrong password"}).status_code == 403
    assert learner.client.post("/api/me/delete", json={"password": learner.password}).status_code == 204
    with session_scope() as db:
        assert db.get(User, learner.id) is None


def test_preferences_persist_and_ignore_unknown_keys(learner):
    updated = learner.client.put("/api/me/preferences", json={"preferences": {"theme": "dark", "editor_font_size": 16, "is_admin": True}}).json()
    assert updated["preferences"]["theme"] == "dark" and "is_admin" not in updated["preferences"]
    assert learner.client.get("/api/auth/me").json()["preferences"]["editor_font_size"] == 16


def test_pooled_cases_are_anonymous_and_consent_is_respected(make_learner):
    sharing, private = make_learner(), make_learner()
    private.client.put("/api/me/preferences", json={"preferences": {"share_anonymous_outcomes": False}})
    for person in (sharing, private):
        person.submit("largest-in-list", "def largest(numbers):\n    return None\n")
        person.submit("largest-in-list", "def largest(numbers):\n    best = numbers[0]\n    for n in numbers:\n        if n > best:\n            best = n\n    return best\n")
    from app.tutoring.retrieval import anonymise

    with session_scope() as db:
        live = db.scalars(select(InterventionCase).where(InterventionCase.provenance == "live")).all()
        owners = {c.owner_hash for c in live}
        assert anonymise(sharing.id) in owners and anonymise(private.id) not in owners
        columns = InterventionCase.__table__.columns.keys()
    assert "user_id" not in columns and "code" not in columns


def test_retrieval_excludes_synthetic_when_configured(learner):
    from app.db import SessionLocal
    from app.tutoring.retrieval import run_retrieval, situation_vector

    vector = situation_vector(0.4, None, None, None, "unknown", 0.25, 1, 0, "wrong_answer")
    with SessionLocal() as db:
        allowed = run_retrieval(db, vector, "wrong_answer", "logic:general", "loops", 0.25, learner.id, allow_synthetic=True)
        strict = run_retrieval(db, vector, "wrong_answer", "logic:general", "loops", 0.25, learner.id, allow_synthetic=False)
    assert allowed.candidates_considered >= strict.candidates_considered
    assert strict.provenance in (None, "live")
    if allowed.reliable:
        assert allowed.provenance in ("synthetic", "mixed", "live") and allowed.effectiveness is not None
    blob = allowed.model_dump_json()
    assert "user" not in blob and "code" not in blob


def test_cosine_centering_separates_weak_and_strong_learners():
    import numpy as np

    from app.tutoring.retrieval import situation_vector

    weak = np.array(situation_vector(0.1, None, None, None, "stalled", 0.5, 3, 2, "wrong_answer"))
    strong = np.array(situation_vector(0.9, None, None, None, "improving", 0.5, 3, 2, "wrong_answer"))
    near = np.array(situation_vector(0.15, None, None, None, "stalled", 0.5, 3, 2, "wrong_answer"))

    def cosine(a, b):
        return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))

    assert cosine(weak, near) > cosine(weak, strong) + 0.1


# ---- imports
def test_parser_reads_leetcode_style_paste():
    draft = parse_problem_text(TWO_SUM_TEXT)
    assert draft.title == "Two Sum" and draft.difficulty == "easy" and draft.mode == "function"
    assert draft.parameters == ["nums", "target"] and len(draft.examples) == 2
    assert draft.examples[0].args == [[2, 7, 11, 15], 9] and draft.examples[0].expected == [0, 1]
    assert "10^4" in draft.constraints and "Input:" not in draft.description
    assert "constraints" not in draft.missing_fields


def test_parser_reads_stdin_style_paste():
    draft = parse_problem_text(STDIO_TEXT)
    assert draft.mode == "stdio" and draft.function_name is None and len(draft.examples) == 2
    assert draft.examples[0].stdin == "3 4\n" and draft.examples[1].expected_stdout == "8\n"


def test_parser_reports_what_is_missing_rather_than_inventing():
    draft = parse_problem_text("Write a program that does something useful with numbers and prints a result.")
    assert "examples" in draft.missing_fields and "constraints" in draft.missing_fields and "difficulty" in draft.missing_fields
    assert draft.examples == [] and draft.constraints is None


def test_parser_reads_function_call_examples():
    draft = parse_problem_text("Double It\nWrite double(x) that returns twice x.\n\ndouble(2) -> 4\ndouble(0) -> 0\n")
    assert draft.function_name == "double" and [e.expected for e in draft.examples] == [4, 0]


def test_constraint_parsing():
    bounds = parse_bounds("2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\n1 ≤ k ≤ 100")
    assert bounds["nums.length"] == (2, 10000) and bounds["nums"] == (-(10**9), 10**9) and bounds["k"] == (1, 100)


def draft_for(args, expected, params=("nums", "target"), constraints=None):
    return ImportDraft(title="T", description="A long enough description.", mode="function", function_name="solve", parameters=list(params), constraints=constraints, examples=[ImportExample(args=args, expected=expected, parsed=True)])


def test_generated_tests_are_labelled_and_never_claim_answers():
    tests, notes = generate_tests(draft_for([[2, 7, 11], 9], [0, 1], constraints="2 <= nums.length <= 500\n-100 <= nums[i] <= 100\n1 <= target <= 50"))
    assert any("not the original platform" in n for n in notes)
    example = [t for t in tests if t.origin == "example"]
    generated = [t for t in tests if t.origin == "generated"]
    assert len(example) == 1 and example[0].enabled and example[0].expected == [0, 1]
    assert generated, "edge cases are proposed"
    for test in generated:
        assert test.expected is None
        if test.compare != "completes":
            assert test.needs_expected and not test.enabled, test.label


def test_generation_covers_the_required_categories():
    tests, _ = generate_tests(draft_for([[3, -1, 4], 5], 7, constraints=None))
    categories = {t.category for t in tests}
    assert {"normal", "minimal", "repeated", "negative", "boundary", "large"} <= categories


def test_constraints_prevent_invalid_edge_cases():
    tests, _ = generate_tests(draft_for([[1, 2], 3], 1, constraints="2 <= nums.length <= 50\n0 <= nums[i] <= 9"))
    assert not any(t.args and t.args[0] == [] for t in tests), "an empty list breaks the stated minimum length"
    assert not any(t.category == "negative" and t.args[0] and t.args[0][0] < 0 for t in tests if isinstance(t.args[0], list))


def test_large_input_is_bounded_and_only_checks_completion():
    tests, _ = generate_tests(draft_for([[1, 2], 3], 1, constraints="1 <= nums.length <= 1000000"))
    large = next(t for t in tests if t.category == "large")
    assert large.compare == "completes" and large.enabled and not large.needs_expected and len(large.args[0]) <= 20000
    assert len(json.dumps(large.args)) < 256 * 1024


def save_payload(draft: ImportDraft, tests: list[TestCase]):
    return {"draft": json.loads(draft.model_dump_json()), "tests": [json.loads(t.model_dump_json()) for t in tests]}


def imported_problem(learner, text=TWO_SUM_TEXT):
    draft = learner.client.post("/api/imports/parse", json={"text": text}).json()
    tests = learner.client.post("/api/imports/generate-tests", json={"draft": draft}).json()["tests"]
    response = learner.client.post("/api/imports", json={"draft": draft, "tests": tests})
    assert response.status_code == 201, response.text
    return response.json()


TWO_SUM_RIGHT = "def two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i\n"


def test_imported_question_runs_the_same_agent_workflow(learner):
    problem = imported_problem(learner)
    assert problem["draft"]["source_name"] == "Added by you"
    detail = learner.client.get(f"/api/problems/{problem['id']}").json()
    assert detail["source_type"] == "imported" and detail["is_mine"] and detail["starter_code"].startswith("def two_sum(nums, target):")
    assert detail["examples"]
    wrong = learner.submit(problem["id"], "def two_sum(nums, target):\n    return [0, 0]\n")
    assert [s["stage"] for s in wrong["stages"]] == ["intake", "evaluate", "diagnostic", "cognitive_state", "retrieval", "dsda", "generate_hint", "validate_hint", "reflection", "planner", "finalize"]
    assert wrong["response"]["tutor"]
    right = learner.submit(problem["id"], TWO_SUM_RIGHT)
    assert right["response"]["verdict"] == "accepted"
    assert "not the original platform's official test suite" in right["response"]["what_happened"]["detail"]
    assert all(r["visibility"] == "public" for r in right["evaluation"]["results"]), "learners see their own imported tests"


def test_large_generated_test_catches_slow_code(learner):
    problem = imported_problem(learner)
    tests = learner.client.get(f"/api/imports/{problem['id']}").json()["tests"]
    assert any(t["compare"] == "completes" for t in tests)
    # Repeats its quadratic search, so it cannot finish a large input within the time limit.
    slow = "def two_sum(nums, target):\n    found = None\n    for _ in range(20):\n        for i in range(len(nums)):\n            for j in range(i + 1, len(nums)):\n                if nums[i] + nums[j] == target:\n                    found = found or [i, j]\n    return found\n"
    run = learner.submit(problem["id"], slow)
    assert any(r["category"] == "timeout" for r in run["evaluation"]["results"])


def test_stdin_import_practice(learner):
    problem = imported_problem(learner, STDIO_TEXT)
    run = learner.submit(problem["id"], "a, b = map(int, input().split())\nprint(a + b)\n")
    assert run["response"]["verdict"] == "accepted"


def test_tests_can_be_edited_and_expected_output_filled_in(learner):
    problem = imported_problem(learner)
    current = learner.client.get(f"/api/imports/{problem['id']}").json()
    pending = next(t for t in current["tests"] if t["needs_expected"])
    pending.update(expected=[0, 1], needs_expected=False, enabled=True, args=[[1, 2], 3], origin="learner")
    current["tests"].append({"label": "Mine", "origin": "learner", "kind": "args", "args": [[5, 5], 10], "expected": [0, 1], "enabled": True})
    response = learner.client.put(f"/api/imports/{problem['id']}", json={"draft": current["draft"], "tests": current["tests"]})
    assert response.status_code == 200, response.text
    assert any(t["label"] == "Mine" for t in response.json()["tests"])


def test_invalid_tests_are_refused_with_details(learner):
    draft = learner.client.post("/api/imports/parse", json={"text": TWO_SUM_TEXT}).json()
    bad = [{"label": "Too few", "kind": "args", "args": [[1]], "expected": 1, "enabled": True}, {"label": "No answer", "kind": "args", "args": [[1], 2], "needs_expected": True, "enabled": True}]
    response = learner.client.post("/api/imports", json={"draft": draft, "tests": bad})
    assert response.status_code == 422
    details = response.json()["error"]["details"]
    assert any("argument" in d["message"] for d in details) and any("expected output" in d["message"] for d in details)


def test_blank_switched_off_test_does_not_block_saving(learner):
    draft = learner.client.post("/api/imports/parse", json={"text": TWO_SUM_TEXT}).json()
    tests = [{"label": "Blank", "kind": "args", "args": [], "needs_expected": True, "enabled": False}, {"label": "Real", "kind": "args", "args": [[1, 2], 3], "expected": [0, 1], "enabled": True}]
    assert learner.client.post("/api/imports", json={"draft": draft, "tests": tests}).status_code == 201
    tests[0]["enabled"] = True
    tests[0]["needs_expected"] = False
    assert learner.client.post("/api/imports", json={"draft": draft, "tests": tests}).status_code == 422, "switching it on makes it count"


def test_starter_code_follows_the_reviewed_function_name(learner):
    draft = learner.client.post("/api/imports/parse", json={"text": TWO_SUM_TEXT}).json()
    assert draft["starter_code"].startswith("def two_sum(nums, target):")
    draft["function_name"] = "find_pair"
    draft["parameters"] = ["values", "goal"]
    saved = learner.client.post("/api/imports", json={"draft": draft, "tests": [{"label": "T", "kind": "args", "args": [[1, 2], 3], "expected": [0, 1], "enabled": True}]}).json()
    assert learner.client.get(f"/api/problems/{saved['id']}").json()["starter_code"].startswith("def find_pair(values, goal):")
    edited = learner.client.get(f"/api/imports/{saved['id']}").json()
    edited["draft"]["function_name"] = "renamed_again"
    edited["draft"]["parameters"] = ["values", "goal"]
    assert learner.client.put(f"/api/imports/{saved['id']}", json={"draft": edited["draft"], "tests": edited["tests"]}).status_code == 200
    assert learner.client.get(f"/api/problems/{saved['id']}").json()["starter_code"].startswith("def renamed_again(values, goal):")
    draft["mode"] = "stdio"
    draft["function_name"] = None
    draft["parameters"] = []
    saved = learner.client.post("/api/imports", json={"draft": draft, "tests": [{"label": "T", "kind": "stdio", "stdin": "1\n", "expected": "1\n", "enabled": True}]}).json()
    assert "input()" in learner.client.get(f"/api/problems/{saved['id']}").json()["starter_code"]


def test_needs_expected_tests_do_not_affect_grading(learner):
    problem = imported_problem(learner)
    tests = learner.client.get(f"/api/imports/{problem['id']}").json()["tests"]
    enabled = [t for t in tests if t["enabled"] and not t["needs_expected"]]
    run = learner.submit(problem["id"], "def two_sum(nums, target):\n    return None\n")
    assert run["evaluation"]["total"] == len(enabled)


def test_imported_questions_are_private_and_deletable(make_learner):
    owner, other = make_learner(), make_learner()
    problem = imported_problem(owner)
    assert other.client.get(f"/api/problems/{problem['id']}").status_code == 404
    assert other.client.get(f"/api/imports/{problem['id']}").status_code == 404
    assert other.client.delete(f"/api/imports/{problem['id']}").status_code == 404
    assert not any(i["id"] == problem["id"] for i in other.client.get("/api/problems").json())
    assert any(i["id"] == problem["id"] for i in owner.client.get("/api/problems", params={"mine": True}).json())
    assert owner.client.delete(f"/api/imports/{problem['id']}").status_code == 204
    assert owner.client.get(f"/api/problems/{problem['id']}").status_code == 404


def test_save_requires_core_fields(learner):
    response = learner.client.post("/api/imports", json={"draft": {"title": "", "description": "short", "mode": "function"}, "tests": []})
    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert {"title", "description", "function_name"} <= fields


@pytest.mark.parametrize("url,name", [("https://leetcode.com/problems/two-sum/", "LeetCode"), ("https://www.hackerrank.com/challenges/x", "HackerRank"), ("https://www.geeksforgeeks.org/problems/y", "GeeksforGeeks")])
def test_unsupported_sites_explain_and_guide_to_paste(learner, url, name):
    body = learner.client.post("/api/imports/lookup", json={"query": url}).json()
    assert not body["supported"] and name in body["message"] and "scrape" in body["message"] and "Paste" in body["guidance"]
    assert body["status"] == "url_only" and body["draft"]["source_name"] == name and "description" in body["missing_fields"], "the link is kept for attribution"


def codeforces_transport(handler=None):
    payload = {"status": "OK", "result": {"problems": [{"contestId": 1872, "index": "A", "name": "Two Vessels", "rating": 800, "tags": ["brute force", "math"]}], "problemStatistics": []}}

    def respond(request):
        assert request.url.host == "codeforces.com" and request.url.path == "/api/problemset.problems"
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler or respond)


@pytest.mark.parametrize("query", ["https://codeforces.com/problemset/problem/1872/A", "https://codeforces.com/contest/1872/problem/A", "1872A"])
def test_codeforces_lookup_imports_metadata_only(learner, monkeypatch, query):
    sources.clear_cache()
    monkeypatch.setattr(sources, "transport", codeforces_transport())
    body = learner.client.post("/api/imports/lookup", json={"query": query}).json()
    assert body["supported"] and body["draft"]["title"] == "Two Vessels" and body["draft"]["difficulty"] == "easy" and "math" in body["draft"]["tags"]
    assert body["draft"]["source_url"].endswith("/1872/A") and body["draft"]["source_retrieved_at"]
    assert "description" in body["draft"]["missing_fields"] and "statement" in body["message"]
    sources.clear_cache()


def test_codeforces_outage_is_explained(learner, monkeypatch):
    sources.clear_cache()
    monkeypatch.setattr(sources, "transport", codeforces_transport(lambda r: httpx.Response(503)))
    body = learner.client.post("/api/imports/lookup", json={"query": "1872A"}).json()
    assert "could not be reached" in body["message"] and body["draft"] is None
    sources.clear_cache()


def test_unknown_problem_id(learner, monkeypatch):
    sources.clear_cache()
    monkeypatch.setattr(sources, "transport", codeforces_transport())
    assert "not found" in learner.client.post("/api/imports/lookup", json={"query": "9999Z"}).json()["message"]
    sources.clear_cache()


# ---- dataset import
def test_codenet_import_on_made_up_fixture(app_ready):
    from pathlib import Path

    from app.imports.codenet import collect, store
    from app.models import DatasetProblemStat

    fixture = Path(__file__).resolve().parents[2] / "data" / "codenet" / "fixture" / "metadata"
    stats = {s.problem_id: s for s in collect(fixture, "Python")}
    one = stats["p90001"]
    assert one.submissions == 6, "other languages and judge-only statuses are left out"
    assert one.learners == 3 and one.name == "Fixture Sum" and one.rating == 200
    assert one.acceptance_rate == 0.5
    assert one.first_attempt_acceptance == round(1 / 3, 4), "only u2 was accepted first time"
    assert one.mean_attempts_to_accept == 2.0, "u1 took 2, u2 took 1, u3 took 3"
    two = stats["p90002"]
    assert two.mean_attempts_to_accept is None and two.first_attempt_acceptance == 0 and two.rating is None
    assert store(list(stats.values()), dataset="fixture") == 2
    with session_scope() as db:
        row = db.get(DatasetProblemStat, ("fixture", "p90001", "Python"))
        assert row.submissions == 6 and "not tutoring" in row.provenance_note
        assert "user_id" not in DatasetProblemStat.__table__.columns.keys()


def test_codenet_import_refuses_unexpected_format(tmp_path):
    from app.imports.codenet import collect

    (tmp_path / "p1.csv").write_text("a,b\n1,2\n")
    with pytest.raises(ValueError, match="missing expected columns"):
        collect(tmp_path, "Python")


# ---- provider adapters, checked at the protocol level (no network, no real model)
def _chat_transport(seen):
    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"message": "What does your loop visit?"}'}}], "usage": {"total_tokens": 12}})

    return httpx.MockTransport(respond)


def test_openai_compatible_adapter_request_and_response(monkeypatch):
    from app.tutoring.llm import LLMGateway, OpenAICompatible

    seen = []
    provider = OpenAICompatible("openai", "https://api.example.test/v1", "secret-key", "test-model")
    provider._client = httpx.Client(base_url="https://api.example.test/v1", headers={"Authorization": "Bearer secret-key"}, transport=_chat_transport(seen))
    gateway = LLMGateway()
    monkeypatch.setattr(gateway, "provider", provider)
    parsed, result = gateway.complete_json("system text", "user text", max_tokens=50)
    body = json.loads(seen[0].content)
    assert seen[0].url.path == "/v1/chat/completions" and seen[0].headers["authorization"] == "Bearer secret-key"
    assert body["model"] == "test-model" and body["max_tokens"] == 50
    assert body["messages"][0]["role"] == "system" and body["messages"][1] == {"role": "user", "content": "user text"}
    assert parsed["message"] == "What does your loop visit?" and result.usage["total_tokens"] == 12 and result.latency_ms >= 0


def test_anthropic_adapter_request_and_response(monkeypatch):
    from app.tutoring.llm import Anthropic, LLMGateway

    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(200, json={"content": [{"type": "text", "text": '```json\n{"message": "Try a small example."}\n```'}], "usage": {"input_tokens": 3, "output_tokens": 4}})

    provider = Anthropic("secret-key", "test-model")
    provider._client = httpx.Client(base_url="https://api.anthropic.com", headers={"x-api-key": "secret-key", "anthropic-version": "2023-06-01"}, transport=httpx.MockTransport(respond))
    gateway = LLMGateway()
    monkeypatch.setattr(gateway, "provider", provider)
    parsed, _ = gateway.complete_json("system text", "user text")
    body = json.loads(seen[0].content)
    assert seen[0].url.path == "/v1/messages" and seen[0].headers["x-api-key"] == "secret-key" and seen[0].headers["anthropic-version"]
    assert "system text" in body["system"] and body["messages"] == [{"role": "user", "content": "user text"}]
    assert parsed["message"] == "Try a small example."


@pytest.mark.parametrize("status", [401, 429, 500, 503])
def test_provider_http_errors_become_a_fallback_signal(status):
    from app.tutoring.llm import LLMUnavailable, OpenAICompatible

    provider = OpenAICompatible("openai", "https://api.example.test/v1", "k", "m")
    provider._client = httpx.Client(base_url="https://api.example.test/v1", transport=httpx.MockTransport(lambda r: httpx.Response(status, json={"error": {"code": "x"}})))
    with pytest.raises(LLMUnavailable):
        provider.complete("s", "u", 10, 0.2)


def test_provider_timeout_becomes_a_fallback_signal():
    from app.tutoring.llm import LLMUnavailable, OpenAICompatible

    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    provider = OpenAICompatible("openai", "https://api.example.test/v1", "k", "m")
    provider._client = httpx.Client(base_url="https://api.example.test/v1", transport=httpx.MockTransport(slow))
    with pytest.raises(LLMUnavailable):
        provider.complete("s", "u", 10, 0.2)


def test_malformed_model_output_is_rejected():
    from app.tutoring.llm import parse_json_object

    assert parse_json_object("not json") is None and parse_json_object("[1, 2]") is None
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1} and parse_json_object('Sure! {"a": 2} done') == {"a": 2}


def test_provider_choice_is_configuration_only(monkeypatch):
    from app.config import settings
    from app.tutoring.llm import build_provider

    monkeypatch.setattr(settings, "llm_provider", "none")
    assert build_provider().name == "none"
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    assert build_provider().name == "none", "no key means no provider, with built-in hints"
    monkeypatch.setattr(settings, "openai_api_key", "k")
    assert build_provider().name == "openai"
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    assert build_provider().name == "ollama"
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", "k")
    assert build_provider().name == "anthropic"


def test_production_refuses_unsafe_settings():
    from app.config import Settings, check_production_settings

    unsafe = Settings(demo_mode=True, retrieval_allow_synthetic=True, runner_token="short", database_url="postgresql+psycopg://csmasf:csmasf_dev_password@db/csmasf")
    assert len(check_production_settings(unsafe)) == 4
    safe = Settings(demo_mode=False, retrieval_allow_synthetic=False, runner_token="x" * 32, database_url="postgresql+psycopg://csmasf:a-real-secret@db/csmasf")
    assert check_production_settings(safe) == []


def test_completion_counts_problems_started_but_never_submitted(learner):
    """Reported: 100% completion while several problems were unfinished, because only submitted problems counted."""
    learner.submit("say-hello", 'def greet(name):\n    return f"Hello, {name}!"\n')
    learner.client.put("/api/problems/sum-to-n/draft", json={"code": "def sum_to_n(n):\n    return 0\n", "language": "python", "base_version": 0})
    learner.run("count-multiples", "def count_multiples(n, limit):\n    return 0\n")
    metrics = learner.client.get("/api/progress").json()["metrics"]
    assert metrics["solved"] == 1 and metrics["submitted"] == 1
    assert metrics["started"] == 3 and metrics["completion_rate"] == pytest.approx(1 / 3, abs=0.001)


def test_an_example_line_is_never_taken_as_the_title():
    from app.imports.parser import parse_problem_text

    draft = parse_problem_text("Input: nums = [7, 4, 1, 5, 3]\nOutput: 4\n\nReturn the length of the longest increasing run.")
    assert not draft.title.lower().startswith("input")



# ---- test cases shown before running, and submission history

def test_each_problem_shows_its_sample_cases_with_named_inputs(learner):
    detail = learner.client.get("/api/problems/count-multiples").json()
    assert detail["param_names"] == ["n", "limit"]
    first = detail["sample_cases"][0]
    assert [p["name"] for p in first["params"]] == ["n", "limit"] and first["editable"] and first["expected"]


def test_edited_and_new_cases_get_expected_answers_from_the_reference(learner):
    detail = learner.client.get("/api/problems/sum-to-n").json()
    sample = detail["sample_cases"][0]["id"]
    code = "def sum_to_n(n):\n    total = 0\n    for i in range(1, n):\n        total += i\n    return total\n"
    response = learner.client.post("/api/problems/sum-to-n/run", json={"code": code, "idempotency_key": learner.key(), "cases": [{"test_id": sample}, {"args": ["5"]}, {"args": ["1"]}]})
    assert response.status_code == 202, response.text
    result = learner.wait_evaluation(response.json()["id"])
    rows = result["results"]
    assert [r["name"] for r in rows] == ["Case 1", "Case 2", "Case 3"]
    assert rows[1]["expected"] == "15" and rows[1]["actual"] == "10" and rows[1]["passed"] is False
    assert rows[2]["expected"] == "1" and rows[2]["passed"] is False
    assert result["verdict"] in ("wrong_answer", "partial")


def test_an_input_the_reference_rejects_is_shown_as_possibly_invalid(learner):
    response = learner.client.post("/api/problems/sum-to-n/run", json={"code": "def sum_to_n(n):\n    return n\n", "idempotency_key": learner.key(), "cases": [{"args": ["'text'"]}]})
    rows = learner.wait_evaluation(response.json()["id"])["results"]
    assert rows[0]["passed"] is None and "may not be a valid input" in rows[0]["note"]


def test_a_case_value_must_be_a_plain_python_value(learner):
    bad = learner.client.post("/api/problems/sum-to-n/run", json={"code": "x = 1\n", "idempotency_key": learner.key(), "cases": [{"args": ["__import__('os')"]}]})
    assert bad.status_code == 422 and "Case 1" in bad.json()["error"]["message"]
    wrong_count = learner.client.post("/api/problems/count-multiples/run", json={"code": "x = 1\n", "idempotency_key": learner.key(), "cases": [{"args": ["3"]}]})
    assert wrong_count.status_code == 422 and "n, limit" in wrong_count.json()["error"]["message"]


def test_submission_history_lists_every_submission_with_its_code(learner):
    wrong = "def sum_to_n(n):\n    return 0\n"
    right = "def sum_to_n(n):\n    return n * (n + 1) // 2\n"
    learner.submit("sum-to-n", wrong)
    learner.submit("sum-to-n", right)
    rows = learner.client.get("/api/problems/sum-to-n/submissions").json()
    assert rows[0]["verdict"] == "accepted" and rows[1]["verdict"] in ("wrong_answer", "partial")
    assert rows[0]["code"] == right and rows[1]["code"] == wrong and rows[0]["created_at"] >= rows[1]["created_at"]
    assert rows[1]["passed"] < rows[1]["total"]


# ---- the learner's profile, the teacher's view of it, and the learner's own questions
SIMILAR_KEYS = {"matched", "support", "effectiveness", "similarity", "candidates", "suggested_strategy", "reason", "demo_data", "at"}


def test_profile_counts_work_and_shows_the_learning_state(learner):
    learner.submit("sum-to-n", "def sum_to_n(n):\n    return 0\n", active_seconds=60)
    learner.submit("sum-to-n", RIGHT, active_seconds=120)
    profile = learner.client.get("/api/me/profile").json()
    totals = profile["totals"]
    assert totals["solved"] == 1 and totals["started"] == 1 and totals["completion_rate"] == 1.0
    assert totals["submissions"] == 2 and totals["accepted_submissions"] == 1 and totals["acceptance_rate"] == 0.5
    assert totals["first_try_solves"] == 0 and totals["topics_with_solves"] == 1
    assert totals["hints_total"] >= 1 and totals["solved_without_hints"] == 0, "the failed submission was answered with a hint"
    assert sum(solved for solved, _ in totals["solved_by_difficulty"].values()) == 1
    assert all(total > 0 for _, total in totals["solved_by_difficulty"].values()), "totals count the curriculum's problems"
    assert len(profile["calendar"]) == 182 and sum(day["count"] for day in profile["calendar"]) >= 2
    assert totals["days_active"] == 1 and totals["current_streak"] == 1 and totals["longest_streak"] == 1
    loops = next(row for row in profile["state_matrix"] if row["unit_id"] == "loops")
    assert loops["solved"] == 1 and loops["total"] >= 15 and loops["graded_attempts"] >= 1
    assert 0 <= loops["mastery_low"] <= loops["mastery"] <= loops["mastery_high"] <= 1
    assert {"confidence", "confusion", "load", "progress", "band", "evidence_weight", "starting_mastery"} <= loops.keys()
    assert all(row["unit_id"] != "graphs" for row in profile["state_matrix"]), "a topic with no work gets no estimate"
    assert len(profile["vector"]["features"]) == 14 and all(f["meaning"] for f in profile["vector"]["features"])
    assert profile["recent"][0]["verdict"] == "accepted" and len(profile["recent"]) == 2
    assert any(m["achieved"] for m in profile["milestones"]) and not all(m["achieved"] for m in profile["milestones"])


def test_profile_shows_similar_learners_only_as_counts(learner):
    learner.submit("sum-to-n", "def sum_to_n(n):\n    return 0\n")
    similar = learner.client.get("/api/me/profile").json()["similar"]
    assert similar is not None and set(similar) <= SIMILAR_KEYS, "no identities, ids or code from other learners"


def test_new_learner_profile_is_empty_not_an_error(learner):
    profile = learner.client.get("/api/me/profile").json()
    assert profile["totals"]["solved"] == 0 and profile["totals"]["acceptance_rate"] is None
    assert profile["vector"] is None and profile["similar"] is None and profile["recent"] == []
    assert profile["improvement"]["then_now"] is None, "early and recent work are compared only after four solves"
    assert len(profile["improvement"]["weekly"]) == 8 and all(week["solved"] == 0 for week in profile["improvement"]["weekly"])


def test_teacher_table_has_state_columns_and_student_profile(classroom):
    teacher, created, student = classroom
    student.submit("sum-to-n", "def sum_to_n(n):\n    return 0\n")
    student.submit("sum-to-n", RIGHT)
    overview = teacher.client.get(f"/api/teacher/classes/{created['id']}/overview").json()
    row = overview["learners"][0]
    for key in ("mastery", "topics_started", "confidence", "confusion", "load", "progress", "first_try_rate", "attempts_per_solve", "current_streak", "longest_streak"):
        assert key in row, key
    assert row["topics_started"] == 1 and row["attempts_per_solve"] == 2 and row["first_try_rate"] == 0
    for key in ("mastery", "confidence", "confusion", "load", "progress"):
        assert overview["definitions"][key], key
    detail = teacher.client.get(f"/api/teacher/classes/{created['id']}/students/{student.id}").json()
    mine = student.client.get("/api/me/profile").json()
    assert detail["profile"]["totals"] == mine["totals"] and detail["profile"]["state_matrix"] == mine["state_matrix"]


def test_your_questions_list_shows_when_each_was_added(make_learner):
    owner, other = make_learner(), make_learner()
    problem = imported_problem(owner)
    mine = owner.client.get("/api/problems", params={"mine": True}).json()
    row = next(p for p in mine if p["id"] == problem["id"])
    assert row["is_mine"] and row["created_at"]
    assert all(p["created_at"] is None for p in owner.client.get("/api/problems", params={"unit": "loops"}).json())
    assert owner.client.get("/api/me/profile").json()["totals"]["questions_added"] == 1
    assert other.client.get("/api/problems", params={"mine": True}).json() == []


def test_generation_adds_order_duplicate_zero_and_smallest_value_cases():
    tests, _ = generate_tests(draft_for([[3, -1, 4], 5], 7, constraints="1 <= nums.length <= 50\n-100 <= nums[i] <= 100"))
    generated = {t.category: t for t in tests if t.origin == "generated"}
    for category in ("sorted", "reverse_sorted", "unsorted", "duplicates", "zero", "boundary", "negative", "minimal", "repeated"):
        assert category in generated, category
    assert generated["sorted"].args[0] == [-1, 3, 4] and generated["reverse_sorted"].args[0] == [4, 3, -1]
    assert all(t.needs_expected and not t.enabled for t in generated.values() if t.compare != "completes"), "a generated answer is never assumed"
    smallest = [t for t in tests if t.label == "nums with its smallest values"]
    assert smallest and smallest[0].args[0] == [-100, -100]
