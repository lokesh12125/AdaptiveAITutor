"""Dynamic Scaffolding Decision Algorithm: deterministic and configurable.

The report names DSDA and its purpose but gives no formula, levels or thresholds. The score,
ladder and rules here are this project's proposal, with starting values in policy.yaml. The LLM never runs
in this module and cannot change its decision. See docs/dsda.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .contracts import DSDADecision, Presentation

POLICY = yaml.safe_load((Path(__file__).parent / "policy.yaml").read_text())["dsda"]

LEVEL_NAMES = {
    0: "Independent attempt",
    1: "Conceptual question",
    2: "Targeted hint",
    3: "Step-by-step outline",
    4: "Analogous worked example",
}
LEVEL_FROM_LABEL = {"low": 0.2, "moderate": 0.55, "high": 0.9}


@dataclass
class DSDAInput:
    trigger: str  # submission | hint_request
    request_size: str | None  # nudge | more | None
    category: str
    issue_key: str
    repeat_count: int
    mastery: float
    mastery_evidence: float
    confidence: float | None
    confusion: str | None
    load: str | None
    progress: str
    last_level_on_issue: int = 0
    last_level_any: int = 0
    last_hint_issue: str | None = None
    hints_on_issue: int = 0
    hints_without_progress_on_issue: int = 0
    attempts_on_problem: int = 0
    retrieval: dict[str, Any] | None = None
    auto_hints: bool = True
    policy: dict[str, Any] | None = None


def need_score(data: DSDAInput, policy: dict[str, Any]) -> tuple[float, dict[str, float]]:
    weights = policy["weights"]
    # Hints alone never raise the score: only hints that were not followed by progress do.
    inputs: dict[str, float | None] = {
        "low_mastery": 1 - data.mastery if data.mastery_evidence > 0 else 0.5,
        "low_confidence": 1 - data.confidence if data.confidence is not None else None,
        "confusion": LEVEL_FROM_LABEL.get(data.confusion) if data.confusion else None,
        "cognitive_load": LEVEL_FROM_LABEL.get(data.load) if data.load else None,
        "repeated_issue": min(1.0, max(0, data.repeat_count - 1) / 3),
        "unhelpful_hints": min(1.0, data.hints_without_progress_on_issue / 2),
    }
    known = {k: v for k, v in inputs.items() if v is not None}
    total_weight = sum(weights[k] for k in known) or 1.0
    components = {k: round(weights[k] * v / total_weight, 3) for k, v in known.items()}
    score = sum(components.values())
    if data.progress == "improving":
        score -= policy["progress_credit"]
        components["progress_credit"] = -policy["progress_credit"]
    return round(max(0.0, min(1.0, score)), 3), components


def level_from_score(score: float, thresholds: list[float]) -> int:
    for level, limit in enumerate(thresholds):
        if score < limit:
            return level
    return 4


def strategy_for(category: str, issue_key: str, level: int) -> str:
    if category == "syntax":
        return "syntax_pinpoint"
    if level == 0:
        return "none"
    if category == "runtime":
        return "error_tracing"
    if category in ("timeout", "memory", "output_limit"):
        return "termination_reasoning"
    if issue_key in ("logic:missing_return", "logic:print_instead_of_return", "logic:returned_none_on_path"):
        return "return_value"
    if issue_key == "logic:not_implemented":
        return "getting_started"
    if issue_key == "logic:early_return_in_loop":
        return "control_flow"
    if issue_key in ("logic:off_by_one", "logic:edge_case"):
        return "boundary_check"
    return {1: "conceptual_question", 2: "trace_example", 3: "step_outline", 4: "analogous_example"}.get(level, "trace_example")


def _presentation(level: int, load: str | None, policy: dict[str, Any]) -> Presentation:
    if level == 0:
        return Presentation(format="none", max_sentences=0, max_words=0)
    base = policy["presentation"][str(level)]
    presentation = Presentation(
        format=base["format"], max_sentences=base["max_sentences"], max_words=base["max_words"],
        allow_code="analogous_only" if level == 4 else "none",
    )
    if load == "high":
        cap = policy["presentation"]["high_load"]
        presentation.max_sentences = min(presentation.max_sentences, cap["max_sentences"])
        presentation.max_words = min(presentation.max_words, cap["max_words"])
        presentation.one_action = True
        if level == 3:
            presentation.format = "hint"
    return presentation


REASONS = {
    "SOLVED": "All tests pass, so no help is needed.",
    "NO_EVIDENCE": "There is no result to base help on yet.",
    "EXPLICIT_REQUEST": "You asked for help.",
    "SMALL_REQUEST": "You asked for a small nudge, so this stays brief.",
    "MORE_REQUEST": "You asked for more detail than the last hint gave.",
    "FIRST_CONTACT": "This is the first time this issue has come up, so the help starts small.",
    "SYNTAX_PRECISE": "This is a syntax issue, so the help points at the exact spot.",
    "ESCALATE_NO_PROGRESS": "The last hint on this issue did not lead to progress, so this one gives more support.",
    "REPEATED_ISSUE": "The same issue has appeared in several attempts.",
    "FADE_PROGRESS": "You are making progress, so the help is lighter this time.",
    "PROGRESS_NO_HELP": "You are making progress, so the tutor is staying out of your way.",
    "HIGH_LOAD_CONCISE": "This looks like a lot right now, so here is just one thing to try.",
    "OFFER_INDEPENDENT": "You have done well on this topic, so you may like to try again before getting a hint.",
    "AUTO_HINTS_OFF": "Automatic hints are off in your settings, so help waits until you ask.",
    "RETRIEVAL_ADJUSTED": "A similar situation was helped by this kind of support.",
    "RETRIEVAL_ADJUSTED_DEMO": "Demo records of a similar situation suggest this kind of support.",
    "LOW_NEED": "Your recent work suggests a light touch is enough.",
    "SUPPORT_NEEDED": "Your recent attempts suggest a bit more support would help.",
    "SERVICE_UNAVAILABLE": "We could not check your code, so there is nothing to base a hint on yet.",
}
ISSUE_FOCUS = {
    "logic:early_return_in_loop": "when your loop should return, because your function returned before processing every value",
    "logic:off_by_one": "where your loop or range starts and stops, because answers differ by exactly one",
    "logic:missing_return": "how your function hands back its result, because it currently returns nothing",
    "logic:print_instead_of_return": "the difference between printing and returning, because your function prints its result",
    "logic:edge_case": "inputs the examples do not show, because the visible examples pass and other tests do not",
    "logic:wrong_return_type": "the kind of value your function returns, because it does not match the task",
    "logic:wrong_order": "the order of your result, because the items are right but the order is not",
    "logic:not_implemented": "how to begin, because the function body is still empty",
    "timeout:loop_no_progress": "how your loop stops, because it ran until the time limit",
    "timeout:recursion_no_base": "when your recursion stops, because it ran until the limit",
    "timeout:general": "how long your approach takes, because a test hit the time limit",
}


def _reason_text(codes: list[str], issue_key: str, repeat_count: int, category: str) -> str:
    focus = ISSUE_FOCUS.get(issue_key)
    if focus and repeat_count >= 2:
        lead = f"This focuses on {focus}, and the same issue appeared in {repeat_count} attempts."
    elif focus:
        lead = f"This focuses on {focus}."
    elif category == "runtime":
        lead = "This focuses on the error Python reported when your code ran."
    elif category == "syntax":
        lead = "This focuses on the place Python could not read."
    else:
        lead = ""
    extras = [REASONS[c] for c in codes if c in ("SMALL_REQUEST", "MORE_REQUEST", "ESCALATE_NO_PROGRESS", "FADE_PROGRESS", "HIGH_LOAD_CONCISE", "RETRIEVAL_ADJUSTED", "RETRIEVAL_ADJUSTED_DEMO")]
    text = " ".join(part for part in [lead, *extras] if part)
    if text:
        return text
    for code in codes:
        if code in REASONS:
            return REASONS[code]
    return "This level of help fits your recent work."


def decide(data: DSDAInput) -> DSDADecision:
    policy = data.policy or POLICY
    version = policy["policy_version"]

    def result(action: str, level: int, timing: str, codes: list[str], score: float | None = None,
               components: dict[str, float] | None = None, used_retrieval: bool = False, strategy: str | None = None) -> DSDADecision:
        return DSDADecision(
            action=action, level=level, level_name=LEVEL_NAMES[level], strategy=strategy or strategy_for(data.category, data.issue_key, level),
            focus_issue=data.issue_key, timing=timing, presentation=_presentation(level, data.load, policy),
            reason_codes=codes, reason_student=_reason_text(codes, data.issue_key, data.repeat_count, data.category),
            score=score, score_components=components or {}, used_retrieval=used_retrieval, policy_version=version,
        )

    if data.category == "accepted":
        return result("none", 0, "not_needed", ["SOLVED"], strategy="none")
    if data.category == "service_failure":
        return result("wait", 0, "wait_for_learner", ["SERVICE_UNAVAILABLE"], strategy="none")
    if data.category in ("no_tests", "cancelled"):
        return result("wait", 0, "wait_for_learner", ["NO_EVIDENCE"], strategy="none")

    explicit = data.trigger == "hint_request"
    score, components = need_score(data, policy)
    level = level_from_score(score, policy["level_thresholds"])
    codes: list[str] = ["EXPLICIT_REQUEST"] if explicit else []
    codes.append("SUPPORT_NEEDED" if level >= 2 else "LOW_NEED")

    same_issue = data.last_level_on_issue > 0
    no_progress_after_hint = same_issue and data.hints_without_progress_on_issue > 0 and data.progress != "improving"

    if data.progress == "improving" and same_issue:
        level = min(level, max(data.last_level_on_issue - 1, 0))
        codes.append("FADE_PROGRESS")
    elif no_progress_after_hint:
        # Repetition without progress: move up one rung, even when the score alone would not.
        level = max(level, data.last_level_on_issue + 1)
        codes.append("ESCALATE_NO_PROGRESS")
    elif data.repeat_count >= 2 and not same_issue:
        level = max(level, 2)
        codes.append("REPEATED_ISSUE")

    if explicit and data.request_size == "more":
        level = max(level, data.last_level_on_issue + 1, 1)
        codes.append("MORE_REQUEST")

    used_retrieval = False
    retrieval_strategy = None
    evidence = data.retrieval or {}
    if (
        evidence.get("reliable")
        and evidence.get("suggested_level")
        and (evidence.get("support") or 0) >= policy["retrieval_min_support"]
        and (evidence.get("effectiveness") or 0) >= policy["retrieval_min_effectiveness"]
        and data.category != "syntax"
        and level > 0
    ):
        shift = policy["retrieval_max_level_shift"]
        adjusted = max(level - shift, min(level + shift, int(evidence["suggested_level"])))
        if adjusted != level or evidence.get("suggested_strategy"):
            used_retrieval = True
            level = adjusted
            retrieval_strategy = evidence.get("suggested_strategy")
            codes.append("RETRIEVAL_ADJUSTED_DEMO" if evidence.get("provenance") == "synthetic" else "RETRIEVAL_ADJUSTED")

    # Hard limits come last, so nothing above can break them.
    level = min(level, 4)
    if same_issue:
        level = min(level, data.last_level_on_issue + 1)
    else:
        if level > policy["first_contact_max_level"]:
            level = policy["first_contact_max_level"]
        codes.append("FIRST_CONTACT")
    prior_events = data.hints_on_issue + max(0, data.repeat_count - 1)
    if level >= 3 and prior_events < policy["l3_min_prior_events"]:
        level = 2
    if level == 4 and data.hints_without_progress_on_issue < policy["l4_min_unhelpful_hints"]:
        level = 3
    if data.category == "syntax":
        level = min(max(level, 2), policy["syntax_max_level"])
        codes.append("SYNTAX_PRECISE")
    if data.load == "high":
        level = min(level, policy["high_load_max_level"])
        codes.append("HIGH_LOAD_CONCISE")
    if explicit:
        level = max(level, policy["explicit_request_floor"])
        if data.request_size == "nudge":
            level = min(level, policy["small_request_max_level"])
            codes.append("SMALL_REQUEST")

    strategy = retrieval_strategy if retrieval_strategy and data.category not in ("syntax",) else None

    if explicit:
        return result("give_help", level, "show_now", codes, score, components, used_retrieval, strategy)

    # Help nobody asked for must clear a higher bar. Syntax errors are the exception, since a precise pointer costs little.
    if level == 0:
        if data.progress == "improving":
            codes.append("PROGRESS_NO_HELP")
        return result("offer_help", 1, "offer", codes, score, components, False)
    if not data.auto_hints:
        codes.append("AUTO_HINTS_OFF")
        return result("offer_help", level, "offer", codes, score, components, used_retrieval, strategy)
    if data.progress == "improving" and data.category != "syntax":
        codes.append("PROGRESS_NO_HELP")
        return result("offer_help", level, "offer", codes, score, components, used_retrieval, strategy)
    first_failure = data.attempts_on_problem <= 1 and data.repeat_count <= 1
    if first_failure and data.category != "syntax" and data.mastery >= policy["offer_only_mastery"] and data.mastery_evidence >= 2:
        codes.append("OFFER_INDEPENDENT")
        return result("offer_help", level, "offer", codes, score, components, used_retrieval, strategy)
    return result("give_help", level, "show_now", codes, score, components, used_retrieval, strategy)
