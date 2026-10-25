"""Six-agent LangGraph orchestration with dedicated agent instances, conditional routing, BKT mastery, and adaptive planning."""
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


def build_graph():
    graph = StateGraph(TutorState)

    # Register all 6 agent execute methods as graph nodes
    graph.add_node("diagnostic", diagnostic_agent.execute)
    graph.add_node("learner_state", learner_state_agent.execute)
    graph.add_node("similar_learners", similar_learner_agent.execute)
    graph.add_node("scaffolding", adaptive_scaffolding_agent.execute)
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

    # Scaffolding leads to reflection
    graph.add_edge("scaffolding", "reflection")

    # Reflection leads to adaptive planner
    graph.add_edge("reflection", "planner")
    graph.add_edge("planner", END)

    return graph.compile()


tutor_graph = build_graph()
