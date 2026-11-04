"""Learner State Agent for Bayesian Knowledge Tracing (BKT) and cognitive metric estimation."""
from typing import Any, Dict

from ..database import (
    get_concept_progress,
    get_concept_state,
    get_recent_concept_history,
    get_problem_hints,
    get_recent_problem_attempts,
    update_concept_progress_db,
)
from ..graph.state import TutorState
from ..learning.bkt import update_mastery
from ..learning.cognitive_load import (
    calculate_attempt_stress,
    calculate_error_stress,
    calculate_hint_stress,
    calculate_load_signal,
    calculate_time_stress,
    update_cognitive_load,
)
from ..learning.confidence import calculate_confidence_evidence, update_confidence
from ..learning.confusion import calculate_confusion_signal, update_confusion
from ..learning.progress import calculate_concept_progress, calculate_overall_progress


class LearnerStateAgent:
    """Agent responsible for maintaining and updating the student's cognitive state

    including BKT mastery, confidence (EWMA), confusion signals, cognitive load, and overall progress.
    """

    def execute(self, state: TutorState) -> Dict[str, Any]:
        """Process student submission evidence and update knowledge tracing state."""
        old = state.get("prior_state", {})
        execution = state.get("execution", {})
        passed = execution.get("passed", False)
        error_type = execution.get("error_type", "none")
        response_time = float(state.get("response_time", 0.0))
        problem = state.get("problem", {})
        learner_id = state.get("learner_id", "demo-student")

        # Map to concept
        concept_id = problem.get("concept_id") or problem.get("topic") or "variables"

        # Fetch Concept-Specific Prior State and History
        concept_prior = get_concept_state(learner_id, concept_id)
        recent_history = get_recent_concept_history(learner_id, concept_id, limit=5)

        prior_mastery = float(concept_prior.get("mastery", 0.20))
        prior_conf = float(concept_prior.get("confidence", 0.50))
        prior_confusion = float(concept_prior.get("confusion", 0.00))
        prior_load = float(concept_prior.get("cognitive_load", 0.00))

        attempts = concept_prior.get("attempts_count", 0) + 1
        solved_count = concept_prior.get("success_count", 0) + (1 if passed else 0)

        # Synchronize hints delivered for this specific problem from database
        problem_id = int(problem.get("id", 1))
        problem_hints = get_problem_hints(learner_id, problem_id)
        current_hints_used = len(problem_hints)

        # Problem-scoped consecutive failure streak
        problem_attempts = get_recent_problem_attempts(learner_id, problem_id, limit=10)
        problem_consecutive_fails = 0
        if not passed:
            problem_consecutive_fails = 1
            for pa in problem_attempts:
                if not pa.get("passed"):
                    problem_consecutive_fails += 1
                else:
                    break

        # Compute concept-scoped consecutive fails from recent history
        consecutive_fails = 0
        if not passed:
            consecutive_fails = 1
            for hist in recent_history:
                if not hist.get("passed"):
                    consecutive_fails += 1
                else:
                    break

        # Compute baseline response time from past interactions
        past_times = [
            h.get("response_time", 0.0)
            for h in recent_history
            if h.get("response_time", 0.0) > 0
        ]
        baseline_rt = 60.0
        if past_times:
            past_times.sort()
            baseline_rt = past_times[len(past_times) // 2]  # Median

        # 1. Mastery & Cognitive State: Bayesian Knowledge Tracing and EWMA
        # Security violations represent policy blocks, not pedagogical failure: preserve prior measurements
        is_security_event = (error_type == "security" or state.get("diagnostic", {}).get("error_type") == "security")
        if is_security_event:
            updated_mastery = prior_mastery
            updated_conf = prior_conf
            updated_confusion = prior_confusion
            updated_cog_load = prior_load
        else:
            updated_mastery = update_mastery(prior_mastery, passed, hints_used=current_hints_used)

            # 2. Confidence: EWMA
            conf_ev = calculate_confidence_evidence(passed, current_hints_used, consecutive_fails)
            updated_conf = update_confidence(prior_conf, conf_ev)

            # 3. Confusion: EWMA
            conf_sig = calculate_confusion_signal(passed, consecutive_fails, current_hints_used)
            updated_confusion = update_confusion(prior_confusion, conf_sig)

            # 4. Cognitive Load: EWMA
            time_stress = calculate_time_stress(response_time, baseline_rt)
            attempt_stress = calculate_attempt_stress(attempts)

            recent_errors = sum(1 for h in recent_history if not h.get("passed"))
            if not passed:
                recent_errors += 1

            error_stress = calculate_error_stress(recent_errors)
            hint_stress = calculate_hint_stress(current_hints_used)

            load_sig = calculate_load_signal(
                time_stress, attempt_stress, error_stress, hint_stress
            )
            updated_cog_load = update_cognitive_load(prior_load, load_sig)

        # Persist updated concept state to DB
        try:
            update_concept_progress_db(
                learner_id,
                concept_id,
                updated_mastery,
                updated_conf,
                updated_confusion,
                updated_cog_load,
                passed,
                current_hints_used,
            )
        except Exception:
            pass

        # Calculate Progress
        concept_prog = calculate_concept_progress(updated_mastery)

        # Fetch all concept states for overall progress
        all_concepts = list(get_concept_progress(learner_id).values())
        found = False
        for c in all_concepts:
            if c.get("concept_id") == concept_id:
                c["mastery"] = updated_mastery
                found = True
        if not found:
            all_concepts.append({"concept_id": concept_id, "mastery": updated_mastery})

        overall_progress = calculate_overall_progress(all_concepts)

        updated = {
            "mastery": round(updated_mastery, 3),
            "confidence": round(updated_conf, 3),
            "confusion": round(updated_confusion, 3),
            "cognitive_load": round(updated_cog_load, 3),
            "progress": overall_progress,
            "concept_progress": concept_prog,
            "attempts": attempts,
            "solved_count": solved_count,
            "hints_used": current_hints_used,
            "problem_consecutive_fails": problem_consecutive_fails,
            "consecutive_fails": consecutive_fails,
            "baseline_time": baseline_rt,
            "response_time": response_time,
            "concept_id": concept_id,
        }

        return {
            "learner_state": updated,
            "concept_id": concept_id,
            "agent_activity": ["Learner State Agent"],
        }
