"""Metrics computed from stored records only. Every metric states its denominator and limits.

Learning gain uses pre and post knowledge checks only, never the system's own mastery estimate.
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    AssessmentAttempt,
    ClassMember,
    Diagnostic,
    Draft,
    Evaluation,
    Hint,
    Problem,
    StateSnapshot,
    SurveyResponse,
    TopicState,
    Unit,
)

BAND_LABEL = {"not_enough_evidence": "Not enough evidence yet", "starting": "Just starting", "developing": "Developing", "proficient": "Proficient", "strong": "Strong"}
ERROR_LABEL = {
    "syntax": "Syntax errors", "runtime": "Errors while running", "timeout": "Time limit reached", "memory": "Memory limit reached", "output_limit": "Too much output",
    "wrong_answer": "Wrong answers", "partial": "Partly correct", "missing_function": "Function not found",
}
ISSUE_LABEL = {
    "logic:off_by_one": "Off-by-one boundaries", "logic:early_return_in_loop": "Returning too early in a loop", "logic:missing_return": "Missing return", "logic:print_instead_of_return": "Printing instead of returning",
    "logic:edge_case": "Edge cases", "logic:wrong_return_type": "Wrong kind of result", "logic:wrong_order": "Wrong order", "logic:not_implemented": "Function not started", "logic:general": "General logic",
    "logic:returned_none_on_path": "Some paths return nothing", "logic:text_format": "Text format differences", "logic:stdout_mismatch": "Printed output mismatch", "timeout:loop_no_progress": "Loops that do not end",
    "timeout:recursion_no_base": "Recursion without a stopping case", "timeout:general": "Slow or endless code", "syntax:missing_colon": "Missing colons", "syntax:indentation": "Indentation",
    "syntax:unbalanced_bracket": "Unbalanced brackets", "syntax:unterminated_string": "Unfinished strings", "syntax:assignment_vs_comparison": "= versus ==", "syntax:other": "Other syntax",
}


def issue_label(key: str) -> str:
    if key.startswith("runtime:"):
        return key.split(":", 1)[1]
    return ISSUE_LABEL.get(key, key.replace("_", " ").split(":")[-1].capitalize())


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def learner_metrics(db: Session, user_ids: list[str]) -> dict[str, Any]:
    """Shared by the student and teacher views, so both always agree."""
    empty = {"started": 0, "submitted": 0, "solved": 0, "completion_rate": None, "hints_total": 0, "hints_per_solved": None, "median_seconds_to_complete": None, "time_sample": 0, "graded_attempts": 0, "hint_progress_rate": None, "hints_with_outcome": 0}
    if not user_ids:
        return empty
    graded = db.execute(
        select(Evaluation.user_id, Evaluation.problem_id, Evaluation.verdict, Evaluation.active_seconds, Evaluation.created_at)
        .where(Evaluation.user_id.in_(user_ids), Evaluation.kind == "submit", Evaluation.verdict.notin_(["service_failure", "cancelled", "no_tests"]), Evaluation.status == "completed")
        .order_by(Evaluation.created_at)
    ).all()
    attempted = {(r.user_id, r.problem_id) for r in graded}
    # A problem counts as started once the learner works on it in any way: code saved, run, a hint, or a submission.
    # Counting only submissions made the rate look perfect while unfinished problems were never submitted.
    open_problems = set(db.scalars(select(Problem.id).where(Problem.archived.is_(False))).all())
    worked = {
        *((r.user_id, r.problem_id) for r in db.execute(select(Evaluation.user_id, Evaluation.problem_id).where(Evaluation.user_id.in_(user_ids))).all()),
        *((r.user_id, r.problem_id) for r in db.execute(select(Draft.user_id, Draft.problem_id).where(Draft.user_id.in_(user_ids))).all()),
        *((r.user_id, r.problem_id) for r in db.execute(select(Hint.user_id, Hint.problem_id).where(Hint.user_id.in_(user_ids))).all()),
    }
    started = {pair for pair in worked | attempted if pair[1] in open_problems}
    solved: dict[tuple[str, str], int | None] = {}
    for row in graded:
        if row.verdict == "accepted" and (row.user_id, row.problem_id) not in solved:
            solved[(row.user_id, row.problem_id)] = row.active_seconds
    hints = db.execute(select(Hint.user_id, Hint.problem_id, Hint.outcome).where(Hint.user_id.in_(user_ids), Hint.delivery == "shown")).all()
    on_solved = sum(1 for h in hints if (h.user_id, h.problem_id) in solved)
    times = [t for t in solved.values() if t is not None]
    with_outcome = [h for h in hints if h.outcome]
    return {
        "started": len(started), "solved": len(solved), "completion_rate": rate(len(solved), len(started)), "hints_total": len(hints),
        "hints_per_solved": round(on_solved / len(solved), 2) if solved else None,
        "median_seconds_to_complete": int(statistics.median(times)) if times else None, "time_sample": len(times), "graded_attempts": len(graded), "submitted": len(attempted),
        "hint_progress_rate": rate(sum(1 for h in with_outcome if h.outcome in ("progress", "solved")), len(with_outcome)), "hints_with_outcome": len(with_outcome),
    }


def activity_by_day(db: Session, user_ids: list[str], days: int = 14) -> list[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=days - 1)
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.execute(
        select(func.date_trunc("day", Evaluation.created_at).label("day"), Evaluation.kind, func.count())
        .where(Evaluation.user_id.in_(user_ids), Evaluation.created_at >= since).group_by("day", Evaluation.kind)
    ).all() if user_ids else []
    table: dict[str, dict[str, int]] = defaultdict(lambda: {"run": 0, "submit": 0})
    for day, kind, count in rows:
        if kind in ("run", "submit"):
            table[day.date().isoformat()][kind] += count
    hints = db.execute(
        select(func.date_trunc("day", Hint.created_at).label("day"), func.count()).where(Hint.user_id.in_(user_ids), Hint.created_at >= since).group_by("day")
    ).all() if user_ids else []
    hint_map = {d.date().isoformat(): c for d, c in hints}
    return [
        {"date": (date := (since + timedelta(days=i)).date().isoformat()), "runs": table[date]["run"], "submissions": table[date]["submit"], "hints": hint_map.get(date, 0)}
        for i in range(days)
    ]


def latest_estimates(db: Session, user_id: str) -> dict[str, Any] | None:
    row = db.scalar(select(StateSnapshot).where(StateSnapshot.user_id == user_id).order_by(StateSnapshot.created_at.desc()).limit(1))
    if not row:
        return None
    problem = db.get(Problem, row.problem_id)
    return {
        "at": row.created_at, "problem_title": problem.title if problem else None, "confidence": row.confidence, "confusion": row.confusion, "cognitive_load": row.cognitive_load, "progress": row.progress,
        "evidence": row.evidence, "method_version": row.method_version,
    }


def learning_gain(db: Session, user_ids: list[str]) -> dict[str, Any]:
    note = "Normalised gain = (post − pre) / (maximum − pre), from the two knowledge checks. It is not derived from the tutor's own estimates."
    rows = db.scalars(select(AssessmentAttempt).where(AssessmentAttempt.user_id.in_(user_ids))).all() if user_ids else []
    by_user: dict[str, dict[str, AssessmentAttempt]] = defaultdict(dict)
    for row in rows:
        by_user[row.user_id][row.phase] = row
    gains = []
    for phases in by_user.values():
        if "pre" in phases and "post" in phases and phases["pre"].max_score > phases["pre"].score:
            pre, post = phases["pre"], phases["post"]
            gains.append((post.score / post.max_score - pre.score / pre.max_score) / (1 - pre.score / pre.max_score))
    return {"available": bool(gains), "mean_normalised_gain": round(statistics.mean(gains), 3) if gains else None, "pairs": len(gains), "with_pre_only": sum(1 for p in by_user.values() if "pre" in p and "post" not in p), "note": note}


def satisfaction(db: Session, user_ids: list[str]) -> dict[str, Any]:
    rows = db.scalars(select(SurveyResponse).where(SurveyResponse.user_id.in_(user_ids))).all() if user_ids else []
    if not rows:
        return {"responses": 0, "median": None, "items": None}

    def med(values: list[int]) -> float:
        return float(statistics.median(values))

    items = {"usefulness": med([r.usefulness for r in rows]), "clarity": med([r.clarity for r in rows]), "hint_adequacy": med([r.hint_adequacy for r in rows]), "adaptivity": med([r.adaptivity for r in rows])}
    overall = med([r.usefulness for r in rows] + [r.clarity for r in rows] + [r.hint_adequacy for r in rows] + [r.adaptivity for r in rows])
    return {"responses": len(rows), "median": overall, "items": items}


def class_member_ids(db: Session, class_id: str) -> list[str]:
    return list(db.scalars(select(ClassMember.user_id).where(ClassMember.class_id == class_id)).all())


def topic_difficulties(db: Session, user_ids: list[str]) -> list[dict[str, Any]]:
    if not user_ids:
        return []
    rows = db.execute(
        select(Problem.unit_id, Evaluation.user_id, Evaluation.problem_id, Evaluation.verdict).join(Problem, Problem.id == Evaluation.problem_id)
        .where(Evaluation.user_id.in_(user_ids), Evaluation.kind == "submit", Evaluation.status == "completed", Evaluation.verdict.notin_(["service_failure", "cancelled", "no_tests"]))
        .order_by(Evaluation.created_at)
    ).all()
    per_unit: dict[str, dict[str, Any]] = defaultdict(lambda: {"attempts": 0, "first": {}, "solved": set(), "started": set()})
    for unit_id, user_id, problem_id, verdict in rows:
        stats = per_unit[unit_id]
        stats["attempts"] += 1
        key = (user_id, problem_id)
        stats["started"].add(key)
        stats["first"].setdefault(key, verdict == "accepted")
        if verdict == "accepted":
            stats["solved"].add(key)
    titles = dict(db.execute(select(Unit.id, Unit.title)).all())
    orders = dict(db.execute(select(Unit.id, Unit.order_index)).all())
    output = []
    for unit_id, stats in per_unit.items():
        started = len(stats["started"])
        output.append({
            "unit_id": unit_id, "title": titles.get(unit_id, unit_id), "order": orders.get(unit_id, 0), "attempts": stats["attempts"], "problems_started": started,
            "first_try_rate": rate(sum(stats["first"].values()), started), "completion_rate": rate(len(stats["solved"]), started),
            "attempts_per_problem": round(stats["attempts"] / started, 2) if started else None,
        })
    return sorted(output, key=lambda r: r["order"])


def common_errors(db: Session, user_ids: list[str], limit: int = 8) -> dict[str, Any]:
    if not user_ids:
        return {"items": [], "total": 0}
    rows = db.execute(select(Diagnostic.issue_key).where(Diagnostic.user_id.in_(user_ids), Diagnostic.category.notin_(["accepted", "service_failure", "cancelled", "no_tests"]))).all()
    counts = Counter(r[0] for r in rows)
    total = sum(counts.values())
    learners = dict(db.execute(select(Diagnostic.issue_key, func.count(func.distinct(Diagnostic.user_id))).where(Diagnostic.user_id.in_(user_ids)).group_by(Diagnostic.issue_key)).all())
    return {"items": [{"issue_key": k, "label": issue_label(k), "count": c, "share": rate(c, total), "learners": learners.get(k, 0)} for k, c in counts.most_common(limit)], "total": total}


def assistance(db: Session, user_ids: list[str]) -> dict[str, Any]:
    if not user_ids:
        return {"by_level": [], "requested": 0, "automatic": 0, "total": 0, "feedback_helpful": 0, "feedback_total": 0}
    rows = db.execute(select(Hint.level, Hint.requested, Hint.outcome, Hint.helpful).where(Hint.user_id.in_(user_ids), Hint.delivery == "shown")).all()
    by_level: dict[int, dict[str, int]] = defaultdict(lambda: {"count": 0, "resolved": 0, "progress": 0})
    for level, _, outcome, _ in rows:
        by_level[level]["count"] += 1
        if outcome:
            by_level[level]["resolved"] += 1
            if outcome in ("progress", "solved"):
                by_level[level]["progress"] += 1
    return {
        "by_level": [{"level": lvl, **vals, "progress_rate": rate(vals["progress"], vals["resolved"])} for lvl, vals in sorted(by_level.items())],
        "requested": sum(1 for r in rows if r.requested), "automatic": sum(1 for r in rows if not r.requested), "total": len(rows),
        "feedback_helpful": sum(1 for r in rows if r.helpful is True), "feedback_total": sum(1 for r in rows if r.helpful is not None),
    }


def learner_flags(db: Session, user_id: str, now: datetime | None = None) -> list[dict[str, Any]]:
    """Possible reasons a learner may need support, with their evidence. These are prompts for a conversation, not conclusions."""
    now = now or datetime.now(UTC)
    flags: list[dict[str, Any]] = []
    window = now - timedelta(days=14)
    diagnostics = db.execute(
        select(Diagnostic.problem_id, Diagnostic.issue_key, Diagnostic.repeat_count, Diagnostic.category).where(Diagnostic.user_id == user_id, Diagnostic.created_at >= window).order_by(Diagnostic.created_at.desc()).limit(40)
    ).all()
    repeated = [d for d in diagnostics if d.repeat_count >= 3 and d.category != "accepted"]
    no_progress = db.scalar(select(func.count()).select_from(Hint).where(Hint.user_id == user_id, Hint.outcome == "no_progress", Hint.created_at >= window)) or 0
    attempts = db.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.user_id == user_id, Evaluation.kind == "submit", Evaluation.created_at >= window)) or 0
    if repeated and no_progress >= 2:
        problem = db.get(Problem, repeated[0].problem_id)
        flags.append({
            "kind": "repeated_issue", "title": "Repeating the same issue",
            "evidence": [f"{issue_label(repeated[0].issue_key)} appeared {repeated[0].repeat_count} times in a row on {problem.title if problem else 'a problem'}.", f"{no_progress} recent hints were not followed by progress."],
            "uncertainty": "Based on the last 14 days. The learner may also be experimenting.", "strength": "stronger",
        })
    weak = db.scalars(select(TopicState).where(TopicState.user_id == user_id, TopicState.evidence_weight >= 3.0, TopicState.mastery < 0.35)).all()
    titles = dict(db.execute(select(Unit.id, Unit.title)).all())
    for state in weak[:2]:
        flags.append({
            "kind": "low_mastery", "title": f"Low estimate in {titles.get(state.unit_id, state.unit_id)}",
            "evidence": [f"{state.graded_attempts} graded attempts in this topic, {state.solved_count} solved."],
            "uncertainty": "The tutor's estimate, from coding activity only. It is not a test score.", "strength": "moderate",
        })
    last = db.scalar(select(func.max(Evaluation.created_at)).where(Evaluation.user_id == user_id))
    if last and now - last > timedelta(days=7):
        days = (now - last).days
        flags.append({"kind": "inactive", "title": "No recent activity", "evidence": [f"Last activity was {days} days ago."], "uncertainty": "They may be practising elsewhere or taking a break.", "strength": "weak"})
    if flags and attempts < 5:
        for flag in flags:
            flag["uncertainty"] += " Limited evidence: fewer than 5 attempts in this period."
    return flags
