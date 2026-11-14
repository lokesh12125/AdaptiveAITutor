"""Cognitive State Agent: documented, inspectable estimates, not diagnoses.

Method cs-1.1 (see docs/agents.md):
- Mastery per topic: Bayesian Knowledge Tracing with evidence weights, so hints, syntax slips and
  repeated identical code count for less. Reported with a range that narrows as evidence grows.
- Confidence: only from the learner's own self-report. No report means unknown.
- Confusion and cognitive load: rule scores that need at least two independent signals. One failure or
  one long pause is never enough, and values stay unknown until there is evidence.
- Progress: the trend in tests passed on this problem, and whether the code now gets further than before.
- Prior attempts, hints, outcomes and earlier self-reports all come from the database. Asking again about
  unchanged code is a signal of difficulty, never of mastery, and adds no evidence of progress.

All of these are behavioural estimates from coding activity, with no medical or psychological meaning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .contracts import CognitiveOutput, MasteryEstimate

POLICY = yaml.safe_load((Path(__file__).parent / "policy.yaml").read_text())["cognitive"]


@dataclass
class AttemptView:
    verdict: str
    ratio: float
    issue_key: str
    same_code_as_previous: bool = False


@dataclass
class CognitiveInput:
    unit_id: str
    prior_mastery: float
    prior_evidence: float
    prior_version: int
    verdict: str
    category: str
    issue_key: str
    repeat_count: int
    ratio: float
    graded: bool
    same_code_as_previous: bool
    difficulty_label: str | None
    source_type: str
    attempts: list[AttemptView] = field(default_factory=list)  # prior graded attempts on this problem, oldest first
    hints_on_problem: int = 0
    max_hint_level_since_last_solve: int = 0
    hints_without_progress: int = 0
    active_seconds: int | None = None
    self_confidence: str | None = None
    self_state: str | None = None
    reflection_unsure: bool = False
    same_code_requests: int = 0  # hints already requested on this exact code
    hints_marked_unhelpful: int = 0
    prior_self_confidence: float | None = None
    code_changed: bool = False
    moved_further: bool = False
    previous_ratio_same_measure: float | None = None


def bkt_update(prior: float, correct: bool, weight: float) -> float:
    guess, slip, learn = POLICY["bkt_guess"], POLICY["bkt_slip"], POLICY["bkt_learn"]
    if correct:
        posterior = prior * (1 - slip) / (prior * (1 - slip) + (1 - prior) * guess)
    else:
        posterior = prior * slip / (prior * slip + (1 - prior) * (1 - guess))
    learned = posterior + (1 - posterior) * learn
    return prior + weight * (learned - prior)


def evidence_weight(data: CognitiveInput) -> float:
    if not data.graded or data.same_code_as_previous:
        return 0.0
    weights = POLICY["evidence_weights"]
    if data.category == "accepted":
        if data.max_hint_level_since_last_solve:
            weight = weights["solved_with_hints_by_level"][min(data.max_hint_level_since_last_solve, 4)]
        else:
            weight = weights["solved_independently"]
    elif data.category == "syntax":
        weight = weights["syntax_error"]
    elif data.category in ("timeout", "memory", "output_limit"):
        weight = weights["resource_limit"]
    elif data.category in ("runtime", "wrong_answer", "partial", "missing_function"):
        weight = weights["logic_failure"]
    else:
        return 0.0
    if data.source_type == "imported":
        weight *= weights["imported_problem_factor"]
    return weight


def mastery_estimate(value: float, evidence: float, updated: bool, explanation: str) -> MasteryEstimate:
    half_width = POLICY["range_base"] / (1 + evidence) ** 0.5
    low, high = max(0.0, value - half_width), min(1.0, value + half_width)
    if evidence < POLICY["min_evidence_for_band"]:
        band = "not_enough_evidence"
    elif value < 0.4:
        band = "starting"
    elif value < 0.65:
        band = "developing"
    elif value < 0.85:
        band = "proficient"
    else:
        band = "strong"
    return MasteryEstimate(value=round(value, 3), low=round(low, 3), high=round(high, 3), band=band,
                           evidence_weight=round(evidence, 2), updated=updated, explanation=explanation)


def _mastery_explanation(data: CognitiveInput, weight: float) -> str:
    if not data.graded:
        return "A hint request is not a graded attempt, so this estimate did not change."
    if data.same_code_as_previous:
        return "This code was already checked, so it adds no new evidence."
    if data.category == "accepted" and data.max_hint_level_since_last_solve >= 2:
        return "You solved this with help, so it counts as partial evidence of independent skill."
    if data.category == "accepted":
        return "Solving this without hints is good evidence, though one success does not prove full understanding."
    if data.category == "syntax":
        return "Syntax slips say little about understanding of the topic, so this counts only slightly."
    return "This attempt counts as evidence that the topic is still developing."


def estimate_confusion(data: CognitiveInput) -> tuple[str | None, list[str]]:
    signals: list[str] = []
    if data.repeat_count >= 2 and data.category not in ("accepted",):
        signals.append(f"The same issue appeared in {data.repeat_count} attempts in a row.")
    if data.hints_without_progress >= 1:
        signals.append("A recent hint was not followed by visible progress.")
    categories = [a.issue_key.split(":")[0] for a in data.attempts[-3:]] + [data.issue_key.split(":")[0]]
    if len(categories) >= 3 and len(set(categories)) >= 3:
        signals.append("The kind of error has been changing from attempt to attempt.")
    if data.self_state == "stuck":
        signals.append("You said you feel stuck.")
    elif data.reflection_unsure:
        signals.append("In your answer to the reflection question, you said you were not sure.")
    if data.same_code_requests >= POLICY["same_code_requests_signal"]:
        signals.append(f"You have asked for help {data.same_code_requests + 1} times on this version of your code.")
    if data.hints_marked_unhelpful >= 1:
        signals.append("You marked a recent hint as not helpful.")
    if data.category == "accepted":
        return ("low" if data.attempts else None), []
    if not data.attempts and not signals:
        return None, []  # a single failure is not evidence of confusion
    if len(signals) >= 2:
        return "high", signals
    if len(signals) == 1:
        return "moderate", signals
    return "low", ["Recent attempts do not show repeated difficulty."]


def estimate_load(data: CognitiveInput) -> tuple[str | None, list[str]]:
    baselines = POLICY["baseline_active_seconds"]
    baseline = baselines.get(data.difficulty_label or "medium", baselines["medium"])
    signals: list[str] = []
    if data.active_seconds is not None and data.active_seconds > POLICY["slow_factor"] * baseline:
        signals.append("You have been working on this for longer than is typical at this difficulty.")
    if data.hints_on_problem + (1 if not data.graded else 0) >= 3:
        signals.append("Several hints were needed on this problem.")
    recent = data.attempts[-2:]
    if len(recent) == 2 and all(a.ratio == 0 for a in recent) and data.ratio == 0 and data.category != "syntax":
        signals.append("Several attempts in a row passed no tests.")
    if data.self_state == "overwhelmed":
        signals.append("You said this feels like a lot.")
    if data.active_seconds is None and not data.attempts and data.self_state is None and not signals:
        return None, []
    if data.self_state == "overwhelmed" and signals:
        return "high", signals
    if len(signals) >= 2:
        return "high", signals
    if len(signals) == 1:
        # One long pause could equally be careful thought or a break, so it stays moderate at most.
        return "moderate", signals
    return ("low", ["Nothing recent suggests overload."]) if (data.attempts or data.active_seconds) else (None, [])


def estimate_progress(data: CognitiveInput) -> tuple[str, list[str], float | None]:
    ratios = [a.ratio for a in data.attempts]
    best = max(ratios + ([data.ratio] if data.graded else []), default=None)
    if data.category == "accepted":
        return "solved", ["All tests pass."], 1.0
    if data.moved_further:
        return "improving", ["This version gets further than the previous one before failing."], best
    if not data.graded:
        # Asking again with the same code is no evidence either way. New code can be compared on the same measure.
        if not data.code_changed or data.previous_ratio_same_measure is None:
            return "unknown", ["The code has not changed since the last check, so there is no new evidence of progress."] if data.same_code_requests else [], best
        if data.ratio > data.previous_ratio_same_measure:
            return "improving", [f"More examples pass than before ({round(data.ratio * 100)}% now)."], best
        if data.ratio < data.previous_ratio_same_measure:
            return "regressing", ["Fewer examples pass than in your previous version."], best
        return ("stalled" if data.repeat_count >= 2 else "steady"), ["The same number of examples pass as in your previous version."], best
    if not ratios:
        return "unknown", [], best
    previous_best = max(ratios)
    if data.ratio > previous_best:
        return "improving", [f"More tests pass than before ({round(data.ratio * 100)}% now)."], best
    if ratios and data.ratio < ratios[-1]:
        return "regressing", ["Fewer tests pass than in your previous attempt."], best
    if data.repeat_count >= 2:
        return "stalled", ["The same issue is repeating."], best
    if data.issue_key != data.attempts[-1].issue_key:
        return "steady", ["The issue has changed, which can be a sign of moving forward."], best
    return "steady", [], best


def run_cognitive(data: CognitiveInput) -> CognitiveOutput:
    weight = evidence_weight(data)
    correct = data.category == "accepted"
    value = bkt_update(data.prior_mastery, correct, weight) if weight > 0 else data.prior_mastery
    evidence = data.prior_evidence + weight

    confidence = None
    basis = None
    if data.self_confidence in POLICY["self_confidence_values"]:
        confidence = POLICY["self_confidence_values"][data.self_confidence]
        basis = "Your own rating on this attempt."
    elif data.prior_self_confidence is not None:
        confidence = data.prior_self_confidence
        basis = "Your most recent rating on this problem."

    confusion, confusion_evidence = estimate_confusion(data)
    load, load_evidence = estimate_load(data)
    progress, progress_evidence, best = estimate_progress(data)
    return CognitiveOutput(
        unit_id=data.unit_id,
        mastery=mastery_estimate(value, evidence, weight > 0, _mastery_explanation(data, weight)),
        confidence=confidence, confidence_basis=basis,
        confusion=confusion, confusion_evidence=confusion_evidence,
        cognitive_load=load, load_evidence=load_evidence,
        progress=progress, progress_evidence=progress_evidence, best_ratio=best,
        graded_attempts_on_problem=len(data.attempts) + (1 if data.graded else 0),
        state_version=data.prior_version + (1 if weight > 0 else 0),
        method_version=POLICY["method_version"],
        timestamp=datetime.now(UTC).isoformat(),
    )


def explain_for_student(output: dict[str, Any]) -> dict[str, Any]:
    """Plain summaries for the UI. These are estimates and are labelled as such there."""
    return {
        "confusion": output.get("confusion"),
        "cognitive_load": output.get("cognitive_load"),
        "progress": output.get("progress"),
    }
