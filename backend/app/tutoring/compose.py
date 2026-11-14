"""Turns internal agent outputs into one coordinated message, so the learner never sees six voices.

Order follows the results design: what happened, the next useful action, then tests and detail on request.
Private reasoning, prompts, hidden tests, reference solutions and other learners' data never appear here.
"""
from __future__ import annotations

from typing import Any

from ..models import Hint, PipelineRun, Reflection
from .dsda import STRATEGY_LABELS
from .questions import CONCEPT_NOTES

VERDICT_TITLES = {
    "accepted": "All tests passed",
    "partial": "Partly correct",
    "wrong_answer": "Not quite yet",
    "syntax_error": "Syntax error",
    "runtime_error": "Your code stopped with an error",
    "timeout": "Your code took too long",
    "memory_limit": "Your code used too much memory",
    "output_limit": "Your code printed too much",
    "missing_function": "Function not found",
    "public_passed": "Visible examples pass",
    "no_tests": "Nothing to check against yet",
    "service_failure": "We could not check your code",
    "cancelled": "Check cancelled",
}
LOAD_WORDS = {"low": "Low", "moderate": "Moderate", "high": "High"}
BUILT_IN_NOTES = {
    "model_unavailable": "AI wording is unavailable right now, so this is a standard hint chosen by the same rules.",
    "validation_fallback": "This is a standard hint chosen by the same rules.",
    "no_model_configured": None,
}
# Small things to do when every kind of help for this version has been seen. Each asks the learner to act.
WAIT_ACTIONS = (
    "Change one small thing, even just a print on the line you are least sure about, and run it.",
    "Explain your code out loud, one line at a time, as if to a friend. Change the first line you cannot explain.",
    "Open Earlier help above, pick the one that made most sense, and try only that one thing.",
)


def _focus_view(diag: dict[str, Any]) -> dict[str, Any] | None:
    focus = diag.get("focus")
    return {"start": focus["start"], "end": focus["end"], "auto": focus.get("auto", False)} if focus else None


def related_topic_id(diag: dict[str, Any]) -> str | None:
    concept = (diag.get("question") or {}).get("concept")
    return CONCEPT_NOTES[concept][1] if concept in CONCEPT_NOTES else None


def progress_note(diag: dict[str, Any]) -> str | None:
    """Acknowledge observed progress. Only states what the comparison actually shows."""
    comparison = diag.get("comparison") or {}
    if not comparison.get("has_previous") or diag["category"] == "accepted":
        return None
    delta = comparison.get("tests_delta")
    if comparison.get("moved_further"):
        if comparison.get("previous_issue_key", "").startswith("syntax"):
            return "Python can read your code now, so that syntax error is fixed. There is a new thing to look at."
        if delta and delta > 0:
            return f"That change helped: {diag['tests_passed']} of {diag['tests_total']} pass now, up from {comparison.get('previous_passed')}."
        return "This version gets further than your last one, so that change helped."
    if delta and delta > 0:
        return f"That change helped: {diag['tests_passed']} of {diag['tests_total']} pass now, up from {comparison.get('previous_passed')}."
    return None


def _next_action(verdict: str, decision: dict[str, Any], plan: dict[str, Any], solved: bool, has_hint: bool, has_reflection: bool) -> dict[str, Any]:
    if solved:
        return {"kind": "next_problem", "label": plan["title"], "detail": plan["reason"], "problem_id": plan.get("problem_id")}
    if plan.get("action") == "practise_prerequisite":
        return {"kind": "next_problem", "label": plan["title"], "detail": plan["reason"], "problem_id": plan.get("problem_id")}
    if verdict == "no_tests":
        return {"kind": "edit_tests", "label": "Add or enable a test", "detail": "Tests are needed before your code can be checked.", "problem_id": None}
    if verdict == "public_passed" and decision.get("action") != "wait":
        return {"kind": "submit", "label": "Submit when you are ready", "detail": "Submitting checks your code on all the tests.", "problem_id": None}
    if has_hint:
        return {"kind": "try_hint", "label": "Try the hint, then run your code again", "detail": "The tutor will wait until you are ready.", "problem_id": None}
    if decision.get("action") == "wait" and "LADDER_EXHAUSTED" in (decision.get("reason_codes") or []):
        return {"kind": "change_code", "label": "Change something, then run it", "detail": "The tutor looks again as soon as your code changes.", "problem_id": None}
    if decision.get("action") == "offer_help":
        return {"kind": "try_again", "label": "Have another go, or ask for a hint", "detail": "The hint is there if you want it.", "problem_id": None}
    return {"kind": "try_again", "label": "Have another go", "detail": "", "problem_id": None}


