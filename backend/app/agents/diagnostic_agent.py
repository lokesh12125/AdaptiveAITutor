"""Diagnostic Agent for detecting code error types, AST syntax flaws, and semantic misconceptions."""
import ast
from typing import Any, Dict

from ..graph.state import TutorState
from ..services.llm_service import llm


class DiagnosticAgent:
    """Agent responsible for analyzing code submissions, AST structures, and execution errors

    to classify misconceptions and provide diagnostic feedback.
    """

    def detect_semantic_misconception(self, code: str, error_type: str, output: str) -> str:
        """Analyze code patterns and error messages to identify the likely conceptual misconception."""
        if error_type == "security":
            return "attempted use of restricted system module or function"
        if error_type == "none":
            return "none detected (solution verified)"
        if error_type == "timeout":
            return "infinite loop or missing loop termination condition"
        if error_type == "recursion":
            return "infinite recursion due to missing or unreachable base case"
        if error_type == "syntax":
            if "colon" in output.lower() or ":" not in code:
                return "missing colon syntax after control flow statement (def, if, for, while)"
            if "indent" in output.lower():
                return "inconsistent indentation or block structure"
            return "syntax structure or unmatched parenthesis/bracket"

        # For Assertion or Runtime errors, inspect AST
        try:
            tree = ast.parse(code)
            # Check if function returns inside a loop on the first iteration
            for node in ast.walk(tree):
                if isinstance(node, (ast.For, ast.While)):
                    for child in node.body:
                        if isinstance(child, ast.Return):
                            return "premature return inside loop body on the first iteration"
            # Check if function has no return statement
            has_return = any(isinstance(node, ast.Return) for node in ast.walk(tree))
            if not has_return:
                return "missing return statement (function returns None)"
        except Exception:
            pass

        if "IndexError" in output:
            return "off-by-one or out-of-bounds sequence indexing"
        if "TypeError" in output:
            return "type incompatibility or unsupported operand types"
        if "KeyError" in output:
            return "dictionary key lookup without verifying presence"
        if "ZeroDivisionError" in output:
            return "division by zero on boundary value"
        if "AssertionError" in output:
            return "logical discrepancy between computed result and expected behavior"

        return "control flow or edge-case handling"

    def execute(self, state: TutorState) -> Dict[str, Any]:
        """Execute diagnostic analysis on the code submission state."""
        execution = state.get("execution", {})
        error_type = execution.get("error_type", "none")
        output = execution.get("output", "")
        code = state.get("code", "")
        problem = state.get("problem", {})

        misconception = self.detect_semantic_misconception(code, error_type, output)
        severity = (
            "low"
            if error_type == "none"
            else ("high" if error_type in ("security", "timeout", "recursion") else "medium")
        )

        default_explanations = {
            "none": "Your solution passed all automated test assertions.",
            "syntax": f"Python syntax error encountered: {output}. Review punctuation, colons, and indentation.",
            "assertion": f"Assertion check failed. {output}. The returned value differed from the expected output.",
            "timeout": "Execution timed out. Review while/for loop conditions to ensure loop termination.",
            "recursion": "Maximum recursion depth exceeded. Verify that your base case is reachable.",
            "security": f"Security restriction: {output}",
            "runtime": f"Runtime exception: {output}. Trace variable values leading up to the failure.",
        }
        fallback_expl = default_explanations.get(error_type, f"Error encountered: {output}")

        # LLM diagnostic enrichment if in live mode
        prompt = (
            f"Problem: {problem.get('title', '')} - {problem.get('description', '')}\n"
            f"Student Code:\n{code[:600]}\n"
            f"Execution Outcome: {error_type} - {output}\n"
            f"Identified Misconception: {misconception}\n"
            "Provide a concise, 1-2 sentence diagnostic diagnosis pointing out the conceptual flaw without writing the code fix."
        )
        explanation = llm.tutor_reply(prompt, fallback_expl)

        # R-03: Longitudinal misconception tracking per learner
        learner_id = state.get("learner_id", "demo-student")
        concept_id = state.get("concept_id") or problem.get("concept_id") or "variables"
        if error_type != "none" and misconception and "none" not in misconception.lower():
            try:
                from ..database import record_learner_misconception
                record_learner_misconception(
                    learner_id=learner_id,
                    concept_id=concept_id,
                    misconception_code=misconception,
                    error_type=error_type
                )
            except Exception:
                pass

        return {
            "diagnostic": {
                "error_type": error_type,
                "explanation": explanation,
                "misconception": misconception,
                "severity": severity,
                "output": output,
            },
            "agent_activity": ["Diagnostic Agent"],
        }
