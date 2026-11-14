"""The curriculum: its structure, its lessons, and a sample checked in the real sandbox.

`scripts/verify_content.py` checks every problem in the sandbox, and takes several minutes.
"""
import uuid

from sqlalchemy import select

from app.db import session_scope
from app.grading import grade
from app.models import Problem, ProblemSolution, Unit
from app.runner_client import runner
from app.seed import PLAYGROUND_ID


def _job(problem, code):
    tests = [{"id": t.id, "kind": t.kind, "args": (t.payload or {}).get("args", []), "setup": (t.payload or {}).get("setup"), "expr": (t.payload or {}).get("expr"), "stdin": (t.payload or {}).get("stdin")} for t in problem.tests]
    return {"job_id": uuid.uuid4().hex, "code": code, "prelude": problem.prelude, "function_name": problem.function_name, "tests": tests, "limits": {"per_test_seconds": 3, "total_seconds": 25, "memory_mb": 192, "output_kb": 64}}


def _problems(db):
    return db.scalars(select(Problem).where(Problem.owner_id.is_(None), Problem.archived.is_(False)).order_by(Problem.order_index)).all()


def test_reference_solutions_pass_and_starters_do_not_on_a_sample(app_ready):
    wrong, starter_passing = [], []
    with session_scope() as db:
        problems = _problems(db)
        for problem in problems[::9]:
            solution = db.get(ProblemSolution, problem.id)
            assert solution, f"{problem.id} has no reference solution"
            result = runner.execute(_job(problem, solution.code))
            assert result.status == "completed", result.message
            if grade(list(problem.tests), result.results, problem.function_name).verdict != "accepted":
                wrong.append(problem.id)
            start = runner.execute(_job(problem, problem.starter_code))
            if grade(list(problem.tests), start.results, problem.function_name).verdict == "accepted":
                starter_passing.append(problem.id)
    assert wrong == [] and starter_passing == []


def test_there_are_450_to_600_problems_and_at_least_15_in_every_topic(app_ready):
    with session_scope() as db:
        problems = _problems(db)
        units = db.scalars(select(Unit)).all()
        assert 450 <= len(problems) <= 600, len(problems)
        for unit in units:
            count = sum(1 for p in problems if p.unit_id == unit.id)
            assert count >= 15, f"{unit.id} has only {count} problems"
        assert all(db.get(ProblemSolution, p.id) for p in problems), "every problem has a reference solution"
        titles = [p.title.lower() for p in problems]
        assert len(titles) == len(set(titles)), "titles do not repeat"


def test_curriculum_structure(app_ready):
    with session_scope() as db:
        units = {u.id: u for u in db.scalars(select(Unit)).all()}
        problems = _problems(db)
        for unit in units.values():
            assert all(p in units for p in unit.prerequisites), unit.id
            assert unit.lessons, f"{unit.id} has no lessons"
        for problem in problems:
            assert any(t.visibility == "public" for t in problem.tests), f"{problem.id} has no public example"
            assert any(t.visibility == "hidden" for t in problem.tests) or len(problem.tests) <= 2, f"{problem.id} has no further tests"
            assert problem.difficulty in ("easy", "medium", "hard")
        assert sum(1 for p in problems if p.recommended_first) == 1


def test_every_topic_has_a_detailed_lesson(app_ready):
    with session_scope() as db:
        for unit in db.scalars(select(Unit)).all():
            guide = unit.guide
            assert guide, f"{unit.id} has no lesson"
            for key in ("overview", "you_will_learn", "before_you_start", "sections", "patterns", "mistakes", "key_ideas", "reading_minutes"):
                assert guide.get(key), f"{unit.id} lesson has no {key}"
            words = sum(len(section["body"].split()) for section in guide["sections"]) + sum(len(p["how"].split()) + len(p["when"].split()) for p in guide["patterns"])
            assert words >= 200, f"{unit.id} lesson has only {words} words"
            assert len(guide["sections"]) >= 3, unit.id
            examples = [e for section in guide["sections"] for e in section.get("examples", [])]
            assert len(examples) >= 3, f"{unit.id} has too few examples"
            ids = [section["id"] for section in guide["sections"]]
            assert len(ids) == len(set(ids)), f"{unit.id} repeats a section id"


def test_every_problem_belongs_to_a_pattern_taught_in_its_topic(app_ready):
    with session_scope() as db:
        taught = {u.id: {p["name"] for p in u.guide["patterns"]} for u in db.scalars(select(Unit)).all()}
        for problem in _problems(db):
            assert problem.pattern, f"{problem.id} has no pattern"
            assert problem.pattern in taught[problem.unit_id], f"{problem.id}: {problem.pattern!r} is not taught in {problem.unit_id}"


def test_every_lesson_example_runs_and_prints_something(app_ready):
    with session_scope() as db:
        examples = [(unit.id, example) for unit in db.scalars(select(Unit)).all() for section in unit.guide["sections"] for example in section.get("examples", [])]
    failures = []
    for unit_id, example in examples:
        job = {"job_id": uuid.uuid4().hex, "code": example["code"], "prelude": None, "function_name": None, "tests": [{"id": "t", "kind": "stdio", "stdin": ""}], "limits": {"per_test_seconds": 3, "total_seconds": 10, "memory_mb": 192, "output_kb": 64}}
        result = runner.execute(job)
        assert result.status == "completed", result.message
        outcome = result.results[0]
        if outcome.get("status") != "ok" or not outcome.get("stdout", "").strip():
            failures.append((unit_id, example.get("title"), outcome.get("status"), outcome.get("error")))
    assert failures == []


