"""Learning Planner: what to do next, and why. Rule-based, so every recommendation is explainable.

It sequences practice the way a teacher would. Inside a topic, each technique is practised in the lesson's order at the
easy level, then each at medium, then at hard. A technique counts as practised after 2 solved problems, or 1 when the
learner solved it on the first try without help. After a solve that needed a lot of help, the next problem uses the
same technique at the same difficulty, without hints. When a topic is secure, the next topic is the next one forward
from where the learner is working, never an earlier topic they chose to skip, unless one of its prerequisites has
shown weakness. An unresolved task stays active, one success never advances a learner past a topic, and weak
prerequisites are suggested, not imposed. Every plan carries a short route: where the learner is, and what comes next.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from .contracts import PlanOutput

POLICY = yaml.safe_load((Path(__file__).parent / "policy.yaml").read_text())["planner"]
DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2, None: 1}
LEVEL_WORD = {0: "easy", 1: "medium", 2: "hard"}


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
    patterns: list[str] = field(default_factory=list)  # the lesson's techniques, in teaching order


@dataclass
class ProblemView:
    id: str
    title: str
    unit_id: str
    difficulty: str | None
    solved: bool = False
    attempted: bool = False
    recommended_first: bool = False
    pattern: str | None = None
    fluent: bool = False  # solved on the first graded attempt, with no hint shown before it


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


def _rank(problem: ProblemView) -> int:
    return DIFFICULTY_ORDER.get(problem.difficulty, 1)


def _position(data: PlannerInput) -> dict[str, int]:
    return {p.id: i for i, p in enumerate(data.problems)}


def _pick(data: PlannerInput, unit_id: str, exclude: str | None, target_difficulty: int | None = None,
          harder_than: int | None = None, pattern: str | None = None) -> ProblemView | None:
    """The best unsolved problem in a topic: the requested technique first, then the nearest difficulty."""
    candidates = [p for p in data.problems if p.unit_id == unit_id and not p.solved and p.id != exclude]
    if harder_than is not None:
        candidates = [p for p in candidates if _rank(p) > harder_than]
    if not candidates:
        return None
    unit = _unit(data, unit_id)
    order = {name: i for i, name in enumerate(unit.patterns if unit else [])}
    position = _position(data)
    candidates.sort(key=lambda p: (
        0 if pattern is None or p.pattern == pattern else 1,
        abs(_rank(p) - target_difficulty) if target_difficulty is not None else _rank(p),
        p.attempted,
        order.get(p.pattern or "", len(order)),
        position[p.id],
    ))
    return candidates[0]


def _solved_count(data: PlannerInput, unit_id: str, pattern: str | None, level: int | None = None) -> int:
    return sum(1 for p in data.problems if p.unit_id == unit_id and p.solved and p.pattern == pattern and (level is None or _rank(p) == level))


def _has_unsolved(data: PlannerInput, unit_id: str, pattern: str | None, level: int) -> bool:
    return any(p.unit_id == unit_id and not p.solved and p.pattern == pattern and _rank(p) == level for p in data.problems)


def _fluent_solve(data: PlannerInput, unit_id: str, pattern: str | None, level: int) -> bool:
    return any(p.unit_id == unit_id and p.solved and p.fluent and p.pattern == pattern and _rank(p) == level for p in data.problems)


def _sequence_next(data: PlannerInput, unit: UnitView, exclude: str | None) -> tuple[ProblemView | None, str, str | None]:
    """The next step in the topic's teaching sequence: (problem, what kind of step it is, its technique).

    Easy first, technique by technique in the lesson's order, then medium, then hard. At the easy level a technique
    is practised after 2 solves, or 1 solved on the first try without hints; above it, after 1 solve. The same rule
    runs after a submission and on the home screen, so both always suggest the same next step.
    """
    patterns = unit.patterns or sorted({p.pattern for p in data.problems if p.unit_id == unit.id and p.pattern}, key=str)
    for level in (0, 1, 2):
        needed = 2 if level == 0 else 1
        for pattern in patterns:
            practised = _solved_count(data, unit.id, pattern, level) >= needed or _fluent_solve(data, unit.id, pattern, level)
            if not practised and _has_unsolved(data, unit.id, pattern, level):
                problem = _pick(data, unit.id, exclude, target_difficulty=level, pattern=pattern)
                if problem and problem.pattern == pattern and _rank(problem) == level:
                    return problem, ("level" if level else "technique"), pattern
    leftover = _pick(data, unit.id, exclude)
    return leftover, "any", leftover.pattern if leftover else None


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


def _sequence(data: PlannerInput) -> list[UnitView]:
    """Topics in the order this learner should meet them, by track and then by the curriculum's order."""
    ordered = sorted((u for u in data.units if not u.optional), key=lambda u: u.order)
    tracks: tuple[str, ...] = ("foundations", "algorithms", "dsa")
    if data.goal == "dsa" and data.experience in ("intermediate", "advanced"):
        tracks = ("algorithms", "dsa", "foundations")
    return [u for track in tracks for u in ordered if u.track == track] + [u for u in ordered if u.track not in tracks]


