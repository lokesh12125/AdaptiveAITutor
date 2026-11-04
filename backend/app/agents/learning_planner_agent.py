"""Learning Planner Agent for adaptive pedagogical recommendations, concept-graph traversal, and curriculum planning."""
from typing import Any, Dict, List, Optional

from ..curriculum import CURRICULUM_CONCEPTS
from ..database import list_concepts, list_problems
from ..graph.state import TutorState

# C-01: Full 49-Concept Curriculum Graph with Topological Dependencies
CONCEPT_GRAPH = [
    {
        "id": c["id"],
        "title": c["title"],
        "category": c.get("category", "Foundations"),
        "prerequisite": c["prerequisites"][0] if c.get("prerequisites") and len(c["prerequisites"]) > 0 else (
            CURRICULUM_CONCEPTS[i - 1]["id"] if i > 0 else None
        )
    }
    for i, c in enumerate(sorted(CURRICULUM_CONCEPTS, key=lambda x: x.get("order_index", 0)))
]


class LearningPlannerAgent:
    """Agent responsible for inspecting multi-dimensional cognitive states

    (mastery, confidence, confusion, cognitive load) and traversing the Concept Graph
    to determine next topics, prerequisite remediation, revision concepts, and learning paths.
    """

    def _get_concept_node(self, concept_id: str) -> Dict[str, Any]:
        """Find matching concept in the graph or map fallback."""
        clean_id = concept_id.lower().replace(" ", "-")
        for node in CONCEPT_GRAPH:
            if node["id"] in clean_id or clean_id in node["id"] or node["title"].lower() in clean_id:
                return node
        # Fallback search by title
        for node in CONCEPT_GRAPH:
            if node["id"] == "variables":
                return node
        return CONCEPT_GRAPH[0]

    def _build_learning_path(self, current_node_id: str) -> List[str]:
        """Construct the forward learning path sequence starting from the current node."""
        path = []
        found_current = False
        for node in CONCEPT_GRAPH:
            if node["id"] == current_node_id or node["title"].lower() == current_node_id.lower():
                found_current = True
            if found_current:
                path.append(node["title"])
        if not path:
            path = [node["title"] for node in CONCEPT_GRAPH]
        return path

    def execute(self, state: TutorState) -> Dict[str, Any]:
        """Inspect student's full cognitive state and generate deterministic curriculum recommendations."""
        execution = state.get("execution", {})
        passed = execution.get("passed", False)
        current_problem = state.get("problem", {})
        learner = state.get("learner_state", {})
        concept_id = (
            state.get("concept_id")
            or current_problem.get("concept_id")
            or "variables"
        )
        learner_id = state.get("learner_id", "demo-student")

        # Multi-factor cognitive state inspection
        mastery = float(learner.get("mastery", 0.35))
        confidence = float(learner.get("confidence", 0.50))
        confusion = float(learner.get("confusion", 0.20))
        cognitive_load = float(learner.get("cognitive_load", 0.30))
        consecutive_fails = int(learner.get("consecutive_fails", 0))

        # Curriculum concepts from database
        db_concepts = list_concepts()
        db_concept_map = {c["id"]: c for c in db_concepts}
        curr_db_concept = db_concept_map.get(concept_id, {})
        curr_order = curr_db_concept.get("order_index", 1)

        # Concept Graph Nodes
        current_graph_node = self._get_concept_node(concept_id)
        prereq_id = current_graph_node.get("prerequisite")
        prereq_node = self._get_concept_node(prereq_id) if prereq_id else current_graph_node

        prerequisite_concept = prereq_node["title"]
        revision_concept = current_graph_node["title"]

        # Planner Decision Matrix based on BKT + EWMA Cognitive Indicators:
        # 1. High Mastery (>= 0.75) & Passed: ADVANCE to next concept node in graph
        # 2. Moderate Mastery & Passed: REINFORCE current concept with next problem
        # 3. High Confusion (>= 0.60) or High Cognitive Load (>= 0.65) or Fails >= 3: REMEDIATE on prerequisite concept
        # 4. Low Confusion & Failed: RETRY current problem with scaffolding hint

        if passed and mastery >= 0.75:
            # Find next concept in DB order
            next_order = curr_order + 1
            next_db_concept = next(
                (c for c in db_concepts if c.get("order_index") == next_order),
                curr_db_concept
            )
            candidate_problems = list_problems(next_db_concept.get("id", concept_id))
            next_prob = candidate_problems[0] if candidate_problems else current_problem

            # Next topic in concept graph
            curr_idx = next((i for i, n in enumerate(CONCEPT_GRAPH) if n["id"] == current_graph_node["id"]), 0)
            next_node = CONCEPT_GRAPH[min(curr_idx + 1, len(CONCEPT_GRAPH) - 1)]
            next_topic = next_node["title"]

            action = "advance"
            reason = (
                f"High mastery ({int(mastery * 100)}%) and confidence ({int(confidence * 100)}%) demonstrated! "
                f"Advancing to '{next_topic}' in your adaptive learning path."
            )
        elif passed:
            # Reinforce same concept with different problem
            candidate_problems = [
                p for p in list_problems(concept_id)
                if p.get("id") != current_problem.get("id")
            ]
            next_prob = candidate_problems[0] if candidate_problems else current_problem
            next_topic = current_graph_node["title"]

            action = "reinforce"
            reason = (
                f"Good job solving '{current_problem.get('title', 'problem')}'. "
                f"Reinforce your understanding of '{next_topic}' with another problem."
            )
        elif confusion >= 0.60 or cognitive_load >= 0.65 or consecutive_fails >= 3:
            # Remediation on prerequisite
            action = "remediate"
            reason = (
                f"High confusion ({int(confusion * 100)}%) or cognitive load ({int(cognitive_load * 100)}%) detected. "
                f"We recommend reviewing foundational prerequisite '{prerequisite_concept}' before retrying."
            )
            next_prob = current_problem
            next_topic = prerequisite_concept
        else:
            # Retry current problem with hint
            action = "retry"
            reason = (
                f"Apply the Level {state.get('scaffolding', {}).get('level', 1)} Socratic hint to adjust your logic, "
                f"then run and resubmit your code."
            )
            next_prob = current_problem
            next_topic = current_graph_node["title"]

        learning_path = self._build_learning_path(current_graph_node["id"])

        recommendation = {
            "action": action,
            "next_topic": next_topic,
            "next_problem_id": next_prob.get("id", current_problem.get("id", 1)),
            "next_problem_title": next_prob.get("title", current_problem.get("title", "")),
            "next_concept_id": next_db_concept.get("id", concept_id) if passed and mastery >= 0.75 else concept_id,
            "topic": next_topic,
            "difficulty": next_prob.get("difficulty", "easy"),
            "reason": reason,
            "prerequisite_concept": prerequisite_concept,
            "revision_concept": revision_concept,
            "learning_path": learning_path,
        }

        return {
            "recommendation": recommendation,
            "agent_activity": ["Learning Planner Agent"],
        }
