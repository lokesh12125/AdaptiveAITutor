"""Learning Planner: what to do next, and why. Rule-based, so every recommendation is explainable.

An unresolved task stays active. One success never advances a learner, and heavy reliance on help
leads to independent practice before anything harder. Weak prerequisites are suggested, not imposed.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .contracts import PlanOutput

POLICY = yaml.safe_load((Path(__file__).parent / "policy.yaml").read_text())["planner"]
DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2, None: 1}


@dataclass
class UnitView:
    id: str
    title: str
    order: int
    track: str
    optional: bool
    prerequisites: list[str]
    mastery: float = 0.2
    evidence: float = 0.0
    independent: int = 0
    assisted: int = 0
    solved: int = 0


@dataclass
class ProblemView:
    id: str
    title: str
    unit_id: str
    difficulty: str | None
    solved: bool = False
    attempted: bool = False
    recommended_first: bool = False


@dataclass
class PlannerInput:
    units: list[UnitView]
    problems: list[ProblemView]
    current_problem: ProblemView | None = None
    solved_now: bool = False
    unresolved: bool = False
    service_failure: bool = False
    graded_attempts_on_problem: int = 0
    max_hint_level_on_problem: int = 0
    goal: str | None = None
    experience: str | None = None


def _unit(data: PlannerInput, unit_id: str | None) -> UnitView | None:
    return next((u for u in data.units if u.id == unit_id), None)


def _pick(data: PlannerInput, unit_id: str, exclude: str | None, target_difficulty: int | None = None,
          harder_than: int | None = None) -> ProblemView | None:
    candidates = [p for p in data.problems if p.unit_id == unit_id and not p.solved and p.id != exclude]
    if harder_than is not None:
        harder = [p for p in candidates if DIFFICULTY_ORDER.get(p.difficulty, 1) > harder_than]
        candidates = harder or []
    if not candidates:
        return None
    if target_difficulty is not None:
        candidates.sort(key=lambda p: (abs(DIFFICULTY_ORDER.get(p.difficulty, 1) - target_difficulty), p.attempted))
    else:
        candidates.sort(key=lambda p: (p.attempted, DIFFICULTY_ORDER.get(p.difficulty, 1)))
    return candidates[0]


def _weak_prerequisite(data: PlannerInput, unit: UnitView) -> UnitView | None:
    weakest: UnitView | None = None
    for pid in unit.prerequisites:
        pre = _unit(data, pid)
        if pre and pre.evidence >= 0.5 and pre.mastery < POLICY["prerequisite_gap"]:
            if weakest is None or pre.mastery < weakest.mastery:
                weakest = pre
    return weakest


def _unit_ready(unit: UnitView) -> bool:
    return (unit.mastery >= POLICY["advance_mastery"] and unit.independent >= POLICY["advance_min_independent"]
            and unit.evidence >= POLICY["advance_min_evidence"])


def _next_unit(data: PlannerInput, after: UnitView | None) -> UnitView | None:
    ordered = sorted((u for u in data.units if not u.optional), key=lambda u: u.order)
    tracks: tuple[str, ...] = ("foundations", "algorithms", "dsa")
    if data.goal == "dsa":
        tracks = ("algorithms", "dsa", "foundations") if data.experience in ("intermediate", "advanced") else tracks
    for track in tracks:
        for unit in ordered:
            if unit.track != track or _unit_ready(unit) or (after and unit.id == after.id):
                continue
            blocked = any(
                (pre := _unit(data, pid)) and pre.evidence >= 0.5 and pre.mastery < POLICY["prerequisite_gap"]
                for pid in unit.prerequisites
            )
            if not blocked and any(p.unit_id == unit.id and not p.solved for p in data.problems):
                return unit
    return None


def _alt(action: str, title: str, unit: UnitView | None = None, problem: ProblemView | None = None) -> dict[str, Any]:
    return {"action": action, "title": title, "unit_id": unit.id if unit else None, "problem_id": problem.id if problem else None}


def plan(data: PlannerInput) -> PlanOutput:
    current = data.current_problem
    unit = _unit(data, current.unit_id) if current else None

    if current and unit and data.service_failure:
        return PlanOutput(action="continue_current", title=f"Try {current.title} again", reason="We could not check your code, so nothing about your learning has changed. Try again in a moment.",
                          reason_codes=["SERVICE_FAILURE"], problem_id=current.id, problem_title=current.title, unit_id=unit.id, unit_title=unit.title)

    if current and unit and data.unresolved:
        alternatives = [_alt("review_concept", f"Review {unit.title}", unit)]
        weak = _weak_prerequisite(data, unit)
        if weak and data.graded_attempts_on_problem >= POLICY["stuck_attempts"]:
            practice = _pick(data, weak.id, None, target_difficulty=0)
            if practice:
                return PlanOutput(
                    action="practise_prerequisite", title=f"Practise {weak.title} with {practice.title}",
                    reason=f"You have made {data.graded_attempts_on_problem} attempts here, and {weak.title} supports this topic but looks less secure. A short detour may help. {current.title} stays saved, so you can come back.",
                    reason_codes=["STUCK", "WEAK_PREREQUISITE"], problem_id=practice.id, problem_title=practice.title, unit_id=weak.id, unit_title=weak.title,
                    keep_current_active=True, alternatives=[_alt("continue_current", f"Keep working on {current.title}", unit, current), *alternatives],
                )
        return PlanOutput(action="continue_current", title=f"Keep going with {current.title}", reason="This problem is not finished yet, so it stays your current task. You can leave and come back at any time.",
                          reason_codes=["UNRESOLVED"], problem_id=current.id, problem_title=current.title, unit_id=unit.id, unit_title=unit.title, alternatives=alternatives)

    if current and unit and data.solved_now:
        total_solves = unit.independent + unit.assisted
        dependence = unit.assisted / total_solves if total_solves else 0.0
        current_rank = DIFFICULTY_ORDER.get(current.difficulty, 1)
        if data.max_hint_level_on_problem >= 3 or dependence > POLICY["dependence_ratio"]:
            practice = _pick(data, unit.id, current.id, target_difficulty=current_rank)
            why = "You solved this with substantial help" if data.max_hint_level_on_problem >= 3 else "Several recent solves in this topic used hints"
            if practice:
                return PlanOutput(action="similar_independent", title=f"Try {practice.title} on your own", reason=f"{why}. A similar problem without hints will show how much of it has stuck.",
                                  reason_codes=["ASSISTANCE_DEPENDENCE"], problem_id=practice.id, problem_title=practice.title, unit_id=unit.id, unit_title=unit.title, keep_current_active=False,
                                  alternatives=[_alt("review_concept", f"Review {unit.title}", unit)])
        if _unit_ready(unit):
            harder = _pick(data, unit.id, current.id, harder_than=current_rank)
            if harder:
                return PlanOutput(action="harder_next", title=f"Step up to {harder.title}", reason=f"You have solved several {unit.title} problems without hints, so a harder one should be a good stretch.",
                                  reason_codes=["READY_HARDER"], problem_id=harder.id, problem_title=harder.title, unit_id=unit.id, unit_title=unit.title, keep_current_active=False,
                                  alternatives=[_alt("similar_independent", f"More {unit.title} practice", unit)])
            following = _next_unit(data, unit)
            if following:
                first = _pick(data, following.id, None, target_difficulty=0)
                if first:
                    return PlanOutput(action="harder_next", title=f"Move on to {following.title}", reason=f"Your work in {unit.title} is looking secure, so {following.title} is a sensible next topic.",
                                      reason_codes=["READY_NEXT_UNIT"], problem_id=first.id, problem_title=first.title, unit_id=following.id, unit_title=following.title, keep_current_active=False,
                                      alternatives=[_alt("similar_independent", f"More {unit.title} practice", unit)])
        practice = _pick(data, unit.id, current.id, target_difficulty=current_rank)
        if practice:
            return PlanOutput(action="similar_independent", title=f"Next, try {practice.title}", reason="One solved problem is a good sign, but it does not yet show the idea is secure. Another similar problem will tell us more.",
                              reason_codes=["CONFIRM_WITH_PRACTICE"], problem_id=practice.id, problem_title=practice.title, unit_id=unit.id, unit_title=unit.title, keep_current_active=False,
                              alternatives=[_alt("review_concept", f"Review {unit.title}", unit)])
        following = _next_unit(data, unit)
        if following:
            first = _pick(data, following.id, None, target_difficulty=0)
            if first:
                return PlanOutput(action="harder_next", title=f"Move on to {following.title}", reason=f"You have finished the available problems in {unit.title}.",
                                  reason_codes=["UNIT_EXHAUSTED"], problem_id=first.id, problem_title=first.title, unit_id=following.id, unit_title=following.title, keep_current_active=False)
        return PlanOutput(action="review_concept", title="Explore any topic you like", reason="You have worked through the problems the planner would choose next. Pick any topic, or add your own question.",
                          reason_codes=["NOTHING_LEFT"], unit_id=unit.id, unit_title=unit.title, keep_current_active=False)

    # No current problem: home screen and path recommendations.
    started = [p for p in data.problems if p.attempted and not p.solved]
    if started:
        recent = started[0]
        started_unit = _unit(data, recent.unit_id)
        return PlanOutput(action="continue_current", title=f"Continue {recent.title}", reason="You started this one and have not finished it yet.", reason_codes=["UNRESOLVED"],
                          problem_id=recent.id, problem_title=recent.title, unit_id=recent.unit_id, unit_title=started_unit.title if started_unit else None)
    first_ever = not any(p.attempted or p.solved for p in data.problems)
    if first_ever and data.experience != "advanced" and data.goal != "dsa":
        first = next((p for p in data.problems if p.recommended_first), None)
        if first:
            first_unit = _unit(data, first.unit_id)
            return PlanOutput(action="start_path", title=f"Start with {first.title}", reason="This is a gentle first exercise that shows how the workspace, tests and hints fit together.", reason_codes=["FIRST_EXERCISE"],
                              problem_id=first.id, problem_title=first.title, unit_id=first.unit_id, unit_title=first_unit.title if first_unit else None, keep_current_active=False)
    following = _next_unit(data, None)
    if following:
        first = _pick(data, following.id, None, target_difficulty=0)
        if first:
            reason = f"{following.title} is the next topic with room to grow, based on your work and goals so far."
            return PlanOutput(action="start_path", title=f"Next: {first.title}", reason=reason, reason_codes=["NEXT_IN_PATH"], problem_id=first.id, problem_title=first.title,
                              unit_id=following.id, unit_title=following.title, keep_current_active=False)
    return PlanOutput(action="review_concept", title="Explore any topic you like", reason="There is no specific recommendation right now.", reason_codes=["NOTHING_LEFT"], keep_current_active=False)