def _blocked(data: PlannerInput, unit: UnitView) -> bool:
    """A weak prerequisite holds a topic back only while it still has problems left to practise."""
    open_units = {p.unit_id for p in data.problems if not p.solved}
    return any((pre := _unit(data, pid)) and pre.evidence >= 0.5 and pre.mastery < POLICY["prerequisite_gap"] and pre.id in open_units for pid in unit.prerequisites)


def _next_unit(data: PlannerInput, after: UnitView | None) -> UnitView | None:
    """The next topic forward from `after`. Earlier topics come back only if the learner has already worked in them."""
    sequence = _sequence(data)
    start = next((i + 1 for i, u in enumerate(sequence) if after and u.id == after.id), 0)
    open_problems = {p.unit_id for p in data.problems if not p.solved}
    # A topic held back by a weak prerequisite also holds back every topic that builds on it, so the planner never
    # jumps past it to something that needs it.
    held: set[str] = set()
    for unit in sequence[start:]:
        if any(pid in held for pid in unit.prerequisites):
            held.add(unit.id)
            continue
        if _unit_ready(unit) or unit.id not in open_problems:
            continue
        if _blocked(data, unit):
            held.add(unit.id)
            continue
        return unit
    for unit in sequence[:start]:
        if unit.evidence > 0 and not _unit_ready(unit) and unit.id in open_problems and (after is None or unit.id != after.id):
            return unit
    return None


def _anchor(data: PlannerInput) -> UnitView | None:
    """The topic the learner was most recently working in."""
    recent = next((p for p in data.problems if p.attempted or p.solved), None)
    return _unit(data, recent.unit_id) if recent else None


def _route(data: PlannerInput, here: UnitView | None) -> list[dict[str, Any]]:
    """Where the learner is, then up to three topics ahead in course order, so they can see the way toward advanced work.

    It is a preview of the order, not a recommendation, so a topic is not left out because the one being worked on now
    is not secure yet: that is the normal case while a learner is in the middle of a topic.
    """
    counts: dict[str, list[int]] = {}
    for p in data.problems:
        counts.setdefault(p.unit_id, [0, 0])
        counts[p.unit_id][1] += 1
        counts[p.unit_id][0] += int(p.solved)
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = here
    if current:
        steps.append({"unit_id": current.id, "title": current.title, "solved": counts.get(current.id, [0, 0])[0], "total": counts.get(current.id, [0, 0])[1],
                      "status": "secure" if _unit_ready(current) else "now"})
        seen.add(current.id)
    sequence = _sequence(data)
    start = next((i + 1 for i, u in enumerate(sequence) if current and u.id == current.id), 0)
    for unit in sequence[start:]:
        if len(steps) >= 4:
            break
        if unit.id in seen or _unit_ready(unit) or not counts.get(unit.id, [0, 0])[1] - counts.get(unit.id, [0, 0])[0]:
            continue
        steps.append({"unit_id": unit.id, "title": unit.title, "solved": counts[unit.id][0], "total": counts[unit.id][1], "status": "next"})
        seen.add(unit.id)
    return steps


