"""Six-agent LangGraph orchestration with conditional routing, BKT mastery modeling, ChromaDB retrieval, and adaptive planning."""
import ast
import re
from langgraph.graph import END, START, StateGraph

from .state import TutorState
from ..database import (
    connection,
    get_concept,
    get_concept_progress,
    list_concepts,
    list_problems,
    save_hint,
    update_concept_progress_db,
)
from ..services.learner_model import (
    build_8d_profile_vector,
    calculate_cognitive_load_proxy,
    calculate_confidence,
    calculate_confusion,
    calculate_concept_progress,
    update_bkt_mastery,
)
from ..services.llm_service import llm
from ..services.vector_store import vector_store


# --- AGENT 1: DIAGNOSTIC AGENT ---

def detect_semantic_misconception(code: str, error_type: str, output: str) -> str:
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


def diagnostic(state: TutorState) -> dict:
    execution = state["execution"]
    error_type = execution.get("error_type", "none")
    output = execution.get("output", "")
    code = state.get("code", "")
    problem = state.get("problem", {})

    misconception = detect_semantic_misconception(code, error_type, output)
    severity = "low" if error_type == "none" else ("high" if error_type in ("security", "timeout", "recursion") else "medium")

    default_explanations = {
        "none": "Your solution passed all automated test assertions.",
        "syntax": f"Python syntax error encountered: {output}. Review punctuation, colons, and indentation.",
        "assertion": f"Assertion check failed. {output}. The returned value differed from the expected output.",
        "timeout": "Execution timed out. Review while/for loop conditions to ensure loop termination.",
        "recursion": "Maximum recursion depth exceeded. Verify that your base case is reachable.",
        "security": f"Security restriction: {output}",
        "runtime": f"Runtime exception: {output}. Trace variable values leading up to the failure."
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

    return {
        "diagnostic": {
            "error_type": error_type,
            "explanation": explanation,
            "misconception": misconception,
            "severity": severity,
            "output": output
        },
        "agent_activity": ["Diagnostic Agent"]
    }


# --- AGENT 2: LEARNER STATE AGENT (BKT + COGNITIVE INDICATORS) ---

def learner_state(state: TutorState) -> dict:
    old = state.get("prior_state", {})
    passed = state["execution"].get("passed", False)
    error_type = state["execution"].get("error_type", "none")
    response_time = float(state.get("response_time", 0.0))
    problem = state.get("problem", {})
    learner_id = state.get("learner_id", "demo-student")
    concept_id = problem.get("concept_id") or problem.get("topic") or "variables"

    prior_mastery = float(old.get("mastery", 0.35))
    prior_conf = float(old.get("confidence", 0.50))
    prior_confusion = float(old.get("confusion", 0.20))

    attempts = old.get("attempts", 0) + 1
    solved_count = old.get("solved_count", 0) + (1 if passed else 0)
    hints_used = old.get("hints_used", 0) + (0 if passed else 1)

    # 1. Bayesian Knowledge Tracing
    updated_mastery = update_bkt_mastery(prior_mastery, passed)

    # 2. Confidence & Confusion
    consecutive_fails = 0 if passed else old.get("consecutive_fails", 0) + 1
    updated_conf = calculate_confidence(prior_conf, passed, hints_used, response_time)
    updated_confusion = calculate_confusion(prior_confusion, passed, error_type, consecutive_fails, hints_used)

    # 3. Cognitive Load Proxy
    updated_cog_load = calculate_cognitive_load_proxy(
        concept_mastery=updated_mastery,
        difficulty=problem.get("difficulty", "easy"),
        hints_used=hints_used,
        response_time=response_time,
        passed=passed
    )

    # 4. Overall Progress
    concept_prog = calculate_concept_progress(updated_mastery, solved_count, total_problems=2)
    overall_progress = round(min(1.0, max(0.0, (solved_count * 0.1) + (updated_mastery * 0.5))), 2)

    updated = {
        "mastery": updated_mastery,
        "confidence": updated_conf,
        "confusion": updated_confusion,
        "cognitive_load": updated_cog_load,
        "progress": overall_progress,
        "concept_progress": concept_prog,
        "attempts": attempts,
        "solved_count": solved_count,
        "hints_used": hints_used,
        "consecutive_fails": consecutive_fails,
        "response_time": response_time,
        "concept_id": concept_id
    }

    # Persist concept progress record to SQLite
    try:
        update_concept_progress_db(learner_id, concept_id, updated_mastery, passed)
    except Exception:
        pass

    return {
        "learner_state": updated,
        "concept_id": concept_id,
        "agent_activity": ["Learner State Agent"]
    }


# --- AGENT 3: SIMILAR LEARNER RETRIEVAL AGENT (CHROMADB) ---

def similar_learners(state: TutorState) -> dict:
    l_state = state["learner_state"]
    # Construct consistent 8D normalized vector
    vector_8d = build_8d_profile_vector(l_state)

    # Query ChromaDB vector collection
    retrieved = vector_store.query_similar_learners(vector_8d, n_results=2)

    active_intervention = (
        retrieved[0]["intervention"] 
        if retrieved 
        else "Provide structured Socratic guidance based on observable test evidence."
    )

    return {
        "similar_learners": retrieved,
        "active_intervention": active_intervention,
        "agent_activity": ["Similar Learner Retrieval Agent"]
    }


# --- AGENT 4: ADAPTIVE SCAFFOLDING AGENT ---

def scaffolding(state: TutorState) -> dict:
    learner = state["learner_state"]
    problem = state.get("problem", {})
    intervention = state.get("active_intervention", "")
    code = state.get("code", "")
    diagnostic_info = state.get("diagnostic", {})
    error_type = diagnostic_info.get("error_type", "assertion")
    misconception = diagnostic_info.get("misconception", "")

    # Calculate Scaffolding Level (1 to 4)
    # Higher confusion, higher cognitive load, and lower mastery produce higher scaffolding
    score = (
        (1.0 - learner["mastery"]) * 0.35 +
        learner["confusion"] * 0.35 +
        learner["cognitive_load"] * 0.20 +
        min(learner["hints_used"] / 4.0, 1.0) * 0.10
    )
    level = min(4, max(1, int(score * 4.0) + 1))

    level_templates = {
        1: f"What happens if you trace this function on the smallest valid input? Notice the requirement: {problem.get('expected_behavior', '')}.",
        2: f"Check your assumptions regarding {misconception}. Strategy: {intervention}",
        3: f"Inspect the return value and loop boundary. Intervention cue: {intervention}. Trace each iteration step-by-step.",
        4: f"Structure guidance: 1. Initialize result accumulator. 2. Iterate carefully over input. 3. Ensure proper return statement outside loop. Note: {intervention}"
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
            hint_text=hint_text
        )
    except Exception:
        pass

    return {
        "scaffolding": {
            "level": level,
            "score": round(score, 2),
            "hint": hint_text,
            "intervention_applied": intervention
        },
        "agent_activity": ["Adaptive Scaffolding Agent"]
    }


# --- AGENT 5: REFLECTION AGENT ---

def reflection(state: TutorState) -> dict:
    passed = state["execution"].get("passed", False)
    problem = state.get("problem", {})
    code = state.get("code", "")
    diagnostic_info = state.get("diagnostic", {})

    if passed:
        fallback_prompt = (
            f"Excellent! Your solution for '{problem.get('title', '')}' passed all tests. "
            "In one sentence, explain what the core invariant of your approach was, and what its time complexity is."
        )
        sys_prompt = "You are a thoughtful tutor encouraging meta-cognitive reflection. Formulate one insightful question asking the student to explain why their working code is sound or analyze its Big-O complexity."
        prompt = f"Problem: {problem.get('title', '')}\nPassing Code:\n{code[:400]}\nGenerate a reflective post-solution question."
    else:
        misconception = diagnostic_info.get("misconception", "the logic error")
        fallback_prompt = (
            f"Before resubmitting, compare the expected test output against your code's behavior. "
            f"Where did your step-by-step mental trace diverge regarding {misconception}?"
        )
        sys_prompt = "You are a reflective programming tutor. Formulate one targeted question prompting the student to compare their mental model against the observed error."
        prompt = f"Problem: {problem.get('title', '')}\nError: {diagnostic_info.get('output', '')}\nMisconception: {misconception}\nGenerate a reflection question."

    reflection_text = llm.tutor_reply(prompt, fallback_prompt, system_prompt=sys_prompt)

    return {
        "reflection": reflection_text,
        "agent_activity": ["Reflection Agent"]
    }


# --- AGENT 6: LEARNING PLANNER AGENT ---

def planner(state: TutorState) -> dict:
    passed = state["execution"].get("passed", False)
    current_problem = state.get("problem", {})
    learner = state["learner_state"]
    concept_id = state.get("concept_id") or current_problem.get("concept_id") or "variables"
    learner_id = state.get("learner_id", "demo-student")

    concepts = list_concepts()
    concept_map = {c["id"]: c for c in concepts}
    curr_concept = concept_map.get(concept_id, {})
    curr_order = curr_concept.get("order_index", 1)

    mastery = learner.get("mastery", 0.35)
    confusion = learner.get("confusion", 0.20)

    # Adaptive decision logic:
    # 1. If passed and high mastery (>= 0.75): Advance to next concept or harder problem
    # 2. If passed with moderate mastery: Reinforce same concept
    # 3. If failed with high confusion: Recommend remediation on prerequisite
    # 4. If failed with low confusion: Retry current problem with hint

    if passed and mastery >= 0.75:
        # Advance to next concept in curriculum
        next_order = curr_order + 1
        next_concept = next((c for c in concepts if c["order_index"] == next_order), curr_concept)
        candidate_problems = list_problems(next_concept["id"])
        next_prob = candidate_problems[0] if candidate_problems else current_problem
        action = "advance"
        reason = f"High mastery ({int(mastery*100)}%) demonstrated! Advance to '{next_concept.get('title', '')}' to expand your Python skillset."
    elif passed:
        # Same concept, next problem if available
        candidate_problems = [p for p in list_problems(concept_id) if p["id"] != current_problem.get("id")]
        next_prob = candidate_problems[0] if candidate_problems else current_problem
        next_concept = curr_concept
        action = "reinforce"
        reason = f"Good job! Reinforce your understanding of '{curr_concept.get('title', '')}' with another practice challenge."
    elif confusion >= 0.65 or learner.get("consecutive_fails", 0) >= 3:
        # Remediation
        action = "remediate"
        reason = f"Noticeable difficulty detected on {curr_concept.get('title', '')}. Review the concept notes and apply the scaffolding hint before trying again."
        next_prob = current_problem
        next_concept = curr_concept
    else:
        # Retry with hint
        action = "retry"
        reason = "Apply the Level " + str(state.get("scaffolding", {}).get("level", 1)) + " hint to adjust your logic, then run and resubmit."
        next_prob = current_problem
        next_concept = curr_concept

    recommendation = {
        "action": action,
        "next_problem_id": next_prob.get("id", current_problem.get("id", 1)),
        "next_problem_title": next_prob.get("title", current_problem.get("title", "")),
        "next_concept_id": next_concept.get("id", concept_id),
        "topic": next_concept.get("title", curr_concept.get("title", "Python")),
        "difficulty": next_prob.get("difficulty", "easy"),
        "reason": reason
    }

    return {
        "recommendation": recommendation,
        "agent_activity": ["Learning Planner Agent"]
    }


# --- CONDITIONAL ROUTING & LANGGRAPH COMPILATION ---

def check_execution_branch(state: TutorState) -> str:
    """Route conditionally: passed solutions bypass scaffolding directly to positive reflection."""
    if state["execution"].get("passed", False):
        return "reflection"
    return "scaffolding"


def build_graph():
    graph = StateGraph(TutorState)

    # Register all 6 agents
    graph.add_node("diagnostic", diagnostic)
    graph.add_node("learner_state", learner_state)
    graph.add_node("similar_learners", similar_learners)
    graph.add_node("scaffolding", scaffolding)
    graph.add_node("reflection", reflection)
    graph.add_node("planner", planner)

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
