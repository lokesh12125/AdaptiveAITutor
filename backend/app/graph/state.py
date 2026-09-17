import operator
from typing import Annotated, TypedDict


class TutorState(TypedDict, total=False):
    learner_id: str
    problem: dict
    code: str
    response_time: float
    execution: dict
    prior_state: dict
    concept_id: str
    diagnostic: dict
    learner_state: dict
    similar_learners: list[dict]
    active_intervention: str
    scaffolding: dict
    reflection: str
    recommendation: dict
    agent_activity: Annotated[list[str], operator.add]
