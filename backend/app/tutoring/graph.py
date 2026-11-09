"""LangGraph orchestration: one learning cycle per learner action, on a cyclic graph.

    intake -> evaluate -> diagnostic -> cognitive_state -> retrieval -> dsda
           -> generate_hint <-> validate_hint -> reflection -> planner -> finalize -> await_learner
                                                                                         |
    intake <-------------------- the learner's next action resumes the graph ------------+

Two real cycles exist. The learning cycle pauses in `await_learner` until the learner acts, and the
pause is stored in PostgreSQL by the checkpointer. The validation cycle is bounded, and it never
produces more detailed help: it only rewrites a rejected draft at the same level.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import START, StateGraph
from langgraph.types import interrupt

from . import nodes

MAX_GENERATION_ATTEMPTS = 3


class TutorState(TypedDict, total=False):
    event: dict[str, Any]
    cycle: int
    context: dict[str, Any]
    evaluation: dict[str, Any]
    diagnostic: dict[str, Any]
    cognitive: dict[str, Any]
    retrieval: dict[str, Any]
    decision: dict[str, Any]
    hint: dict[str, Any] | None
    generation_attempts: int
    violations: list[str]
    reflection: dict[str, Any]
    plan: dict[str, Any]
    cycle_log: list[dict[str, Any]]


def route_after_evaluate(state: TutorState) -> Literal["diagnostic", "finalize"]:
    verdict = state["evaluation"].get("verdict")
    if verdict in ("service_failure", "cancelled"):
        for stage, agent in nodes.AGENT_STAGES:
            nodes.record_skip(state, stage, agent, "The code could not be evaluated, so this stage did not run.")
        return "finalize"
    return "diagnostic"


def route_after_state(state: TutorState) -> Literal["retrieval", "dsda"]:
    if state["diagnostic"]["category"] == "accepted":
        nodes.record_skip(state, "retrieval", "similar_learner_retrieval", "The task is solved, so no help needs to be chosen.")
        return "dsda"
    return "retrieval"


def route_after_dsda(state: TutorState) -> Literal["generate_hint", "reflection"]:
    if state["decision"]["action"] == "give_help":
        return "generate_hint"
    # An offer generates nothing: if the learner accepts, that request starts a new cycle.
    nodes.record_skip(state, "generate_hint", "adaptive_scaffolding", "DSDA decided not to show a hint now.")
    nodes.record_skip(state, "validate_hint", "adaptive_scaffolding", "There is no hint to validate.")
    return "reflection"


def route_after_validate(state: TutorState) -> Literal["generate_hint", "reflection"]:
    violations = state.get("violations") or []
    if violations and state.get("generation_attempts", 0) < MAX_GENERATION_ATTEMPTS:
        return "generate_hint"
    return "reflection"


def await_learner(state: TutorState) -> dict[str, Any]:
    """Pause here. Nothing runs until the learner's next action resumes the graph."""
    event = interrupt({"waiting_for": "learner_action", "cycle": state.get("cycle", 0)})
    return {
        "event": event, "cycle": state.get("cycle", 0) + 1, "evaluation": {}, "diagnostic": {}, "cognitive": {},
        "retrieval": {}, "decision": {}, "hint": None, "generation_attempts": 0, "violations": [], "reflection": {}, "plan": {},
    }


def build_graph(checkpointer=None):
    graph = StateGraph(TutorState)
    graph.add_node("intake", nodes.intake)
    graph.add_node("evaluate", nodes.evaluate)
    graph.add_node("diagnostic", nodes.diagnostic)
    graph.add_node("cognitive_state", nodes.cognitive_state)
    graph.add_node("retrieval", nodes.retrieval)
    graph.add_node("dsda", nodes.dsda)
    graph.add_node("generate_hint", nodes.generate_hint)
    graph.add_node("validate_hint", nodes.validate_hint_node)
    graph.add_node("reflection", nodes.reflection)
    graph.add_node("planner", nodes.planner)
    graph.add_node("finalize", nodes.finalize)
    graph.add_node("await_learner", await_learner)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "evaluate")
    graph.add_conditional_edges("evaluate", route_after_evaluate, ["diagnostic", "finalize"])
    graph.add_edge("diagnostic", "cognitive_state")
    graph.add_conditional_edges("cognitive_state", route_after_state, ["retrieval", "dsda"])
    graph.add_edge("retrieval", "dsda")
    graph.add_conditional_edges("dsda", route_after_dsda, ["generate_hint", "reflection"])
    graph.add_edge("generate_hint", "validate_hint")
    graph.add_conditional_edges("validate_hint", route_after_validate, ["generate_hint", "reflection"])
    graph.add_edge("reflection", "planner")
    graph.add_edge("planner", "finalize")
    graph.add_edge("finalize", "await_learner")
    graph.add_edge("await_learner", "intake")  # the learning cycle
    return graph.compile(checkpointer=checkpointer)

