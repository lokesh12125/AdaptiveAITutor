"""A learner's profile: what they have done, how they have improved, and the estimates the tutor keeps about them.

Everything comes from stored activity. Estimates are labelled as estimates, and a value with no evidence stays
unknown rather than being guessed. Nothing here mentions other learners: similar-learner matching is described only
as counts and outcomes, never as people.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import analytics
from .models import Evaluation, Hint, InteractionRecord, Problem, StateSnapshot, TopicState, Unit, User
from .tutoring import cognitive
from .tutoring.retrieval import CATEGORIES, LEVEL_VALUE, PROGRESS_VALUE, VECTOR_VERSION

CALENDAR_DAYS = 182
FEATURES = [
    ("Topic mastery", "How well you know the current topic, as the tutor estimates it."),
    ("Confidence", "How sure you said you were, or unknown if you have not said."),
    ("Confusion", "Signs of difficulty, such as a repeated issue after a hint."),
    ("Workload", "Signs that a task feels heavy, such as long gaps or asking for less."),
    ("Progress", "Whether recent attempts are moving forward, stalled or going back."),
    ("Problem difficulty", "How hard the current problem is, from easy to hard."),
    ("Attempts so far", "Graded attempts on this problem, up to six."),
    ("Hints so far", "Hints already seen on this problem, up to four."),
    *[(f"Situation: {c.replace('_', ' ')}", f"1 when the current issue is a {c.replace('_', ' ')} problem.") for c in CATEGORIES],
]
MILESTONES = [
    ("first_solve", "First problem solved", lambda t: t["solved"] >= 1),
    ("ten_solved", "Ten problems solved", lambda t: t["solved"] >= 10),
    ("fifty_solved", "Fifty problems solved", lambda t: t["solved"] >= 50),
    ("first_try", "Solved on the first submission", lambda t: t["first_try_solves"] >= 1),
    ("independent", "Five solved without any hint", lambda t: t["solved_without_hints"] >= 5),
    ("hard", "A hard problem solved", lambda t: t["solved_by_difficulty"]["hard"][0] >= 1),
    ("streak", "Active seven days in a row", lambda t: t["longest_streak"] >= 7),
    ("topics", "Problems solved in five topics", lambda t: t["topics_with_solves"] >= 5),
]


def _streaks(days: set[date], today: date) -> tuple[int, int]:
    longest = run = 0
    previous = None
    for day in sorted(days):
        run = run + 1 if previous and (day - previous).days == 1 else 1
        longest = max(longest, run)
        previous = day
    current = 0
    cursor = today if today in days else today - timedelta(days=1)
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def _solve_records(evaluations: list[Evaluation], hints_by_problem: dict[str, list[datetime]]) -> list[dict[str, Any]]:
    """One row per solved problem: when, after how many submissions, with how many hints, and in how much time."""
    attempts: dict[str, int] = defaultdict(int)
    solved: dict[str, dict[str, Any]] = {}
    for row in evaluations:
        if row.kind != "submit" or row.problem_id in solved:
            continue
        attempts[row.problem_id] += 1
        if row.verdict == "accepted":
            hints = sum(1 for at in hints_by_problem.get(row.problem_id, []) if at <= row.created_at)
            solved[row.problem_id] = {"problem_id": row.problem_id, "at": row.created_at, "attempts": attempts[row.problem_id], "hints": hints, "seconds": row.active_seconds}
    return sorted(solved.values(), key=lambda r: r["at"])


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    times = [r["seconds"] for r in rows if r["seconds"]]
    return {
        "count": len(rows), "attempts_per_solve": round(statistics.mean(r["attempts"] for r in rows), 2) if rows else None,
        "hints_per_solve": round(statistics.mean(r["hints"] for r in rows), 2) if rows else None,
        "first_try_rate": round(sum(1 for r in rows if r["attempts"] == 1) / len(rows), 3) if rows else None,
        "median_minutes": round(statistics.median(times) / 60, 1) if times else None,
    }


def build_profile(db: Session, user_id: str) -> dict[str, Any]:
    user = db.get(User, user_id)
    now = datetime.now(UTC)
    today = now.date()
    open_problems = {p.id: p for p in db.scalars(select(Problem).where(Problem.archived.is_(False))).all()}
    units = {u.id: u for u in db.scalars(select(Unit).order_by(Unit.order_index)).all()}
    evaluations = db.scalars(select(Evaluation).where(Evaluation.user_id == user_id, Evaluation.problem_id.in_(open_problems)).order_by(Evaluation.created_at)).all()
    hints = db.scalars(select(Hint).where(Hint.user_id == user_id, Hint.problem_id.in_(open_problems)).order_by(Hint.created_at)).all()
    hints_by_problem: dict[str, list[datetime]] = defaultdict(list)
    for hint in hints:
        if hint.delivery == "shown":
            hints_by_problem[hint.problem_id].append(hint.created_at)
    solves = _solve_records(list(evaluations), hints_by_problem)
    solved_ids = {r["problem_id"] for r in solves}
    metrics = analytics.learner_metrics(db, [user_id])
    submissions = [e for e in evaluations if e.kind == "submit" and e.verdict not in ("service_failure", "cancelled", None)]

    # ---- activity calendar and streaks
    per_day: dict[date, int] = defaultdict(int)
    for row in evaluations:
        if row.kind in ("run", "submit"):
            per_day[row.created_at.date()] += 1
    for hint in hints:
        per_day[hint.created_at.date()] += 1
    current_streak, longest_streak = _streaks(set(per_day), today)
    start = today - timedelta(days=CALENDAR_DAYS - 1)
    calendar = [{"date": (start + timedelta(days=i)).isoformat(), "count": per_day.get(start + timedelta(days=i), 0)} for i in range(CALENDAR_DAYS)]

    # ---- totals
    by_difficulty = {level: [0, 0] for level in ("easy", "medium", "hard")}
    for problem in open_problems.values():
        if problem.owner_id is None and problem.difficulty in by_difficulty:
            by_difficulty[problem.difficulty][1] += 1
            if problem.id in solved_ids:
                by_difficulty[problem.difficulty][0] += 1
    totals = {
        "solved": len(solves), "started": metrics["started"], "submitted": metrics["submitted"], "completion_rate": metrics["completion_rate"],
        "submissions": len(submissions), "accepted_submissions": sum(1 for e in submissions if e.verdict == "accepted"),
        "acceptance_rate": round(sum(1 for e in submissions if e.verdict == "accepted") / len(submissions), 3) if submissions else None,
        "runs": sum(1 for e in evaluations if e.kind == "run"), "hints_total": sum(len(times) for times in hints_by_problem.values()),
        "hints_per_solved": metrics["hints_per_solved"], "first_try_solves": sum(1 for r in solves if r["attempts"] == 1),
        "solved_without_hints": sum(1 for r in solves if r["hints"] == 0), "solved_by_difficulty": by_difficulty,
        "questions_added": sum(1 for p in open_problems.values() if p.owner_id == user_id),
        "active_minutes": round(sum((r["seconds"] or 0) for r in solves) / 60), "days_active": len(per_day), "current_streak": current_streak, "longest_streak": longest_streak,
        "topics_with_solves": len({open_problems[r["problem_id"]].unit_id for r in solves}),
    }

    # ---- improvement: then and now, and week by week
    half = min(5, len(solves) // 2)
    then_now = None
    if half >= 2:
        early, recent = _summary(solves[:half]), _summary(solves[-half:])
        rows = []
        for key, label, lower_is_better, unit in (("attempts_per_solve", "Submissions per solve", True, ""), ("hints_per_solve", "Hints per solve", True, ""),
                                                  ("first_try_rate", "Solved on the first submission", False, "%"), ("median_minutes", "Minutes to solve", True, " min")):
            a, b = early[key], recent[key]
            better = None if a is None or b is None or a == b else ((b < a) == lower_is_better)
            rows.append({"label": label, "early": a, "recent": b, "better": better, "unit": unit})
        then_now = {"count": half, "rows": rows}
    weekly = []
    for weeks_back in range(7, -1, -1):
        week_start = today - timedelta(days=today.weekday() + 7 * weeks_back)
        week_end = week_start + timedelta(days=7)
        in_week = [r for r in solves if week_start <= r["at"].date() < week_end]
        subs = [e for e in submissions if week_start <= e.created_at.date() < week_end]
        weekly.append({"week_start": week_start.isoformat(), "solved": len(in_week), "submissions": len(subs), **{k: v for k, v in _summary(in_week).items() if k != "count"}})

    # ---- the tutor's estimates, one row per topic
    states = {s.unit_id: s for s in db.scalars(select(TopicState).where(TopicState.user_id == user_id)).all()}
    snapshots = db.scalars(select(StateSnapshot).where(StateSnapshot.user_id == user_id).order_by(StateSnapshot.created_at)).all()
    latest: dict[str, StateSnapshot] = {}
    first: dict[str, StateSnapshot] = {}
    for snap in snapshots:
        latest[snap.unit_id] = snap
        first.setdefault(snap.unit_id, snap)
    totals_by_unit: dict[str, int] = defaultdict(int)
    solved_by_unit: dict[str, int] = defaultdict(int)
    for problem in open_problems.values():
        if problem.owner_id is None:
            totals_by_unit[problem.unit_id] += 1
            if problem.id in solved_ids:
                solved_by_unit[problem.unit_id] += 1
    matrix = []
    for unit_id, unit in units.items():
        state = states.get(unit_id)
        snap = latest.get(unit_id)
        if state is None and snap is None and not solved_by_unit.get(unit_id):
            continue
        estimate = cognitive.mastery_estimate(state.mastery, state.evidence_weight, False, "") if state else None
        start_snap = first.get(unit_id)
        matrix.append({
            "unit_id": unit_id, "title": unit.title, "solved": solved_by_unit.get(unit_id, 0), "total": totals_by_unit.get(unit_id, 0),
            "graded_attempts": state.graded_attempts if state else 0, "independent_solved": state.independent_solved if state else 0, "assisted_solved": state.assisted_solved if state else 0,
            "mastery": round(state.mastery, 3) if state else None, "mastery_low": estimate.low if estimate else None, "mastery_high": estimate.high if estimate else None,
            "band": analytics.BAND_LABEL[estimate.band] if estimate else "Not enough evidence yet", "evidence_weight": round(state.evidence_weight, 2) if state else 0,
            "starting_mastery": round(start_snap.mastery, 3) if start_snap else None,
            "confidence": round(snap.confidence, 2) if snap and snap.confidence is not None else None, "confusion": snap.confusion if snap else None,
            "load": snap.cognitive_load if snap else None, "progress": snap.progress if snap else None, "updated_at": (state.updated_at if state else snap.created_at if snap else None),
        })

    # ---- the situation vector used to find similar learners, and what the last match found
    # A correct submission needs no help, so it runs no similarity search. Use the latest record that did.
    recent_records = db.scalars(select(InteractionRecord).where(InteractionRecord.user_id == user_id).order_by(InteractionRecord.created_at.desc()).limit(50)).all()
    record = next((row for row in recent_records if row.retrieval), None)
    vector = None
    similar = None
    if record is not None:
        stored = (record.retrieval or {}).get("query_vector")
        if stored:
            raw = _raw_values(record, stored)
            vector = {"version": VECTOR_VERSION, "problem": open_problems[record.problem_id].title if record.problem_id in open_problems else None, "at": record.created_at,
                      "features": [{"name": name, "meaning": meaning, "value": stored[i], "raw": raw[i] if i < len(raw) else None} for i, (name, meaning) in enumerate(FEATURES) if i < len(stored)]}
        retrieval = record.retrieval or {}
        if retrieval:
            similar = {
                "matched": bool(retrieval.get("reliable")), "support": retrieval.get("support"), "effectiveness": retrieval.get("effectiveness"), "similarity": retrieval.get("mean_similarity"),
                "candidates": retrieval.get("candidates_considered"), "suggested_strategy": retrieval.get("suggested_strategy"), "reason": retrieval.get("reason"),
                "demo_data": retrieval.get("provenance") in ("synthetic", "mixed"), "at": record.created_at,
            }

    titles = {pid: p.title for pid, p in open_problems.items()}
    recent = [{"problem_id": e.problem_id, "title": titles.get(e.problem_id), "verdict": e.verdict, "passed": e.passed, "total": e.total, "at": e.created_at} for e in reversed(submissions[-10:])]
    return {
        "user": {"name": user.name, "joined": user.created_at, "experience": user.experience_level, "goal": user.goal, "is_demo": user.is_demo},
        "totals": totals, "calendar": calendar, "improvement": {"then_now": then_now, "weekly": weekly, "knowledge_checks": analytics.learning_gain(db, [user_id])},
        "state_matrix": matrix, "vector": vector, "similar": similar,
        "milestones": [{"id": key, "title": title, "achieved": bool(test(totals))} for key, title, test in MILESTONES],
        "recent": recent,
    }


def _raw_values(record: InteractionRecord, vector: list[float]) -> list[str | None]:
    """The plain value behind each feature, where the record has it."""
    cog = record.cognitive or {}
    mastery = (cog.get("mastery") or {}).get("value")
    names = {v: k for k, v in LEVEL_VALUE.items()}
    progress_names = {v: k for k, v in PROGRESS_VALUE.items()}
    def level(value: float) -> str | None:
        return names.get(round((value / 2) + 0.5, 2)) if value != 0 else None
    def progress(value: float) -> str | None:
        return progress_names.get(round((value / 2) + 0.5, 2))
    return [
        f"{round(mastery * 100)}%" if mastery is not None else None,
        f"{round(cog['confidence'] * 100)}%" if cog.get("confidence") is not None else None,
        cog.get("confusion") or level(vector[2]), cog.get("cognitive_load") or level(vector[3]), cog.get("progress") or progress(vector[4]),
        None, None, None,
        *["yes" if value > 0.5 else "no" for value in vector[8:]],
    ]


def state_summary(db: Session, user_id: str) -> dict[str, Any]:
    """One row of the teacher's class table: the same estimates as the profile, summarised across topics."""
    states = db.scalars(select(TopicState).where(TopicState.user_id == user_id)).all()
    weighted = [(s.mastery, s.evidence_weight) for s in states if s.evidence_weight > 0]
    mastery = round(sum(m * w for m, w in weighted) / sum(w for _, w in weighted), 3) if weighted else None
    snap = db.scalar(select(StateSnapshot).where(StateSnapshot.user_id == user_id).order_by(StateSnapshot.created_at.desc()).limit(1))
    evaluations = db.scalars(select(Evaluation).where(Evaluation.user_id == user_id, Evaluation.kind == "submit").order_by(Evaluation.created_at)).all()
    hint_times: dict[str, list[datetime]] = defaultdict(list)
    for problem_id, at in db.execute(select(Hint.problem_id, Hint.created_at).where(Hint.user_id == user_id, Hint.delivery == "shown")).all():
        hint_times[problem_id].append(at)
    solves = _solve_records(list(evaluations), hint_times)
    days = {e.created_at.date() for e in evaluations}
    current, longest = _streaks(days, datetime.now(UTC).date())
    summary = _summary(solves)
    return {
        "mastery": mastery, "topics_started": len(states), "confidence": round(snap.confidence, 2) if snap and snap.confidence is not None else None,
        "confusion": snap.confusion if snap else None, "load": snap.cognitive_load if snap else None, "progress": snap.progress if snap else None,
        "first_try_rate": summary["first_try_rate"], "attempts_per_solve": summary["attempts_per_solve"], "current_streak": current, "longest_streak": longest,
    }
