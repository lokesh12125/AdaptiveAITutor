"""Turns internal agent outputs into one coordinated message, so the learner never sees six voices.

Order follows the results design: what happened, the next useful action, then tests and detail on request.
Private reasoning, prompts, hidden tests, reference solutions and other learners' data never appear here.
"""
from __future__ import annotations

from typing import Any

from ..models import Hint, PipelineRun, Reflection

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


def _next_action(verdict: str, decision: dict[str, Any], plan: dict[str, Any], solved: bool, has_hint: bool, has_reflection: bool) -> dict[str, Any]:
    if solved:
        return {"kind": "next_problem", "label": plan["title"], "detail": plan["reason"], "problem_id": plan.get("problem_id")}
    if plan.get("action") == "practise_prerequisite":
        return {"kind": "next_problem", "label": plan["title"], "detail": plan["reason"], "problem_id": plan.get("problem_id")}
    if verdict == "no_tests":
        return {"kind": "edit_tests", "label": "Add or enable a test", "detail": "Tests are needed before your code can be checked.", "problem_id": None}
    if verdict == "public_passed":
        return {"kind": "submit", "label": "Submit when you are ready", "detail": "Submitting checks your code on all the tests.", "problem_id": None}
    if has_hint:
        return {"kind": "try_hint", "label": "Try the hint, then run your code again", "detail": "The tutor will wait until you are ready.", "problem_id": None}
    if decision.get("action") == "offer_help":
        return {"kind": "try_again", "label": "Have another go, or ask for a hint", "detail": "The hint is there if you want it.", "problem_id": None}
    return {"kind": "try_again", "label": "Have another go", "detail": "", "problem_id": None}


def tutor_response(state: dict[str, Any], run: PipelineRun, hint_row: Hint | None, reflection_row: Reflection | None) -> dict[str, Any]:
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
    tutor = None
    if hint_row is not None:
        hint = state.get("hint") or {}
        tutor = {
            "hint_id": hint_row.id, "level": decision["level"], "level_name": decision["level_name"], "format": decision["presentation"]["format"],
            "text": hint_row.text, "source": hint_row.source, "source_note": BUILT_IN_NOTES.get(hint.get("built_in_reason")),
            "why": decision["reason_student"], "one_action": decision["presentation"]["one_action"],
        }
    return {
        "verdict": verdict,
        "what_happened": {"title": title, "detail": detail},
        "next_action": _next_action(verdict, decision, plan, solved, hint_row is not None, reflection_row is not None),
        "tutor": tutor,
        "offer": {"label": "Get a hint", "why": decision["reason_student"]} if decision.get("action") == "offer_help" else None,
        "diagnostics": {
            "category": diag["category"], "issue_key": diag["issue_key"],
            "facts": [{"text": f["text"], "line": f.get("line"), "source": f["source"]} for f in diag.get("facts", [])],
            "possible_causes": [{"text": i["misconception"], "confidence": i["confidence"]} for i in diag.get("inferences", [])],
            "lines": diag.get("affected_lines", []), "uncertain": diag.get("uncertain", False),
        },
        "reflection": {"id": reflection_row.id, "prompt": reflection_row.prompt} if reflection_row is not None else None,
        "plan": {
            "action": plan["action"], "title": plan["title"], "reason": plan["reason"], "problem_id": plan.get("problem_id"), "problem_title": plan.get("problem_title"),
            "unit_id": plan.get("unit_id"), "unit_title": plan.get("unit_title"), "keep_current_active": plan.get("keep_current_active", True), "alternatives": plan.get("alternatives", []),
        },
        "estimates": {
            "unit_id": cog["unit_id"], "mastery_low": mastery["low"], "mastery_high": mastery["high"], "mastery_band": mastery["band"], "mastery_note": mastery["explanation"],
            "progress": cog.get("progress"), "progress_notes": cog.get("progress_evidence", []), "confusion": cog.get("confusion"), "confusion_notes": cog.get("confusion_evidence", []),
            "load": cog.get("cognitive_load"), "load_notes": cog.get("load_evidence", []), "confidence": cog.get("confidence"),
        },
        "retrieval_used": bool(decision.get("used_retrieval")),
        "retrieval_demo_data": bool((state.get("retrieval") or {}).get("provenance") in ("synthetic", "mixed") and decision.get("used_retrieval")),
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
        "tutor": None, "offer": None,
        "diagnostics": {"category": "service_failure" if failed else "cancelled", "issue_key": verdict, "facts": [], "possible_causes": [], "lines": [], "uncertain": False},
        "reflection": None,
        "plan": {"action": "continue_current", "title": f"Stay on {problem['title']}", "reason": "Nothing has changed.", "problem_id": problem["id"], "problem_title": problem["title"],
                 "unit_id": problem["unit_id"], "unit_title": None, "keep_current_active": True, "alternatives": []},
        "estimates": None, "retrieval_used": False, "retrieval_demo_data": False, "snapshot_id": run.snapshot_id, "graded": False,
    }