def _alt(action: str, title: str, unit: UnitView | None = None, problem: ProblemView | None = None) -> dict[str, Any]:
    return {"action": action, "title": title, "unit_id": unit.id if unit else None, "problem_id": problem.id if problem else None}


def _out(data: PlannerInput, here: UnitView | None, **fields: Any) -> PlanOutput:
    return PlanOutput(**fields, route=_route(data, here))


def _step_in_topic(data: PlannerInput, unit: UnitView, current: ProblemView | None, intro: str) -> PlanOutput | None:
    """The next problem in the topic's sequence, with a reason that says which kind of step it is."""
    problem, kind, pattern = _sequence_next(data, unit, current.id if current else None)
    if problem is None:
        return None
    technique = (pattern or "this technique").lower()
    # On the home screen there is no current problem: a technique the learner has already solved once is the same one, being consolidated.
    same = pattern == current.pattern if current is not None else _solved_count(data, unit.id, pattern, 0) > 0
    if kind == "technique" and same:
        title, reason, code = f"One more {technique} problem: {problem.title}", f"{intro}A second {technique} problem, on your own, makes the technique stick before the next one.", "CONSOLIDATE_TECHNIQUE"
    elif kind == "technique":
        order = unit.patterns or []
        earlier = current is not None and current.pattern in order and pattern in order and order.index(pattern) < order.index(current.pattern)
        tried = _solved_count(data, unit.id, pattern, 0) > 0
        settle = "needs one more solve to settle" if tried else "has not been practised yet"
        where = f"{technique.capitalize()} comes earlier in the lesson and {settle}" if earlier else f"Next in the lesson is {technique}"
        title, reason, code = f"Next technique: {problem.title}", f"{intro}{where}, so this easy problem covers it.", "NEXT_TECHNIQUE"
    elif kind == "level":
        level = LEVEL_WORD[_rank(problem)]
        title, reason, code = f"Step up: {problem.title}", f"{intro}You have practised the {unit.title} techniques at the easier level, so this {level} {technique} problem is the next stretch.", "STEP_UP_DIFFICULTY"
    else:
        title = f"Next, try {problem.title}"
        reason = f"{intro}One solved problem is a good sign, but it does not yet show the idea is secure. Another {unit.title} problem will tell us more."
        code = "CONFIRM_WITH_PRACTICE"
    # Only a harder problem or a new topic counts as moving the learner on. A new technique at the same level does not.
    action = "harder_next" if kind == "level" else "similar_independent"
    return _out(data, unit, action=action, title=title, reason=reason, reason_codes=[code],
                problem_id=problem.id, problem_title=problem.title, unit_id=unit.id, unit_title=unit.title, keep_current_active=False,
                alternatives=[_alt("review_concept", f"Review {unit.title}", unit)])


def _move_on(data: PlannerInput, unit: UnitView, reason_start: str, code: str) -> PlanOutput | None:
    following = _next_unit(data, unit)
    if not following:
        return None
    first = _sequence_next(data, following, None)[0] or _pick(data, following.id, None, target_difficulty=0)
    if not first:
        return None
    backwards = following.order < unit.order
    reason = f"{reason_start} {following.title} is {'an earlier topic you have started but not yet secured' if backwards else 'the next topic'}, and {first.title} is where it begins."
    return _out(data, unit, action="harder_next", title=f"Move on to {following.title}", reason=reason, reason_codes=[code],
                problem_id=first.id, problem_title=first.title, unit_id=following.id, unit_title=following.title, keep_current_active=False,
                alternatives=[_alt("similar_independent", f"More {unit.title} practice", unit)])


