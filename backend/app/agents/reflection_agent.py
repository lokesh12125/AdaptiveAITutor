"""Reflection Agent for formulating metacognitive self-explanation questions and learning feedback."""
from typing import Any, Dict

from ..graph.state import TutorState
from ..services.llm_service import llm


class ReflectionAgent:
    """Agent responsible for formulating targeted metacognitive questions prompting students

    to analyze invariants, Big-O complexity (on success), or mental trace divergence (on error).
    """

    def execute(self, state: TutorState) -> Dict[str, Any]:
        """Generate metacognitive reflection prompt for the student."""
        execution = state.get("execution", {})
        passed = execution.get("passed", False)
        problem = state.get("problem", {})
        code = state.get("code", "")
        diagnostic_info = state.get("diagnostic", {})

        if passed:
            fallback_prompt = (
                f"Excellent! Your solution for '{problem.get('title', '')}' passed all tests. "
                "In one sentence, explain what the core invariant of your approach was, and what its time complexity is."
            )
            sys_prompt = (
                "You are a thoughtful tutor encouraging meta-cognitive reflection. "
                "Formulate one insightful question asking the student to explain why their working code is sound or analyze its Big-O complexity."
            )
            prompt = (
                f"Problem: {problem.get('title', '')}\n"
                f"Passing Code:\n{code[:400]}\n"
                "Generate a reflective post-solution question."
            )
        else:
            misconception = diagnostic_info.get("misconception", "the logic error")
            fallback_prompt = (
                f"Before resubmitting, compare the expected test output against your code's behavior. "
                f"Where did your step-by-step mental trace diverge regarding {misconception}?"
            )
            sys_prompt = (
                "You are a reflective programming tutor. "
                "Formulate one targeted question prompting the student to compare their mental model against the observed error."
            )
            prompt = (
                f"Problem: {problem.get('title', '')}\n"
                f"Error: {diagnostic_info.get('output', '')}\n"
                f"Misconception: {misconception}\n"
                "Generate a reflection question."
            )

        reflection_text = llm.tutor_reply(prompt, fallback_prompt, system_prompt=sys_prompt)

        return {
            "reflection": reflection_text,
            "agent_activity": ["Reflection Agent"],
        }