def test_scratch_space_runs_code_and_stays_hidden(learner):
    response = learner.client.post("/api/playground/run", json={"code": "print(6 * 7)", "idempotency_key": learner.key()})
    assert response.status_code == 202
    evaluation = learner.wait_evaluation(response.json()["id"])
    assert evaluation["kind"] == "run" and "42" in evaluation["results"][0]["stdout"]
    listed = [p["id"] for p in learner.client.get("/api/problems").json()]
    assert PLAYGROUND_ID not in listed
    assert learner.client.get(f"/api/problems/{PLAYGROUND_ID}").status_code == 404
    assert learner.client.get("/api/progress").json()["metrics"]["graded_attempts"] == 0


def test_lessons_and_pattern_reach_the_client_but_solutions_do_not(learner):
    unit = learner.client.get("/api/units/loops").json()
    assert unit["guide"]["sections"] and all("pattern" in p for p in unit["problems"])
    detail = learner.client.get("/api/problems/sum-to-n").json()
    assert detail["pattern"] == "Running totals" and detail["topic_notes"]["pattern"]["name"] == "Running totals"
    assert "total += i" not in str(unit["problems"]) and "total += i" not in str(detail.get("topic_notes"))
    assert "solution" not in detail


def test_prerequisites_form_no_cycle(app_ready):
    with session_scope() as db:
        graph = {u.id: list(u.prerequisites or []) for u in db.scalars(select(Unit)).all()}
    done, visiting = set(), set()

    def visit(node):
        assert node not in visiting, f"cycle through {node}"
        if node in done:
            return
        visiting.add(node)
        for parent in graph[node]:
            visit(parent)
        visiting.discard(node)
        done.add(node)

    for node in graph:
        visit(node)


def test_every_topic_has_detailed_notes_and_every_technique_has_guidance():
    from app.learning import DEFAULT_TECHNIQUE, techniques
    from app.seed import load_guides

    library = techniques()
    assert DEFAULT_TECHNIQUE in library
    for unit_id, guide in load_guides().items():
        for field in ("why", "definitions", "how_it_works", "diagram", "edge_cases", "when_to_use", "related", "summary", "glossary", "checks"):
            assert guide.get(field), (unit_id, field)
        for pattern in guide["patterns"]:
            entry = library.get(pattern["name"])
            assert entry, (unit_id, pattern["name"])
            assert entry["idea"] and entry["steps"] and entry["approaches"] and entry["mistakes"] and entry["edge_cases"], pattern["name"]


def test_every_problem_gets_a_learn_panel_that_reveals_no_hidden_test(learner):
    from sqlalchemy import select

    from app.db import session_scope
    from app.grading import display
    from app.models import Problem

    with session_scope() as db:
        rows = [(p.id, [display(t.expected) for t in p.tests if t.visibility == "hidden"]) for p in db.scalars(select(Problem).where(Problem.archived.is_(False), Problem.owner_id.is_(None))).all()]
    assert len(rows) >= 300
    for problem_id, hidden in rows:
        response = learner.client.get(f"/api/problems/{problem_id}/learn")
        assert response.status_code == 200, problem_id
        panel = response.json()
        assert panel["summary"] and panel["asking"] and panel["approaches"] and panel["mistakes"] and panel["edge_cases"] and panel["worked_example"], problem_id
        assert "def " not in str(panel["approaches"]), "guidance is in words, never code"
        worked = str(panel["worked_example"])
        for value in hidden:
            if len(value) >= 6 and value not in worked:
                assert value not in str(panel["shape"]), (problem_id, value)


def test_search_finds_topics_lessons_glossary_and_problems(learner):
    found = learner.client.get("/api/search", params={"q": "time complexity"}).json()
    assert any(hit["id"] == "searching-sorting" for hit in found["topics"])
    assert learner.client.get("/api/search", params={"q": "palindrome"}).json()["problems"]
    assert learner.client.get("/api/search", params={"q": "zzzzzz"}).json() == {"topics": [], "problems": []}


def test_most_problems_have_many_tests_and_generated_ones_stay_hidden():
    from sqlalchemy import select

    from app.db import session_scope
    from app.models import Problem

    with session_scope() as db:
        problems = db.scalars(select(Problem).where(Problem.archived.is_(False), Problem.owner_id.is_(None))).all()
        counts = [len([t for t in p.tests if t.enabled]) for p in problems]
        public = [sum(1 for t in p.tests if t.enabled and t.visibility == "public") for p in problems]
    assert sum(1 for c in counts if c >= 10) >= 480, "all but a few problems with very few possible inputs have at least ten tests"
    assert sum(1 for c in counts if c >= 12) >= 460, "most problems have twelve tests"
    assert max(public) <= 3, "generated tests are hidden, so the examples stay as written"

