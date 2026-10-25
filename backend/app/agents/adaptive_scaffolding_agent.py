"""Adaptive Scaffolding Agent for calculating scaffolding levels (1-4) and generating Socratic hints."""
from typing import Any, Dict

from ..database import save_hint
from ..graph.state import TutorState
from ..learning.scaffolding import (
    calculate_scaffolding_score,
    determine_scaffolding_level,
)
from ..services.llm_service import llm


class AdaptiveScaffoldingAgent:
    """Agent responsible for computing multi-dimensional scaffolding scores (levels 1-4),

    selecting hint templates, generating LLM Socratic prompts, and persisting hint records.
    """

    def execute(self, state: TutorState) -> Dict[str, Any]:
        """Determine appropriate scaffolding level and generate Socratic guidance hint."""
        learner = state.get("learner_state", {})
        problem = state.get("problem", {})
        intervention = state.get("active_intervention", "")
        code = state.get("code", "")
        diagnostic_info = state.get("diagnostic", {})
        error_type = diagnostic_info.get("error_type", "assertion")
        misconception = diagnostic_info.get("misconception", "")

        # Calculate Scaffolding Level (1 to 4)
        mastery = learner.get("mastery", 0.2)
        confidence = learner.get("confidence", 0.5)
        confusion = learner.get("confusion", 0.0)
        cognitive_load = learner.get("cognitive_load", 0.0)
        hints_used = learner.get("hints_used", 0)
        response_time = learner.get("response_time", 0.0)

        hint_dependence = min(hints_used / 3.0, 1.0)
        time_stress = min(response_time / 60.0, 1.0)

        score = calculate_scaffolding_score(
            mastery,
            confidence,
            confusion,
            cognitive_load,
            hint_dependence,
            time_stress,
        )
        level = determine_scaffolding_level(score)

        level_templates = {
            1: f"What happens if you trace this function on the smallest valid input? Notice the requirement: {problem.get('expected_behavior', '')}.",
            2: f"Check your assumptions regarding {misconception}. Strategy: {intervention}",
            3: f"Inspect the return value and loop boundary. Intervention cue: {intervention}. Trace each iteration step-by-step.",
            4: f"Structure guidance: 1. Initialize result accumulator. 2. Iterate carefully over input. 3. Ensure proper return statement outside loop. Note: {intervention}",
        }
        fallback_hint = level_templates.get(level, level_templates[2])

        prompt = (
            f"Problem: {problem.get('title', '')} - {problem.get('description', '')}\n"
            f"Student's Code:\n{code[:400]}\n"
            f"Error Encountered: {error_type} - {diagnostic_info.get('output', '')}\n"
            f"Identified Misconception: {misconception}\n"
            f"Pedagogical Intervention Strategy: {intervention}\n"
            f"Generate a Level {level} Socratic hint (Level 1=guiding question, Level 2=conceptual clue, Level 3=pseudocode guidance, Level 4=step-by-step breakdown). "
            "Do NOT write the complete solution code."
        )
        hint_text = llm.tutor_reply(prompt, fallback_hint)

        # Persist hint to SQLite
        try:
            save_hint(
                learner_id=state.get("learner_id", "demo-student"),
                problem_id=problem.get("id", 1),
                level=level,
                hint_text=hint_text,
            )
        except Exception:
            pass

        return {
            "scaffolding": {
                "level": level,
                "score": round(score, 2),
                "hint": hint_text,
                "intervention_applied": intervention,
            },
            "agent_activity": ["Adaptive Scaffolding Agent"],
        }
