"""Application services for Run, Submit and Hint.

Event semantics are kept distinct:
- Run   executes public examples or the learner's own input. Never graded, never starts the agents.
- Submit evaluates against all assessment tests, counts as a graded attempt, and starts a learning cycle.
- Hint  starts a learning cycle from a public-example probe. Never graded, never changes mastery.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import session_scope
from ..errors import ApiError
from ..grading import describe_input, display, grade
from ..models import CodeSnapshot, Evaluation, PipelineRun, Problem, ProblemSolution, ProblemTest, User
from ..runner_client import runner as default_runner

log = logging.getLogger("csmasf.service")

executor = ThreadPoolExecutor(max_workers=settings.pipeline_workers, thread_name_prefix="pipeline")
_compiled_graph = None
_graph_lock = threading.Lock()
_pool = None
runner = default_runner


def get_graph():
    """Compiled graph with a PostgreSQL checkpointer, created once."""
    global _compiled_graph, _pool
    with _graph_lock:
        if _compiled_graph is None:
            from langgraph.checkpoint.postgres import PostgresSaver
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool

            from .graph import build_graph

            _pool = ConnectionPool(
                settings.psycopg_url, min_size=1, max_size=settings.pipeline_workers + 2, open=True,
                kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0},
            )
            saver = PostgresSaver(_pool)
            saver.setup()
            _compiled_graph = build_graph(checkpointer=saver)
        return _compiled_graph


class _UserQueue:
    """FIFO per learner: results and state updates always apply in the order actions were made."""

    def __init__(self) -> None:
        self._waiting: dict[str, deque[str]] = defaultdict(deque)
        self._cv = threading.Condition()

    def enqueue(self, user_id: str, ticket: str) -> None:
        with self._cv:
            self._waiting[user_id].append(ticket)

    def wait_turn(self, user_id: str, ticket: str) -> None:
        with self._cv:
            self._cv.wait_for(lambda: self._waiting[user_id] and self._waiting[user_id][0] == ticket)

    def done(self, user_id: str, ticket: str) -> None:
        with self._cv:
            if self._waiting[user_id] and self._waiting[user_id][0] == ticket:
                self._waiting[user_id].popleft()
            if not self._waiting[user_id]:
                del self._waiting[user_id]
            self._cv.notify_all()


user_queue = _UserQueue()


def code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def get_or_create_snapshot(db: Session, user_id: str, problem_id: str, code: str) -> CodeSnapshot:
    digest = code_hash(code)
    query = select(CodeSnapshot).where(CodeSnapshot.user_id == user_id, CodeSnapshot.problem_id == problem_id, CodeSnapshot.code_hash == digest)
    existing = db.scalar(query)
    if existing:
        return existing
    snapshot = CodeSnapshot(user_id=user_id, problem_id=problem_id, code=code, code_hash=digest)
    db.add(snapshot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return db.scalar(query)
    return snapshot


def _tests_for(db: Session, problem: Problem, kind: str) -> list[ProblemTest]:
    tests = [t for t in problem.tests if t.enabled and not t.needs_expected]
    if kind in ("run", "hint_probe"):
        return [t for t in tests if t.visibility == "public"]
    return tests


def _job_test(test: ProblemTest) -> dict[str, Any]:
    payload = test.payload or {}
    return {
        "id": test.id, "kind": test.kind, "args": payload.get("args", []), "kwargs": payload.get("kwargs", {}),
        "setup": payload.get("setup"), "expr": payload.get("expr"), "stdin": payload.get("stdin"),
    }


def _output_only_row(test: dict[str, Any], outcome: dict[str, Any], name: str, shown_input: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": test["id"], "name": name, "visibility": "public", "passed": None, "category": "output_only", "origin": "learner",
        "input": shown_input, "expected": None, "stdout": (outcome.get("stdout") or "")[:4000], "stderr": (outcome.get("stderr") or "")[:2000],
        "truncated": bool(outcome.get("truncated")), "duration_ms": outcome.get("duration_ms", 0),
        "status": outcome.get("status"),
        "actual": display(outcome.get("value")) if outcome.get("status") == "ok" and test["kind"] != "stdio" else None,
    }
    error = outcome.get("error")
    if error:
        row["error"] = {"type": error.get("type"), "message": error.get("message"), "line": error.get("line"), "column": error.get("column")}
    return row


def _verdict_from_status(status: str | None) -> str:
    return {"ok": "ran", "syntax_error": "syntax_error", "exception": "runtime_error", "timeout": "timeout", "memory_limit": "memory_limit", "output_limit": "output_limit",
            "missing_function": "missing_function"}.get(status or "", "runtime_error")


def run_evaluation(evaluation_id: str) -> dict[str, Any]:
    """Execute one evaluation. Returns a compact summary; details stay in the database row."""
    with session_scope() as db:
        evaluation = db.get(Evaluation, evaluation_id)
        if evaluation.status in ("completed", "failed", "cancelled"):
            return {"id": evaluation.id, "verdict": evaluation.verdict, "passed": evaluation.passed, "total": evaluation.total, "kind": evaluation.kind, "backend": evaluation.runner_backend, "reused": True}
        if evaluation.status == "cancelling":
            evaluation.status, evaluation.verdict = "cancelled", "cancelled"
            evaluation.finished_at = datetime.now(UTC)
            return {"id": evaluation.id, "verdict": "cancelled", "passed": 0, "total": 0, "kind": evaluation.kind, "backend": None}
        evaluation.status = "running"
        problem = db.get(Problem, evaluation.problem_id)
        snapshot = db.get(CodeSnapshot, evaluation.snapshot_id)
        tests = _tests_for(db, problem, evaluation.kind)
        for test in tests:
            db.expunge(test)
        function_name, prelude, per_test = problem.function_name, problem.prelude, problem.per_test_seconds
        code, kind, custom = snapshot.code, evaluation.kind, evaluation.custom_input
        mode = problem.mode

    if custom and custom.get("cases"):
        return _run_cases(evaluation_id, tests, custom["cases"], code, function_name, prelude, per_test)

    extra: list[tuple[dict[str, Any], str, str]] = []
    if custom:
        if custom.get("stdin") is not None:
            extra.append(({"id": "custom", "kind": "stdio", "stdin": custom["stdin"]}, "Your input", custom["stdin"] or "(no input)"))
        elif custom.get("args") is not None:
            args = custom["args"]
            shown = f"{function_name or 'solution'}({', '.join(display(a, 200) for a in args)})"
            extra.append(({"id": "custom", "kind": "args", "args": args}, "Your input", shown))
    if not tests and not extra and kind != "submit":
        # Nothing public to compare against: still run the file, so the learner sees errors and output.
        extra.append(({"id": "script", "kind": "stdio", "stdin": ""}, "Your program", "(no input)"))

    job_tests = [_job_test(t) for t in tests] + [e[0] for e in extra]
    if not job_tests:
        return _finish(evaluation_id, "no_tests", 0, 0, [], [], None, None, None, 0)

    limits = {"per_test_seconds": per_test, "total_seconds": min(25.0, max(8.0, per_test * len(job_tests))), "memory_mb": 192, "output_kb": 64}
    job = {"job_id": evaluation_id, "language": "python", "code": code, "prelude": prelude, "function_name": function_name, "tests": job_tests, "limits": limits}
    _ = mode
    result = runner.execute(job)

    if result.status == "cancelled":
        return _finish(evaluation_id, "cancelled", 0, 0, [], [], None, result.backend, result.secure, result.duration_ms)
    if result.status != "completed":
        message = "The execution service is busy. Please try again." if result.status == "busy" else "The execution service is unavailable."
        return _finish(evaluation_id, "service_failure", 0, 0, [], [], message, result.backend, result.secure, result.duration_ms)

    outcomes = {o["id"]: o for o in result.results}
    graded = grade(tests, [outcomes[t.id] for t in tests if t.id in outcomes], function_name)
    public = list(graded.public_results)
    internal = list(graded.internal_results)
    verdict = graded.verdict
    for test, name, shown in extra:
        outcome = outcomes.get(test["id"], {"status": "invalid_result"})
        public.append(_output_only_row(test, outcome, name, shown))
        internal.append({
            "test_id": test["id"], "visibility": "public", "passed": True, "category": "output_only", "status": outcome.get("status"), "value": outcome.get("value"), "expected": None,
            "stdout": (outcome.get("stdout") or "")[:4000], "error": outcome.get("error"), "kind": test["kind"], "input": shown, "origin": "learner", "compare": "output_only", "duration_ms": outcome.get("duration_ms", 0),
        })
        if not tests:
            verdict = _verdict_from_status(outcome.get("status"))
        elif outcome.get("status") == "syntax_error":
            verdict = "syntax_error"
    if kind != "submit" and verdict == "accepted":
        verdict = "public_passed"
    return _finish(evaluation_id, verdict, graded.passed, graded.total, public, internal, None, result.backend, result.secure, result.duration_ms)


def _run_cases(evaluation_id: str, public_tests: list[ProblemTest], cases: list[dict[str, Any]], code: str, function_name: str | None, prelude: str | None, per_test: float) -> dict[str, Any]:
    """Run the cases the learner chose before running: examples, edited ones and new ones.

    An edited or new case has no stored answer, so the reference solution is run on the same input in the same sandbox,
    and its answer becomes the expected value. The reference code itself never leaves the server.
    """
    by_id = {t.id: t for t in public_tests}
    with session_scope() as db:
        evaluation = db.get(Evaluation, evaluation_id)
        reference = db.get(ProblemSolution, evaluation.problem_id)
        reference_code = reference.code if reference else None
    picked: list[tuple[int, ProblemTest | None, dict[str, Any] | None]] = []
    for number, case in enumerate(cases, start=1):
        if case.get("test_id") and case["test_id"] in by_id:
            picked.append((number, by_id[case["test_id"]], None))
        elif "args" in case:
            picked.append((number, None, {"id": f"case-{number}", "kind": "args", "args": case["args"]}))
        else:
            picked.append((number, None, {"id": f"case-{number}", "kind": "stdio", "stdin": case.get("stdin", "")}))
    custom_specs = [spec for _, _, spec in picked if spec]
    job_tests = [_job_test(test) for _, test, _ in picked if test] + custom_specs
    limits = {"per_test_seconds": per_test, "total_seconds": min(25.0, max(8.0, per_test * len(job_tests))), "memory_mb": 192, "output_kb": 64}
    result = runner.execute({"job_id": evaluation_id, "language": "python", "code": code, "prelude": prelude, "function_name": function_name, "tests": job_tests, "limits": limits})
    if result.status == "cancelled":
        return _finish(evaluation_id, "cancelled", 0, 0, [], [], None, result.backend, result.secure, result.duration_ms)
    if result.status != "completed":
        message = "The execution service is busy. Please try again." if result.status == "busy" else "The execution service is unavailable."
        return _finish(evaluation_id, "service_failure", 0, 0, [], [], message, result.backend, result.secure, result.duration_ms)
    outcomes = {o["id"]: o for o in result.results}
    expected: dict[str, dict[str, Any]] = {}
    if custom_specs and reference_code:
        ref_limits = {**limits, "total_seconds": min(25.0, max(8.0, per_test * len(custom_specs)))}
        ref = runner.execute({"job_id": f"{evaluation_id[:24]}-ref", "language": "python", "code": reference_code, "prelude": prelude, "function_name": function_name, "tests": custom_specs, "limits": ref_limits})
        if ref.status == "completed":
            expected = {o["id"]: o for o in ref.results}

    # Each case becomes a temporary test, so the usual grading and wording apply to it.
    graded_tests: list[ProblemTest] = []
    unknown: list[tuple[int, dict[str, Any], str]] = []
    for number, test, spec in picked:
        if test is not None:
            graded_tests.append(ProblemTest(id=test.id, problem_id=test.problem_id, kind=test.kind, payload=test.payload, expected=test.expected, compare=test.compare, visibility="public", origin="curriculum", label=f"Case {number}"))
            continue
        answer = expected.get(spec["id"])
        if answer and answer.get("status") == "ok":
            value = answer.get("stdout", "") if spec["kind"] == "stdio" else answer.get("value")
            payload = {"stdin": spec["stdin"]} if spec["kind"] == "stdio" else {"args": spec["args"]}
            graded_tests.append(ProblemTest(id=spec["id"], problem_id="", kind=spec["kind"], payload=payload, expected=value, compare="exact", visibility="public", origin="learner", label=f"Case {number}"))
        else:
            reason = "The reference solution could not run on this input either, so it may not be a valid input for this problem." if answer else "There is no stored answer for this input, so only your output is shown."
            unknown.append((number, spec, reason))
    graded = grade(graded_tests, [outcomes[t.id] for t in graded_tests if t.id in outcomes], function_name)
    order = {t.id: index for index, t in enumerate(graded_tests)}
    public = sorted(graded.public_results, key=lambda row: order.get(row["id"], 0))
    internal = list(graded.internal_results)
    for number, spec, reason in unknown:
        outcome = outcomes.get(spec["id"], {"status": "invalid_result"})
        shown = spec["stdin"] or "(no input)" if spec["kind"] == "stdio" else f"{function_name or 'solution'}({', '.join(display(a, 200) for a in spec['args'])})"
        row = _output_only_row(spec, outcome, f"Case {number}", shown)
        row["note"] = reason
        public.append(row)
    public.sort(key=lambda row: int(str(row.get("name", "Case 0")).split()[-1]) if str(row.get("name", "")).startswith("Case ") else 0)
    verdict = graded.verdict if graded_tests else _verdict_from_status(next((outcomes.get(spec["id"], {}).get("status") for _, spec, _ in unknown), None))
    if any(outcomes.get(spec["id"], {}).get("status") == "syntax_error" for _, spec, _ in unknown):
        verdict = "syntax_error"
    if verdict == "accepted":
        verdict = "public_passed"
    return _finish(evaluation_id, verdict, graded.passed, graded.total, public, internal, None, result.backend, result.secure, result.duration_ms)


def _finish(evaluation_id: str, verdict: str, passed: int, total: int, public: list, internal: list, message: str | None, backend: str | None, secure: bool | None, duration: int) -> dict[str, Any]:
    with session_scope() as db:
        evaluation = db.get(Evaluation, evaluation_id)
        evaluation.verdict, evaluation.passed, evaluation.total = verdict, passed, total
        evaluation.public_results, evaluation.internal_results, evaluation.message = public, internal, message
        evaluation.runner_backend, evaluation.runner_secure, evaluation.duration_ms = backend, secure, duration
        evaluation.status = "cancelled" if verdict == "cancelled" else ("failed" if verdict == "service_failure" else "completed")
        evaluation.finished_at = datetime.now(UTC)
        return {"id": evaluation.id, "verdict": verdict, "passed": passed, "total": total, "kind": evaluation.kind, "backend": backend}


def trace_lines(problem_id: str, code: str, test_id: str, lines: list[int]) -> list[dict[str, Any]] | None:
    """What the variables held on these lines, for one visible example. Explains code, and is never used to grade.

    None means no trace is available, for example with an older execution service.
    """
    with session_scope() as db:
        problem = db.get(Problem, problem_id)
        test = db.get(ProblemTest, test_id)
        if problem is None or test is None or test.visibility != "public":
            return None
        spec = {**_job_test(test), "trace_lines": lines[:30]}
        prelude, function_name, per_test = problem.prelude, problem.function_name, problem.per_test_seconds
    job = {"job_id": uuid.uuid4().hex, "language": "python", "code": code, "prelude": prelude, "function_name": function_name, "tests": [spec],
           "limits": {"per_test_seconds": min(per_test, 3.0), "total_seconds": 6.0, "memory_mb": 192, "output_kb": 64}}
    result = runner.execute(job)
    if result.status != "completed" or not result.results:
        return None
    return result.results[0].get("trace")


def _existing_evaluation(db: Session, user_id: str, key: str) -> Evaluation | None:
    return db.scalar(select(Evaluation).where(Evaluation.user_id == user_id, Evaluation.idempotency_key == key))


def _existing_run(db: Session, user_id: str, key: str) -> PipelineRun | None:
    return db.scalar(select(PipelineRun).where(PipelineRun.user_id == user_id, PipelineRun.idempotency_key == key))


def _validate_code(code: str) -> None:
    if len(code) > settings.max_code_chars:
        raise ApiError(413, "code_too_long", f"Your code is longer than the {settings.max_code_chars} character limit. Your work is safe in the editor.")


def create_run_evaluation(db: Session, user: User, problem: Problem, code: str, key: str, custom: dict[str, Any] | None) -> tuple[Evaluation, bool]:
    _validate_code(code)
    existing = _existing_evaluation(db, user.id, key)
    if existing:
        return existing, False
    snapshot = get_or_create_snapshot(db, user.id, problem.id, code)
    evaluation = Evaluation(user_id=user.id, problem_id=problem.id, snapshot_id=snapshot.id, kind="run", idempotency_key=key, custom_input=custom)
    db.add(evaluation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _existing_evaluation(db, user.id, key), False
    return evaluation, True


def schedule_evaluation(evaluation: Evaluation) -> None:
    user_id, evaluation_id = evaluation.user_id, evaluation.id
    ticket = uuid.uuid4().hex
    user_queue.enqueue(user_id, ticket)

    def task() -> None:
        try:
            user_queue.wait_turn(user_id, ticket)
            run_evaluation(evaluation_id)
        except Exception:  # noqa: BLE001
            log.exception("evaluation %s failed", evaluation_id)
            _finish(evaluation_id, "service_failure", 0, 0, [], [], "The check could not be completed.", None, None, 0)
        finally:
            user_queue.done(user_id, ticket)

    executor.submit(task)


def create_learning_run(db: Session, user: User, problem: Problem, code: str, key: str, trigger: str, request: dict[str, Any], active_seconds: int | None) -> tuple[PipelineRun, bool]:
    """Create the records for a Submit or Hint. Idempotent, so a double click cannot create two attempts."""
    _validate_code(code)
    existing = _existing_run(db, user.id, key)
    if existing:
        return existing, False
    snapshot = get_or_create_snapshot(db, user.id, problem.id, code)
    if trigger == "submission":
        # The same code, already being checked, is the same attempt.
        active = db.scalar(select(PipelineRun).where(PipelineRun.user_id == user.id, PipelineRun.problem_id == problem.id, PipelineRun.snapshot_id == snapshot.id, PipelineRun.trigger == "submission", PipelineRun.status.in_(["queued", "running"])))
        if active:
            return active, False
        kind = "submit"
    else:
        kind = "hint_probe"
    evaluation = None
    if trigger == "hint_request":
        # Reuse evidence already gathered for this exact code rather than running it again.
        evaluation = db.scalar(
            select(Evaluation).where(Evaluation.user_id == user.id, Evaluation.problem_id == problem.id, Evaluation.snapshot_id == snapshot.id, Evaluation.status == "completed",
                                     Evaluation.kind.in_(["submit", "hint_probe"]), Evaluation.verdict.notin_(["service_failure", "cancelled"]),
                                     # Results from before the question's tests were edited are stale.
                                     Evaluation.created_at >= problem.updated_at).order_by(Evaluation.created_at.desc()).limit(1)
        )
    try:
        if evaluation is None:
            evaluation = Evaluation(user_id=user.id, problem_id=problem.id, snapshot_id=snapshot.id, kind=kind, idempotency_key=key, active_seconds=active_seconds)
            db.add(evaluation)
            db.flush()
        run = PipelineRun(
            user_id=user.id, problem_id=problem.id, evaluation_id=evaluation.id, snapshot_id=snapshot.id, trigger=trigger, idempotency_key=key, correlation_id=uuid.uuid4().hex,
            thread_id=f"{user.id}:{problem.id}:{user.thread_epoch}", request=request,
        )
        db.add(run)
        db.commit()
    except IntegrityError:
        # A simultaneous request with this key won the race, so this is the same attempt.
        db.rollback()
        return _existing_run(db, user.id, key), False
    return run, True


def schedule_run(run: PipelineRun) -> None:
    run_id, user_id = run.id, run.user_id
    ticket = uuid.uuid4().hex
    user_queue.enqueue(user_id, ticket)

    def task() -> None:
        try:
            user_queue.wait_turn(user_id, ticket)
            execute_run(run_id)
        finally:
            user_queue.done(user_id, ticket)

    executor.submit(task)


def execute_run(run_id: str) -> None:
    with session_scope() as db:
        run = db.get(PipelineRun, run_id)
        run.status = "running"
        event = {
            "run_id": run.id, "user_id": run.user_id, "problem_id": run.problem_id, "evaluation_id": run.evaluation_id, "snapshot_id": run.snapshot_id,
            "trigger": run.trigger, "correlation_id": run.correlation_id, **(run.request or {}),
        }
        thread_id = run.thread_id
    try:
        _invoke_graph(event, thread_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("run %s failed (correlation %s)", run_id, event["correlation_id"])
        _fail_run(run_id, f"{type(exc).__name__}: {str(exc)[:300]}")
        return
    with session_scope() as db:
        run = db.get(PipelineRun, run_id)
        if run.status != "completed":
            run.status, run.error = "failed", "The pipeline ended before finishing."
            run.finished_at = datetime.now(UTC)


def _invoke_graph(event: dict[str, Any], thread_id: str) -> None:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 60}
    snapshot = graph.get_state(config)
    if snapshot.next == ("await_learner",):
        graph.invoke(Command(resume=event), config)
    elif not snapshot.values:
        graph.invoke({"event": event, "cycle": 0, "cycle_log": []}, config)
    else:
        # The server stopped part-way through an earlier cycle. Start a fresh thread rather than resume half a turn.
        with session_scope() as db:
            user = db.get(User, event["user_id"])
            user.thread_epoch += 1
            run = db.get(PipelineRun, event["run_id"])
            run.thread_id = f"{user.id}:{run.problem_id}:{user.thread_epoch}"
            config = {"configurable": {"thread_id": run.thread_id}, "recursion_limit": 60}
        graph.invoke({"event": event, "cycle": 0, "cycle_log": []}, config)


def _fail_run(run_id: str, error: str) -> None:
    with session_scope() as db:
        run = db.get(PipelineRun, run_id)
        run.status, run.error = "failed", error
        run.finished_at = datetime.now(UTC)
        evaluation = db.get(Evaluation, run.evaluation_id) if run.evaluation_id else None
        verdict = evaluation.verdict if evaluation else None
        from .compose import VERDICT_TITLES

        run.response = {
            "verdict": verdict or "service_failure",
            "what_happened": {
                "title": VERDICT_TITLES.get(verdict or "", "The tutor had a problem"),
                "detail": "Your code was checked, but the tutor could not finish its response. Your work is safe." if verdict else "This is a problem on our side, not with your code. Your work is safe.",
            },
            "next_action": {"kind": "retry", "label": "Try again", "detail": "", "problem_id": None},
            "tutor": None, "offer": None, "diagnostics": {"category": "service_failure", "issue_key": "pipeline_failure", "facts": [], "possible_causes": [], "lines": [], "uncertain": False},
            "reflection": None, "plan": None, "estimates": None, "retrieval_used": False, "retrieval_demo_data": False, "snapshot_id": run.snapshot_id, "graded": False,
        }


def cancel_evaluation(db: Session, evaluation: Evaluation) -> None:
    if evaluation.status in ("queued", "running"):
        queued = evaluation.status == "queued"
        evaluation.status = "cancelling" if queued else evaluation.status
        db.commit()
        if not queued:
            runner.cancel(evaluation.id)


def recover_interrupted() -> int:
    """After a restart, nothing is still running. Mark such work as failed so the UI can offer a retry."""
    count = 0
    with session_scope() as db:
        for evaluation in db.scalars(select(Evaluation).where(Evaluation.status.in_(["queued", "running", "cancelling"]))).all():
            evaluation.status, evaluation.verdict, evaluation.message = "failed", "service_failure", "The server restarted before this finished."
            evaluation.finished_at = datetime.now(UTC)
            count += 1
    with session_scope() as db:
        for run in db.scalars(select(PipelineRun).where(PipelineRun.status.in_(["queued", "running"]))).all():
            run.status, run.error = "failed", "The server restarted before this finished."
            run.finished_at = datetime.now(UTC)
            run.response = None
            count += 1
    return count


_ = describe_input


def plan_after_reflection(db: Session, user: User, problem_id: str, quality: str, solved: bool, run_id: str | None = None) -> dict[str, Any] | None:
    """After a reflection answer on a solved problem: an unsure answer earns one more problem of the same technique.

    It changes the plan only when the plan shown with the question was moving on. When that plan already gives one
    more problem of this technique, it stands, so the learner is not told the same thing twice.
    """
    if not solved or quality != "unsure":
        return None
    from ..models import AgentStep
    from . import planner as planner_agent
    from .nodes import load_planner_views

    units, problems = load_planner_views(db, user)
    current = next((p for p in problems if p.id == problem_id), None)
    if current is None:
        return None
    current.solved = True
    data = planner_agent.PlannerInput(units=units, problems=problems, current_problem=current, solved_now=True, goal=user.goal, experience=user.experience_level)
    output = planner_agent.after_reflection(data, quality)
    if output is None:
        return None
    shown = (db.scalar(select(AgentStep.output_summary).where(AgentStep.run_id == run_id, AgentStep.stage == "planner").order_by(AgentStep.sequence.desc()).limit(1))
             if run_id else None) or {}
    already = next((p for p in problems if p.id == shown.get("problem_id")), None)
    if already and already.unit_id == current.unit_id and already.pattern == current.pattern:
        return None
    return output.model_dump()
