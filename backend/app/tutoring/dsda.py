"""Dynamic Scaffolding Decision Algorithm: deterministic, configurable and aware of hint history.

The report names DSDA and its purpose but gives no formula, levels or thresholds. The score, ladders
and rules here are this project's proposal, with starting values in policy.yaml. They are experimental
choices, not validated results. The LLM never runs in this module and cannot change its decision.
See docs/dsda.md.

Two questions are answered separately:
1. How much support does this learner seem to need?  (support_need_score, from the learner's state)
2. What should that support be, given what they have already seen?  (the strategy ladder)

The second is what stops help repeating: each issue has an ordered ladder of different kinds of help,
and a step already used on that issue is not used again. When the ladder is used up on code that has
not changed, the policy says so and waits for the learner, rather than saying the same thing twice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .contracts import DSDADecision, Presentation, SolutionConstraints

POLICY = yaml.safe_load((Path(__file__).parent / "policy.yaml").read_text())["dsda"]

LEVEL_NAMES = {
    0: "Independent attempt",
    1: "Conceptual question",
    2: "Targeted hint",
    3: "Step-by-step outline",
    4: "Analogous worked example",
}
LEVEL_FROM_LABEL = {"low": 0.2, "moderate": 0.55, "high": 0.9}
STRATEGY_LABELS = {
    "conceptual_question": "A question to think about",
    "targeted_hint": "Where to look",
    "trace_failing_case": "Trace a failing case",
    "step_outline": "A step-by-step plan",
    "analogous_example": "A similar worked example",
    "syntax_pinpoint": "Where Python got stuck",
    "syntax_read_tokens": "Read the line piece by piece",
    "syntax_checklist": "A syntax checklist",
    "syntax_analogous_line": "A correct line to compare with",
    "syntax_exact_fix": "Exactly what to change",
    "print_debugging": "See what your code is doing",
    "direct_pointer": "Exactly what to change",
    "evidence_review": "Your latest change",
    "answer_question": "Answer to your question",
    "name_options": "Your options",
}
STRATEGY_LEVEL_NAMES = {"direct_pointer": "Direct pointer", "syntax_exact_fix": "Direct pointer", "answer_question": "Answer to your question"}
PROGRESS_LOOP_CATEGORIES = ("timeout", "memory", "output_limit")


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
    # Hint history, read from the database for each decision.
    used_strategies: list[str] = field(default_factory=list)  # on this issue, since the problem was last solved
    same_code_hints: int = 0  # hints already shown on this issue for this exact code
    code_changed_since_last_hint: bool = False
    moved_further: bool = False
    last_hint_helpful: bool | None = None
    last_hint_outcome: str | None = None
    seconds_since_last_hint: float | None = None
    seconds_since_last_action: float | None = None
    has_failing_example: bool = True
    has_question: bool = False  # the learner asked something specific, or pointed at their code


@dataclass(frozen=True)
class LadderStep:
    strategy: str
    level: int


def base_issue(issue_key: str) -> str:
    """The family an issue belongs to, for comparing with stored cases: runtime:NameError:missing_import is runtime:NameError."""
    return ":".join(issue_key.split(":")[:2])


def ladder_for(category: str, issue_key: str, has_failing_example: bool, policy: dict[str, Any]) -> list[LadderStep]:
    name_issue = issue_key.startswith(("runtime:NameError:", "runtime:UnboundLocalError:"))
    steps = policy["ladders"]["syntax" if category == "syntax" else "name" if name_issue else "default"]
    excluded = set(policy.get("ladder_exclude", {}).get(issue_key, []))
    if not has_failing_example:
        excluded.add("trace_failing_case")
    if category in PROGRESS_LOOP_CATEGORIES:
        excluded.add("print_debugging")  # a print inside a loop that never ends only makes things worse
    return [LadderStep(step["strategy"], step["level"]) for step in steps if step["strategy"] not in excluded]


def need_score(data: DSDAInput, policy: dict[str, Any]) -> tuple[float, dict[str, float]]:
    weights = policy["weights"]
    # Hints alone never raise the score. Hints not followed by progress do, and so does asking again with no change.
    unhelpful = data.hints_without_progress_on_issue + (1 if data.last_hint_helpful is False and data.last_hint_outcome is None else 0)
    stalled = None if data.seconds_since_last_action is None else min(1.0, data.seconds_since_last_action / policy["stalled_seconds"])
    inputs: dict[str, float | None] = {
        "low_mastery": 1 - data.mastery if data.mastery_evidence > 0 else 0.5,
        "low_confidence": 1 - data.confidence if data.confidence is not None else None,
        "confusion": LEVEL_FROM_LABEL.get(data.confusion) if data.confusion else None,
        "cognitive_load": LEVEL_FROM_LABEL.get(data.load) if data.load else None,
        "repeated_issue": min(1.0, max(0, data.repeat_count - 1) / 3),
        "unhelpful_hints": min(1.0, unhelpful / 2),
        "repeat_requests": min(1.0, data.same_code_hints / 3),
        "stalled_time": stalled,
    }
    known = {k: v for k, v in inputs.items() if v is not None}
    total_weight = sum(weights[k] for k in known) or 1.0
    components = {k: round(weights[k] * v / total_weight, 3) for k, v in known.items()}
    score = sum(components.values())
    if data.progress == "improving" or data.moved_further:
        score -= policy["progress_credit"]
        components["progress_credit"] = -policy["progress_credit"]
    return round(max(0.0, min(1.0, score)), 3), components


def level_from_score(score: float, thresholds: list[float]) -> int:
    for level, limit in enumerate(thresholds):
        if score < limit:
            return level
    return 4


def theme_for(category: str, issue_key: str) -> str:
    """What the help is about, as distinct from how it is framed. Chooses worked examples and reasons."""
    if category == "syntax":
        return "syntax"
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
    return "default"


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
        presentation.one_action_at_a_time = True
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
    "NEW_ISSUE": "This is a different issue from the last one, so the help starts again from here.",
    "SYNTAX_PRECISE": "This is a syntax issue, so the help points at the exact spot.",
    "ESCALATE_NO_PROGRESS": "The last hint on this issue did not lead to progress, so this one gives more support.",
    "ESCALATE_SAME_CODE": "You asked again about the same code, so this takes a different and more specific angle.",
    "RAPID_REREQUEST": "You asked again straight away, so this tries a different angle without skipping ahead.",
    "NUDGE_LADDER_USED": "You have already seen the small nudges for this, so this is the next step up.",
    "EVIDENCE_REVIEW": "You have seen the main kinds of help for this issue, so this looks at what your latest change did.",
    "LADDER_EXHAUSTED": "You have seen all the help available for this version of your code.",
    "QUESTION_ASKED": "You asked about this directly, so this answers your question using what your code actually did.",
    "REPEATED_ISSUE": "The same issue has appeared in several attempts.",
    "FADE_PROGRESS": "You are making progress, so the help is lighter this time.",
    "PROGRESS_NO_HELP": "You are making progress, so the tutor is staying out of your way.",
    "HIGH_LOAD_CONCISE": "This looks like a lot right now, so here is just one thing to try.",
    "OFFER_INDEPENDENT": "You have done well on this topic, so you may like to try again before getting a hint.",
    "OFFER_NEXT_STEP": "You have already had a hint on this, so try your own next idea first. The next hint is here whenever you want it.",
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
_EXPLAINED_CODES = (
    "QUESTION_ASKED", "SMALL_REQUEST", "MORE_REQUEST", "NEW_ISSUE", "ESCALATE_SAME_CODE", "RAPID_REREQUEST", "NUDGE_LADDER_USED", "ESCALATE_NO_PROGRESS",
    "EVIDENCE_REVIEW", "LADDER_EXHAUSTED", "FADE_PROGRESS", "HIGH_LOAD_CONCISE", "RETRIEVAL_ADJUSTED", "RETRIEVAL_ADJUSTED_DEMO", "OFFER_NEXT_STEP",
)


def _reason_text(codes: list[str], issue_key: str, repeat_count: int, category: str) -> str:
    focus = ISSUE_FOCUS.get(issue_key)
    if "OFFER_NEXT_STEP" in codes:
        # An offer says one thing, once: try your own idea first, and what the next hint will look at when asked for.
        return REASONS["OFFER_NEXT_STEP"] + (f" It will focus on {focus}." if focus else "")
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
    extras = [REASONS[c] for c in codes if c in _EXPLAINED_CODES]
    text = " ".join(part for part in [lead, *extras] if part)
    if text:
        return text
    for code in codes:
        if code in REASONS:
            return REASONS[code]
    return "This level of help fits your recent work."


def _choose_step(ladder: list[LadderStep], tried: set[str], floor: int, ceiling: int, prefer_lighter: bool) -> LadderStep | None:
    """The next unused step. Support rises through the ladder, unless progress means it can ease off."""
    remaining = [step for step in ladder if step.strategy not in tried and step.level <= ceiling]
    if not remaining:
        return None
    if prefer_lighter:
        lighter = [step for step in remaining if step.level <= floor]
        return lighter[-1] if lighter else remaining[0]
    return next((step for step in remaining if step.level >= floor), None)


def decide(data: DSDAInput) -> DSDADecision:
    policy = data.policy or POLICY
    version = policy["policy_version"]
    theme = theme_for(data.category, data.issue_key)
    evidence: dict[str, Any] = {
        "mastery": data.mastery, "mastery_evidence": data.mastery_evidence, "confidence": data.confidence, "confusion": data.confusion, "cognitive_load": data.load,
        "progress": data.progress, "repeat_count": data.repeat_count, "hints_on_issue": data.hints_on_issue, "same_code_hints": data.same_code_hints,
        "hints_without_progress": data.hints_without_progress_on_issue, "last_hint_helpful": data.last_hint_helpful, "last_hint_outcome": data.last_hint_outcome,
        "used_strategies": list(data.used_strategies), "code_changed_since_last_hint": data.code_changed_since_last_hint,
        "seconds_since_last_hint": data.seconds_since_last_hint, "seconds_since_last_action": data.seconds_since_last_action, "explicit_request": data.trigger == "hint_request",
        "request_size": data.request_size, "issue_key": data.issue_key, "category": data.category,
    }

    def result(action: str, level: int, timing: str, codes: list[str], strategy: str, score: float = 0.0,
               components: dict[str, float] | None = None, used_retrieval: bool = False) -> DSDADecision:
        return DSDADecision(
            action=action, selected_level=level, level_name=STRATEGY_LEVEL_NAMES.get(strategy, LEVEL_NAMES[level]), strategy=strategy, focus_issue=data.issue_key, timing=timing, theme=theme,
            presentation=_presentation(level, data.load, policy), constraints=SolutionConstraints(allow_analogous_example=level == 4), reason_codes=codes,
            reason_student=_reason_text(codes, data.issue_key, data.repeat_count, data.category), support_need_score=score, score_components=components or {},
            used_retrieval=used_retrieval, policy_version=version, evidence=evidence,
        )

    if data.category == "accepted" and not (data.trigger == "hint_request" and data.has_question):
        return result("none", 0, "not_needed", ["SOLVED"], "consolidate")
    if data.category == "service_failure":
        return result("wait", 0, "wait_for_learner", ["SERVICE_UNAVAILABLE"], "none")
    if data.category in ("no_tests", "cancelled"):
        return result("wait", 0, "wait_for_learner", ["NO_EVIDENCE"], "none")

    explicit = data.trigger == "hint_request"
    score, components = need_score(data, policy)
    score_level = level_from_score(score, policy["level_thresholds"])
    codes: list[str] = ["EXPLICIT_REQUEST"] if explicit else []
    codes.append("SUPPORT_NEEDED" if score_level >= 2 else "LOW_NEED")

    # A specific question gets a specific answer, whatever is left on the ladder. It does not use up a step,
    # and the validator still stops it repeating an earlier answer or giving away the solution.
    if explicit and data.has_question:
        codes.append("QUESTION_ASKED")
        level = min(3, max(2, data.last_level_on_issue))
        answer = result("give_help", level, "show_now", codes, "answer_question", score, components)
        settings = policy["presentation"]["question"]
        answer.presentation = Presentation(format=settings["format"], max_sentences=settings["max_sentences"], max_words=settings["max_words"], allow_code="none", one_action_at_a_time=data.load == "high")
        return answer

    ladder = ladder_for(data.category, data.issue_key, data.has_failing_example, policy)
    tried = set(data.used_strategies)
    last = data.last_level_on_issue
    same_issue = last > 0
    improving = data.progress == "improving" or data.moved_further
    same_code_repeat = same_issue and data.same_code_hints > 0
    unhelpful = data.hints_without_progress_on_issue > 0 or data.last_hint_helpful is False
    prefer_lighter = False
    wanted_unprompted = score_level

    # 1. Where on the ladder should this be, given what has happened?
    if not same_issue:
        floor = min(max(score_level, 1), policy["first_contact_max_level"])
        codes.append("FIRST_CONTACT")
        if data.last_hint_issue and data.last_hint_issue != data.issue_key:
            codes.append("NEW_ISSUE")
        if data.repeat_count >= 2:
            floor = min(max(floor, 2), policy["first_contact_max_level"])
            wanted_unprompted = max(wanted_unprompted, 2)
            codes.append("REPEATED_ISSUE")
    elif improving:
        floor = max(last - 1, 1)
        prefer_lighter = True
        wanted_unprompted = min(wanted_unprompted, max(last - 1, 0))
        codes.append("FADE_PROGRESS")
    elif same_code_repeat:
        rapid = data.seconds_since_last_hint is not None and data.seconds_since_last_hint < policy["rapid_rerequest_seconds"] and data.request_size != "more"
        floor = last if rapid else max(last, min(score_level, last + 1))
        codes.append("RAPID_REREQUEST" if rapid else "ESCALATE_SAME_CODE")
    elif unhelpful:
        # Repetition without progress: take the next step on the ladder, even when the score alone would not.
        floor = max(last, min(score_level, last + 1))
        wanted_unprompted = max(wanted_unprompted, last)
        codes.append("ESCALATE_NO_PROGRESS")
    else:
        floor = max(last, min(score_level, last + 1))
    if explicit and data.request_size == "more":
        # The next unused step, which may be at the same level. Requiring a higher level here would jump over kinds of help the learner has not seen.
        # Older hints may have no recorded strategy. Then nothing shows what was used at this level, so move up.
        seen_at_this_level = any(s.strategy in tried and s.level == last for s in ladder)
        floor = max(last if seen_at_this_level else last + 1, 1)
        prefer_lighter = False
        codes.append("MORE_REQUEST")

    # 2. Hard limits on how much help this moment allows.
    ceiling = 4
    if data.hints_on_issue + max(0, data.repeat_count - 1) < policy["l3_min_prior_events"]:
        ceiling = min(ceiling, 2)
    if data.hints_on_issue < policy["l4_min_prior_hints"]:
        ceiling = min(ceiling, 3)
    if same_issue:
        ceiling = min(ceiling, last + 1)
    else:
        ceiling = min(ceiling, policy["first_contact_max_level"])
    high_load = data.load == "high"
    if high_load:
        ceiling = min(ceiling, policy["high_load_max_level"])
    if data.category == "syntax":
        floor = max(floor, ladder[0].level)
        ceiling = max(ceiling, ladder[0].level)
        codes.append("SYNTAX_PRECISE")
    if explicit:
        floor = max(floor, policy["explicit_request_floor"])

    # 3. Similar situations may nudge the choice, only within those limits.
    used_retrieval = False
    preferred: LadderStep | None = None
    retrieved = data.retrieval or {}
    if (
        retrieved.get("reliable")
        and retrieved.get("suggested_level")
        and (retrieved.get("support") or 0) >= policy["retrieval_min_support"]
        and (retrieved.get("effectiveness") or 0) >= policy["retrieval_min_effectiveness"]
        and data.category != "syntax"
        and not prefer_lighter
        and not (explicit and data.request_size == "more")  # asking for more walks the ladder in order, so nothing is jumped over
    ):
        shift = policy["retrieval_max_level_shift"]
        adjusted = max(1, min(ceiling, max(floor - shift, min(floor + shift, int(retrieved["suggested_level"])))))
        if adjusted != floor:
            floor, used_retrieval = adjusted, True
        suggested = retrieved.get("suggested_strategy")
        preferred = next((s for s in ladder if s.strategy == suggested and s.strategy not in tried and s.level <= ceiling), None)
        if preferred is not None:
            used_retrieval = True
    if used_retrieval:
        codes.append("RETRIEVAL_ADJUSTED_DEMO" if retrieved.get("provenance") == "synthetic" else "RETRIEVAL_ADJUSTED")

    # 4. Choose a step not yet used on this issue.
    nudge = explicit and data.request_size == "nudge"
    step = preferred
    if step is None and nudge:
        step = _choose_step(ladder, tried, 1, min(ceiling, policy["small_request_max_level"]), False)
    if step is None:
        step = _choose_step(ladder, tried, floor, ceiling, prefer_lighter)
        if step is not None and nudge:
            codes.append("NUDGE_LADDER_USED")
    if step is None and ceiling < 4 and not (high_load and policy["high_load_max_level"] < 4):
        # Everything allowed so far has been used, so the next unused step up is the only new help available.
        step = _choose_step(ladder, tried, floor, 4, False)
    if step is None and same_issue and not data.code_changed_since_last_hint:
        # High need may have jumped over a step earlier. Concrete help the learner has not seen beats stopping,
        # though a conceptual question straight after a worked example would not help.
        skipped = [s for s in ladder if s.strategy not in tried and s.level >= 2 and (not high_load or s.level <= policy["high_load_max_level"])]
        step = skipped[0] if skipped else None
    if nudge and step is not None and step.level <= policy["small_request_max_level"]:
        codes.append("SMALL_REQUEST")
    if high_load:
        codes.append("HIGH_LOAD_CONCISE")
    evidence["ladder"] = [s.strategy for s in ladder]
    evidence["retrieval"] = {k: retrieved.get(k) for k in ("reliable", "suggested_level", "suggested_strategy", "support", "effectiveness", "provenance", "excluded_strategies")} if retrieved else None

    if step is None and data.code_changed_since_last_hint:
        # New evidence exists, so looking at what the change did is genuinely new help.
        codes.append("EVIDENCE_REVIEW")
        level = max(2, min(last or 2, policy["high_load_max_level"] if high_load else 4))
        strategy = "evidence_review"
    elif step is None:
        # Nothing new to say at this level of support, and going back down or repeating would not help. Wait for the learner.
        codes.append("LADDER_EXHAUSTED")
        return result("wait", 0, "wait_for_learner", codes, "await_code_change", score, components)
    else:
        level, strategy = step.level, step.strategy

    if explicit:
        return result("give_help", level, "show_now", codes, strategy, score, components, used_retrieval)

    # Help nobody asked for must clear a higher bar. Syntax errors are the exception, since a precise pointer costs little.
    if data.category != "syntax" and wanted_unprompted == 0:
        if improving:
            codes.append("PROGRESS_NO_HELP")
        return result("offer_help", level, "offer", codes, strategy, score, components, False)
    if not data.auto_hints:
        codes.append("AUTO_HINTS_OFF")
        return result("offer_help", level, "offer", codes, strategy, score, components, used_retrieval)
    if improving and data.category != "syntax":
        codes.append("PROGRESS_NO_HELP")
        return result("offer_help", level, "offer", codes, strategy, score, components, used_retrieval)
    # Like a tutor beside the learner: the first nudge on an issue comes unasked, then they get room to try.
    # More help on the same issue waits until they ask for it, so help never climbs the ladder on its own.
    if same_issue and data.hints_on_issue >= 1:
        codes.append("OFFER_NEXT_STEP")
        return result("offer_help", level, "offer", codes, strategy, score, components, used_retrieval)

    first_failure = data.attempts_on_problem <= 1 and data.repeat_count <= 1
    if first_failure and data.category != "syntax" and data.mastery >= policy["offer_only_mastery"] and data.mastery_evidence >= 2:
        codes.append("OFFER_INDEPENDENT")
        return result("offer_help", level, "offer", codes, strategy, score, components, used_retrieval)
    return result("give_help", level, "show_now", codes, strategy, score, components, used_retrieval)