def _why_details(decision: dict[str, Any], diag: dict[str, Any], cog: dict[str, Any], retrieval: dict[str, Any] | None) -> list[dict[str, str]]:
    """The evidence behind the choice, in plain words, for the learner who wants to look."""
    evidence = decision.get("evidence") or {}
    items = [{"label": "Hints already seen on this issue", "value": str(evidence.get("hints_on_issue", 0))}]
    same_code = evidence.get("same_code_hints") or 0
    if same_code:
        items.append({"label": "Of those, on this exact code", "value": str(same_code)})
    if diag.get("repeat_count", 1) >= 2:
        items.append({"label": "Attempts in a row with this issue", "value": str(diag["repeat_count"])})
    if cog.get("progress") not in (None, "unknown"):
        items.append({"label": "Recent progress", "value": str(cog["progress"]).capitalize()})
    if cog.get("confusion"):
        items.append({"label": "Signs of difficulty", "value": str(cog["confusion"]).capitalize()})
    known = diag.get("diagnosis") or {}
    # The cause stays back until the help has reached it, so opening this cannot undo the first hint.
    if known and (decision.get("selected_level") or 0) >= 2:
        items.append({"label": "What the tutor found", "value": known.get("likely_cause") or ""})
        items.append({"label": "Concept", "value": known.get("concept") or ""})
        if len(known.get("evidence") or []) > 1:
            items.append({"label": "Based on", "value": " ".join(known["evidence"][:3])})
    if retrieval and retrieval.get("reliable") and decision.get("used_retrieval"):
        source = "demo records" if retrieval.get("provenance") in ("synthetic", "mixed") else "past learners"
        items.append({"label": "Similar situations", "value": f"{retrieval.get('support')} cases from {source}. This suggests, but does not prove, what may help."})
    return items


def _diagnosis_view(diag: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any] | None:
    """What the learner may see of the diagnosis. The cause waits until the help has reached that point, so it does not undo the first hint."""
    known = diag.get("diagnosis")
    if not known:
        return None
    reached = (decision.get("selected_level") or 0) >= 2 or not known.get("name")
    view = {"error_class": known.get("error_class"), "location": known.get("location"), "confidence": known.get("confidence"), "explanation": known.get("explanation"), "evidence": (known.get("evidence") or [])[:1]}
    if reached:
        view.update({"likely_cause": known.get("likely_cause"), "concept": known.get("concept"), "evidence": known.get("evidence") or []})
    return view