def plan(data: PlannerInput) -> PlanOutput:
    current = data.current_problem
    unit = _unit(data, current.unit_id) if current else None

    if current and unit and data.service_failure:
        return _out(data, unit, action="continue_current", title=f"Try {current.title} again", reason="We could not check your code, so nothing about your learning has changed. Try again in a moment.",
                    reason_codes=["SERVICE_FAILURE"], problem_id=current.id, problem_title=current.title, unit_id=unit.id, unit_title=unit.title)

    if current and unit and data.unresolved:
        alternatives = [_alt("review_concept", f"Review {unit.title}", unit)]
        weak = _weak_prerequisite(data, unit)
        if weak and data.graded_attempts_on_problem >= POLICY["stuck_attempts"]:
            practice = _sequence_next(data, weak, None)[0] or _pick(data, weak.id, None, target_difficulty=0)
            if practice:
                return _out(data, unit,
                    action="practise_prerequisite", title=f"Practise {weak.title} with {practice.title}",
                    reason=f"You have made {data.graded_attempts_on_problem} attempts here, and {weak.title} supports this topic but looks less secure. A short detour may help. {current.title} stays saved, so you can come back.",
                    reason_codes=["STUCK", "WEAK_PREREQUISITE"], problem_id=practice.id, problem_title=practice.title, unit_id=weak.id, unit_title=weak.title,
                    keep_current_active=True, alternatives=[_alt("continue_current", f"Keep working on {current.title}", unit, current), *alternatives],
                )
        return _out(data, unit, action="continue_current", title=f"Keep going with {current.title}", reason="This problem is not finished yet, so it stays your current task. You can leave and come back at any time.",
                    reason_codes=["UNRESOLVED"], problem_id=current.id, problem_title=current.title, unit_id=unit.id, unit_title=unit.title, alternatives=alternatives)

    if current and unit and data.solved_now:
        total_solves = unit.independent + unit.assisted
        dependence = unit.assisted / total_solves if total_solves else 0.0
        heavy_help = data.max_hint_level_on_problem >= 3
        if heavy_help or (dependence > POLICY["dependence_ratio"] and data.max_hint_level_on_problem >= 1):
            practice = _pick(data, unit.id, current.id, target_difficulty=_rank(current), pattern=current.pattern)
            why = "You solved this with substantial help" if heavy_help else "Several recent solves in this topic used hints"
            if practice:
                return _out(data, unit, action="similar_independent", title=f"Try {practice.title} on your own",
                            reason=f"{why}. Another {(practice.pattern or 'similar').lower()} problem at the same level, without hints, will show how much of it has stuck.",
                            reason_codes=["ASSISTANCE_DEPENDENCE"], problem_id=practice.id, problem_title=practice.title, unit_id=unit.id, unit_title=unit.title, keep_current_active=False,
                            alternatives=[_alt("review_concept", f"Review {unit.title}", unit)])
        fluent = data.graded_attempts_on_problem <= 1 and data.max_hint_level_on_problem == 0
        if fluent and not current.fluent:
            current = replace(current, fluent=True)
            data = replace(data, current_problem=current, problems=[current if p.id == current.id else p for p in data.problems])
        if _unit_ready(unit):
            harder = _pick(data, unit.id, current.id, harder_than=_rank(current))
            if harder:
                return _out(data, unit, action="harder_next", title=f"Step up to {harder.title}", reason=f"You have solved several {unit.title} problems without hints, so a harder one should be a good stretch.",
                            reason_codes=["READY_HARDER"], problem_id=harder.id, problem_title=harder.title, unit_id=unit.id, unit_title=unit.title, keep_current_active=False,
                            alternatives=[_alt("similar_independent", f"More {unit.title} practice", unit)])
            moved = _move_on(data, unit, f"Your work in {unit.title} is looking secure.", "READY_NEXT_UNIT")
            if moved:
                return moved
        intro = "Solved on your first try without hints. " if fluent else "Solved. "
        step = _step_in_topic(data, unit, current, intro)
        if step:
            return step
        moved = _move_on(data, unit, f"You have finished the available problems in {unit.title}.", "UNIT_EXHAUSTED")
        if moved:
            return moved
        return _out(data, unit, action="review_concept", title="Explore any topic you like", reason="You have worked through the problems the planner would choose next. Pick any topic, or add your own question.",
                    reason_codes=["NOTHING_LEFT"], unit_id=unit.id, unit_title=unit.title, keep_current_active=False)

    # No current problem: home screen and path recommendations.
    started = [p for p in data.problems if p.attempted and not p.solved]
    if started:
        recent = started[0]
        started_unit = _unit(data, recent.unit_id)
        return _out(data, started_unit, action="continue_current", title=f"Continue {recent.title}", reason="You started this one and have not finished it yet.", reason_codes=["UNRESOLVED"],
                    problem_id=recent.id, problem_title=recent.title, unit_id=recent.unit_id, unit_title=started_unit.title if started_unit else None)
    first_ever = not any(p.attempted or p.solved for p in data.problems)
    if first_ever and data.experience != "advanced" and data.goal != "dsa":
        first = next((p for p in data.problems if p.recommended_first), None)
        if first:
            first_unit = _unit(data, first.unit_id)
            return _out(data, first_unit, action="start_path", title=f"Start with {first.title}", reason="This is a gentle first exercise that shows how the workspace, tests and hints fit together.", reason_codes=["FIRST_EXERCISE"],
                        problem_id=first.id, problem_title=first.title, unit_id=first.unit_id, unit_title=first_unit.title if first_unit else None, keep_current_active=False)
    anchor = _anchor(data)
    if anchor and not _unit_ready(anchor):
        step = _step_in_topic(data, anchor, None, intro=f"You have been working in {anchor.title}. ")
        if step:
            return step.model_copy(update={"action": "start_path", "reason_codes": ["CONTINUE_TOPIC", *step.reason_codes]})
    following = _next_unit(data, anchor)
    if following:
        first = _sequence_next(data, following, None)[0] or _pick(data, following.id, None, target_difficulty=0)
        if first:
            reason = f"{following.title} is the next topic with room to grow, based on your work and goals so far."
            return _out(data, following, action="start_path", title=f"Next: {first.title}", reason=reason, reason_codes=["NEXT_IN_PATH"], problem_id=first.id, problem_title=first.title,
                        unit_id=following.id, unit_title=following.title, keep_current_active=False)
    return _out(data, anchor, action="review_concept", title="Explore any topic you like", reason="There is no specific recommendation right now.", reason_codes=["NOTHING_LEFT"], keep_current_active=False)


def after_reflection(data: PlannerInput, quality: str) -> PlanOutput | None:
    """A solved problem whose reflection answer was unsure gets one more problem of the same technique before moving on.

    Only an honest "not sure" changes the plan. A clear, partial or short answer leaves the plan already shown as it
    was: a short answer is asked for a little more in the reply, which is not evidence that the idea is unsettled.
    An unsolved problem stays the current task.
    """
    current = data.current_problem
    unit = _unit(data, current.unit_id) if current else None
    if not (current and unit and data.solved_now) or quality != "unsure":
        return None
    practice = _pick(data, unit.id, current.id, target_difficulty=_rank(current), pattern=current.pattern)
    if not practice:
        return None
    technique = (current.pattern or "the same idea").lower()
    return _out(data, unit, action="similar_independent", title=f"Before moving on, try {practice.title}",
                reason=f"You solved it, and your answer suggests the idea is not fully settled yet. One more {technique} problem at the same level will help it stick.",
                reason_codes=["REFLECTION_UNSURE"], problem_id=practice.id, problem_title=practice.title, unit_id=unit.id, unit_title=unit.title, keep_current_active=False)
