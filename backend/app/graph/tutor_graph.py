"""Six-agent LangGraph orchestration with dedicated agent instances, cyclic anti-leak verifier, conditional routing, BKT mastery, and adaptive planning."""
from langgraph.graph import END, START, StateGraph

from .state import TutorState
from ..agents import (
    AdaptiveScaffoldingAgent,
    DiagnosticAgent,
    LearnerStateAgent,
    LearningPlannerAgent,
    ReflectionAgent,
    SimilarLearnerAgent,
)
from ..learning.scaffolding import FALLBACK_MATRIX

# Instantiate the six dedicated AI agents
diagnostic_agent = DiagnosticAgent()
learner_state_agent = LearnerStateAgent()
similar_learner_agent = SimilarLearnerAgent()
adaptive_scaffolding_agent = AdaptiveScaffoldingAgent()
reflection_agent = ReflectionAgent()
learning_planner_agent = LearningPlannerAgent()


def check_execution_branch(state: TutorState) -> str:
    """Route conditionally: passed solutions bypass scaffolding directly to positive reflection."""
    if state.get("execution", {}).get("passed", False):
        return "reflection"
    return "scaffolding"


def verify_hint_anti_leak(state: TutorState) -> dict:
    """
    R-12 / A-03 Anti-Leak Verifier Node:
    Inspects generated hint text for forbidden direct code solutions (fenced blocks, function definitions, multi-line logic).
    """
    scaffolding = state.get("scaffolding", {})
    hint_text = scaffolding.get("hint", "")
    level = scaffolding.get("level", 1)
    focus = scaffolding.get("focus", "Conceptual")
    attempts = state.get("verifier_attempts", 0)

    # Check for direct code leakage:
    has_code_fence = "```python" in hint_text or "```" in hint_text
    has_full_func = "def " in hint_text and "return " in hint_text and ":" in hint_text
    code_lines = [l for l in hint_text.splitlines() if l.strip().startswith(("def ", "for ", "while ", "if ", "return "))]
    is_leaky = (has_code_fence and ("def " in hint_text or "return " in hint_text)) or has_full_func or len(code_lines) >= 3

    if is_leaky:
        if attempts < 2:
            return {
                "verifier_attempts": attempts + 1,
                "leak_detected": True,
                "agent_activity": ["Anti-Leak Verifier (Leak Detected -> Re-generating)"]
            }
        else:
            # Over retry threshold: replace with deterministic pedagogical template
            safe_fallback = FALLBACK_MATRIX.get(
                (level, focus),
                "Examine how the expected output relates to each step of your calculation."
            )
            scaffolding_copy = dict(scaffolding)
            scaffolding_copy["hint"] = safe_fallback
            scaffolding_copy["anti_leak_sanitized"] = True
            return {
                "scaffolding": scaffolding_copy,
                "verifier_attempts": attempts + 1,
                "leak_detected": False,
                "agent_activity": ["Anti-Leak Verifier (Sanitized via Template)"]
            }

    return {
        "verifier_attempts": attempts,
        "leak_detected": False,
        "agent_activity": ["Anti-Leak Verifier (Clean)"]
    }


def route_verifier_decision(state: TutorState) -> str:
    """R-11 Cyclic orchestration: Re-enters scaffolding if leak was detected, else proceeds to reflection."""
    if state.get("leak_detected", False) and state.get("verifier_attempts", 0) <= 2:
        return "scaffolding"
    return "reflection"


def build_graph():
    graph = StateGraph(TutorState)

    # Register all 6 agent execute methods as graph nodes + anti-leak verifier
    graph.add_node("diagnostic", diagnostic_agent.execute)
    graph.add_node("learner_state", learner_state_agent.execute)
    graph.add_node("similar_learners", similar_learner_agent.execute)
    graph.add_node("scaffolding", adaptive_scaffolding_agent.execute)
    graph.add_node("hint_verifier", verify_hint_anti_leak)
    graph.add_node("reflection", reflection_agent.execute)
    graph.add_node("planner", learning_planner_agent.execute)

    # Sequential preprocessing
    graph.add_edge(START, "diagnostic")
    graph.add_edge("diagnostic", "learner_state")
    graph.add_edge("learner_state", "similar_learners")

    # Conditional branch: Passed vs Failed
    graph.add_conditional_edges(
        "similar_learners",
        check_execution_branch,
        {
            "scaffolding": "scaffolding",
            "reflection": "reflection"
        }
    )

    # Scaffolding leads to hint_verifier
    graph.add_edge("scaffolding", "hint_verifier")

    # R-11 Cyclic Edge: Verifier conditionally loops back to scaffolding if leak detected, or advances to reflection
    graph.add_conditional_edges(
        "hint_verifier",
        route_verifier_decision,
        {
            "scaffolding": "scaffolding",
            "reflection": "reflection"
        }
    )

    # Reflection leads to adaptive planner
    graph.add_edge("reflection", "planner")
    graph.add_edge("planner", END)

    return graph.compile()


tutor_graph = build_graph()
