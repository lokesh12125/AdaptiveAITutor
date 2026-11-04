"""Adaptive Scaffolding Agent for calculating scaffolding levels (1-4) and generating Socratic hints."""
from typing import Any, Dict

from ..database import get_problem_hints, save_hint
from ..graph.state import TutorState
from ..learning.scaffolding import evaluate_dsda_v2, FALLBACK_MATRIX
from ..services.llm_service import llm


class AdaptiveScaffoldingAgent:
    """Agent responsible for computing multi-dimensional scaffolding scores (levels 1-4),
    selecting hint templates, generating LLM Socratic prompts, and persisting hint records.
    """

    def execute(self, state: TutorState) -> Dict[str, Any]:
        """Determine appropriate scaffolding level and generate Socratic guidance hint using DSDA v2.1."""
        learner = state.get("learner_state", {})
        problem = state.get("problem", {})
        problem_id = int(problem.get("id", 1))
        learner_id = state.get("learner_id", "demo-student")
        execution = state.get("execution", {})
        passed = execution.get("passed", False)
        intervention = state.get("active_intervention", "")
        code = state.get("code", "")
        diagnostic_info = state.get("diagnostic", {})
        error_type = diagnostic_info.get("error_type", "assertion")
        misconception = diagnostic_info.get("misconception", "")

        # Fetch problem hint history
        problem_hints = get_problem_hints(learner_id, problem_id)

        # Run DSDA v2.1 decision algorithm
        decision = evaluate_dsda_v2(
            diagnostic=diagnostic_info,
            learner_state=learner,
            problem_hints=problem_hints,
            current_attempt_count=learner.get("attempts", 1),
            consecutive_fails=learner.get("problem_consecutive_fails", learner.get("consecutive_fails", 0)),
            response_time=float(state.get("response_time", 0.0)),
            baseline_time=float(learner.get("baseline_time", 60.0)),
            observations_count=learner.get("attempts", 1),
            code=code,
            passed=passed
        )

        level = decision["level"]
        focus = decision["focus"]
        csi_score = decision["csi"]
        remediation_flag = decision["remediation_flag"]
        rationale = decision["rationale"]

        if level == 0 or passed:
            return {
                "scaffolding": {
                    "level": 0,
                    "score": 0.0,
                    "hint": "All test assertions passed successfully! Great work.",
                    "focus": "None",
                    "remediation_flag": False,
                    "rationale": "Solution passed all assertions."
                },
                "agent_activity": ["Adaptive Scaffolding Agent"]
            }

        # Select deterministic fallback template for (level, focus)
        fallback_hint = FALLBACK_MATRIX.get(
            (level, focus),
            f"Inspect your logic around {misconception or 'the return statement'}. Review: {problem.get('expected_behavior', '')}."
        )

        leak_detected = state.get("leak_detected", False)
        anti_leak_instruction = (
            "CRITICAL WARNING: Direct code was previously detected. Under NO circumstances output executable Python syntax, complete functions, or code blocks. Use ONLY conceptual questioning."
            if leak_detected
            else "Do NOT write the complete solution code."
        )

        prompt = (
            f"Problem: {problem.get('title', '')} - {problem.get('description', '')}\n"
            f"Expected Behavior: {problem.get('expected_behavior', '')}\n"
            f"Student's Code:\n{code[:400]}\n"
            f"Error Encountered: {error_type} - {diagnostic_info.get('output', '')}\n"
            f"Identified Misconception: {misconception}\n"
            f"Scaffolding Level: Level {level} of 4\n"
            f"Pedagogical Focus: {focus}\n"
            f"Intervention Cue: {intervention}\n"
            f"Rationale: {rationale}\n"
            f"Generate a targeted Level {level} Socratic hint focusing on {focus} (Level 1=guiding question, Level 2=conceptual clue, Level 3=pseudocode guidance, Level 4=step-by-step breakdown). "
            f"{anti_leak_instruction}"
        )
        hint_text = llm.tutor_reply(prompt, fallback_hint)

        # Persist hint to SQLite
        try:
            save_hint(
                learner_id=learner_id,
                problem_id=problem_id,
                level=level,
                hint_text=hint_text,
                focus=focus
            )
        except Exception:
            pass

        return {
            "scaffolding": {
                "level": level,
                "score": round(csi_score, 2),
                "hint": hint_text,
                "focus": focus,
                "remediation_flag": remediation_flag,
                "rationale": rationale,
                "intervention_applied": intervention,
                "llm_mode": "fallback" if getattr(llm, "last_was_fallback", True) else "live",
            },
            "agent_activity": ["Adaptive Scaffolding Agent"],
        }