def tutor_response(state: dict[str, Any], run: PipelineRun, hint_row: Hint | None, reflection_row: Reflection | None, hints_on_issue: int = 0, same_code_cycles: int = 0, distinct_hints: int = 0) -> dict[str, Any]:
    event, evaluation, diag, cog, decision, plan, context = (
        state["event"], state["evaluation"], state["diagnostic"], state["cognitive"], state["decision"], state["plan"], state["context"],
    )
    verdict = evaluation["verdict"]
    graded = event["trigger"] == "submission" and evaluation.get("kind") == "submit"
    solved = diag["category"] == "accepted" and graded
    mastery = cog["mastery"]
    imported = context["problem"].get("source_type") == "imported"
    title = VERDICT_TITLES.get(verdict, "Result")
    detail = diag["student_summary"]
    if solved and imported:
        detail = f"{detail} These are the tests saved with this imported question, not the original platform's official test suite."
    retrieval = state.get("retrieval") or {}
    why_details = _why_details(decision, diag, cog, retrieval)
    tutor = None
    if hint_row is not None:
        hint = state.get("hint") or {}
        tutor = {
            "hint_id": hint_row.id, "level": decision["selected_level"], "level_name": decision["level_name"], "format": decision["presentation"]["format"],
            "text": hint_row.text, "source": hint_row.source, "source_note": BUILT_IN_NOTES.get(hint.get("built_in_reason")),
            "why": decision["reason_student"], "why_details": why_details, "one_action_at_a_time": decision["presentation"]["one_action_at_a_time"],
            "strategy": decision["strategy"], "strategy_label": STRATEGY_LABELS.get(decision["strategy"], decision["level_name"]),
            "hint_number": None if decision["strategy"] == "answer_question" else hints_on_issue + 1,
            "question": (diag.get("question") or {}).get("text") or None, "focus": _focus_view(diag), "topic_id": related_topic_id(diag) or context["problem"].get("unit_id"),
            # The idea this hint is about. Naming the concept never gives away the fix.
            "concept": ((diag.get("question") or {}).get("concept") or (diag.get("diagnosis") or {}).get("concept")) or None,
        }
    waiting = None
    if decision.get("action") == "wait" and "LADDER_EXHAUSTED" in (decision.get("reason_codes") or []):
        plural = "hint" if distinct_hints == 1 else "different hints"
        asked = diag.get("question")
        waiting = {
            "title": "That is everything I can work out from this version of your code" if asked else "You have seen all the help for this version of your code",
            "detail": ("Point at different lines, tell me what you expected to happen, or change your code, and I will look again." if asked
                       else f"That is {distinct_hints} {plural} on this issue. You can still ask about a specific line or what confuses you, and changing your code opens new help."),
            "try_next": WAIT_ACTIONS[same_code_cycles % len(WAIT_ACTIONS)],
            "snapshot_id": event["snapshot_id"],
        }
    comparison = diag.get("comparison") or {}
    return {
        "verdict": verdict,
        "what_happened": {"title": title, "detail": detail},
        "next_action": _next_action(verdict, decision, plan, solved, hint_row is not None, reflection_row is not None),
        "progress_note": progress_note(diag),
        "tutor": tutor,
        "waiting": waiting,
        # An offer after an earlier hint already invites the learner in its own words, so the card adds no second invitation.
        "offer": {"label": "Get a hint", "why": decision["reason_student"],
                  "lead": None if "OFFER_NEXT_STEP" in (decision.get("reason_codes") or []) else "You may want to try again by yourself first. A hint is here if you'd like one."}
                 if decision.get("action") == "offer_help" else None,
        "diagnostics": {
            "category": diag["category"], "issue_key": diag["issue_key"],
            "facts": [{"text": f["text"], "line": f.get("line"), "source": f["source"]} for f in diag.get("facts", [])],
            "possible_causes": [{"text": i["misconception"], "confidence": i["confidence"]} for i in diag.get("inferences", [])],
            "lines": diag.get("affected_lines", []), "uncertain": diag.get("uncertain", False), "diagnosis": _diagnosis_view(diag, decision),
            "comparison": {
                "has_previous": comparison.get("has_previous", False), "same_issue": comparison.get("same_issue", False), "changed_lines": comparison.get("changed_lines", []),
                "moved_further": comparison.get("moved_further", False), "tests_delta": comparison.get("tests_delta"),
            },
        },
        "reflection": {"id": reflection_row.id, "prompt": reflection_row.prompt} if reflection_row is not None else None,
        "plan": {
            "action": plan["action"], "title": plan["title"], "reason": plan["reason"], "problem_id": plan.get("problem_id"), "problem_title": plan.get("problem_title"),
            "unit_id": plan.get("unit_id"), "unit_title": plan.get("unit_title"), "keep_current_active": plan.get("keep_current_active", True), "alternatives": plan.get("alternatives", []),
            "route": plan.get("route", []),
        },
        "estimates": {
            "unit_id": cog["unit_id"], "mastery_low": mastery["low"], "mastery_high": mastery["high"], "mastery_band": mastery["band"], "mastery_note": mastery["explanation"],
            "progress": cog.get("progress"), "progress_notes": cog.get("progress_evidence", []), "confusion": cog.get("confusion"), "confusion_notes": cog.get("confusion_evidence", []),
            "load": cog.get("cognitive_load"), "load_notes": cog.get("load_evidence", []), "confidence": cog.get("confidence"),
        },
        "retrieval_used": bool(decision.get("used_retrieval")),
        "retrieval_demo_data": bool(retrieval.get("provenance") in ("synthetic", "mixed") and decision.get("used_retrieval")),
        "snapshot_id": event["snapshot_id"],
        "graded": graded,
    }


def unavailable_response(evaluation: dict[str, Any], problem: dict[str, Any], run: PipelineRun) -> dict[str, Any]:
    verdict = evaluation["verdict"]
    failed = verdict == "service_failure"
    return {
        "verdict": verdict,
        "what_happened": {
            "title": VERDICT_TITLES[verdict],
            "detail": ("This is a problem on our side, not with your code. Nothing was counted against you, and your code is still in the editor."
                       if failed else "You cancelled this check. Your code is still in the editor."),
        },
        "next_action": {"kind": "retry" if failed else "try_again", "label": "Try again" if failed else "Run it again when you are ready", "detail": "", "problem_id": None},
        "progress_note": None, "tutor": None, "waiting": None, "offer": None,
        "diagnostics": {"category": "service_failure" if failed else "cancelled", "issue_key": verdict, "facts": [], "possible_causes": [], "lines": [], "uncertain": False, "comparison": {}},
        "reflection": None,
        "plan": {"action": "continue_current", "title": f"Stay on {problem['title']}", "reason": "Nothing has changed.", "problem_id": problem["id"], "problem_title": problem["title"],
                 "unit_id": problem["unit_id"], "unit_title": None, "keep_current_active": True, "alternatives": []},
        "estimates": None, "retrieval_used": False, "retrieval_demo_data": False, "snapshot_id": run.snapshot_id, "graded": False,
    }
