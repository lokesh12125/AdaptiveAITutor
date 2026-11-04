"""FastAPI main application router for the Adaptive Multi-Agent AI Tutoring System."""
import os
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Security, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from .auth import (
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    verify_password,
)
from .config import api_key_configured
from .database import (
    create_custom_problem,
    create_user,
    get_chat_history,
    get_concept,
    get_concept_progress,
    get_latest_metrics,
    get_problem,
    get_state,
    get_user_by_email,
    get_user_by_id,
    history,
    initialize_database,
    list_concepts,
    list_custom_problems,
    list_problems,
    save_attempt_and_state,
    save_chat_message,
    save_evaluation_metric,
    get_all_student_metrics,
    get_problem_hints,
    save_recommendation,
    get_latest_recommendation,
    start_learning_session,
    update_learning_session,
    end_learning_session,
    get_learning_sessions,
    get_session_by_id,
    get_state_history,
    get_weakest_concepts,
    get_learner_misconceptions,
    get_student_drilldown,
    save_reflection_response,
    save_satisfaction_survey,
    save_hint,
)
from .graph.tutor_graph import tutor_graph
from .learning.assessment import evaluate_placement_answers, get_placement_quiz
from .services.code_runner import evaluate
from .services.llm_service import generate_contextual_socratic_fallback, llm
from .services.vector_store import vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Adaptive Multi-Agent AI Tutoring Platform", lifespan=lifespan)

# P-08: Standardized CORS permissions with configurable origins and security headers
cors_env = os.environ.get("CORS_ORIGINS", "*")
if cors_env.strip() == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """P-08: Attach OWASP recommended baseline security headers to all HTTP responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


TEACHER_INVITE_CODE = os.environ.get("TEACHER_INVITE_CODE", "TEACH-2026-ADAPTIVE")


# --- REQUEST & RESPONSE SCHEMAS ---

class RegisterRequest(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=4, max_length=100)
    role: str = Field(default="student")
    invite_code: Optional[str] = None

    @model_validator(mode="before")
    def resolve_name(cls, data):
        if isinstance(data, dict):
            name = data.get("name") or data.get("full_name")
            if not name or len(str(name).strip()) < 2:
                raise ValueError("Name must be at least 2 characters.")
            data["name"] = str(name).strip()
        return data


class LoginRequest(BaseModel):
    email: str
    password: str


class Submission(BaseModel):
    learner_id: str = Field(min_length=1, max_length=80)
    problem_id: int
    code: str = Field(min_length=1, max_length=15000)
    response_time: float = Field(default=0.0, ge=0.0, le=86400.0)
    session_id: Optional[int] = None


class ChatRequest(BaseModel):
    learner_id: str
    message: str = Field(min_length=1, max_length=2000)
    problem_id: Optional[int] = None


class CustomQuestionRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=10, max_length=3000)
    concept_id: str
    difficulty: str = Field(default="easy")
    starter_code: str = Field(default="def solution():\n    pass")
    test_cases: list[dict] = Field(default_factory=list)
    expected_behavior: str = Field(default="")
    creator_id: Optional[str] = None


class SatisfactionRequest(BaseModel):
    learner_id: str
    score: int = Field(ge=1, le=5)


class ReflectionSubmitRequest(BaseModel):
    learner_id: str
    problem_id: int
    prompt_text: str
    response_text: str
    session_id: Optional[int] = None


class SurveySubmitRequest(BaseModel):
    learner_id: str
    session_id: Optional[int] = None
    usefulness_score: int = Field(default=5, ge=1, le=5)
    clarity_score: int = Field(default=5, ge=1, le=5)
    hint_adequacy_score: int = Field(default=5, ge=1, le=5)
    perceived_adaptivity_score: int = Field(default=5, ge=1, le=5)
    comments: Optional[str] = ""


class PlacementSubmitRequest(BaseModel):
    learner_id: str
    answers: dict[str, str]


class ProgressiveHintRequest(BaseModel):
    learner_id: str = Field(min_length=1, max_length=80)
    problem_id: int
    level: int = Field(ge=1, le=4, default=1)
    code: Optional[str] = ""


# --- 1. HEALTH CHECK ---

@app.get("/api/health")
def health() -> dict:
    """Comprehensive health check reporting status of backend, database, chromadb, and LLM."""
    db_status = "ok"
    try:
        from .database import connection
        with connection() as conn:
            conn.execute("SELECT 1").fetchone()
    except Exception:
        db_status = "error"

    chroma_status = vector_store.status()

    return {
        "status": "ok",
        "backend": "ok",
        "database": db_status,
        "chromadb": chroma_status,
        "llm": llm.mode,
        "api_key_configured": api_key_configured()
    }


# --- 2. AUTHENTICATION & USER MANAGEMENT ---

@app.post("/api/auth/register")
def register(payload: RegisterRequest) -> dict:
    existing = get_user_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")
    
    # P-02 role escalation defense: only allow teacher role with a valid invitation key
    assigned_role = "student"
    if payload.role == "teacher":
        if payload.invite_code != TEACHER_INVITE_CODE:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Teacher registration requires a valid teacher invite code."
            )
        assigned_role = "teacher"

    user_id = f"user-{uuid.uuid4().hex[:8]}"
    pwd_hash = hash_password(payload.password)
    user = create_user(user_id=user_id, name=payload.name, email=payload.email, password_hash=pwd_hash, role=assigned_role)
    token = create_access_token(user_id=user["id"], name=user["name"], email=user["email"], role=user.get("role", "student"))
    return {"token": token, "user": user}


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict:
    user = get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    role = user.get("role", "student")
    token = create_access_token(user_id=user["id"], name=user["name"], email=user["email"], role=role)
    return {
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"], "role": role}
    }


@app.get("/api/auth/me")
def me(current_user: dict = Depends(get_current_user)) -> dict:
    user = get_user_by_id(current_user["uid"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"id": user["id"], "name": user["name"], "email": user["email"], "role": user.get("role", "student")}


@app.get("/api/admin/students")
def admin_students(current_user: dict = Depends(get_current_user)) -> list[dict]:
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Forbidden: Teachers only.")
    return get_all_student_metrics()


@app.get("/api/teacher/students/{student_id}/drilldown")
def teacher_student_drilldown(student_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    """R-14: Detailed per-student longitudinal drilldown analytics, concept mastery breakdown, and at-risk alerts."""
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Forbidden: Teachers only.")
    data = get_student_drilldown(student_id)
    if not data:
        raise HTTPException(status_code=404, detail="Student not found.")
    return data


# --- 3. CURRICULUM & PROBLEMS ---

@app.get("/api/concepts")
def concepts() -> list[dict]:
    return list_concepts()


@app.get("/api/concepts/{concept_id}")
def concept_detail(concept_id: str) -> dict:
    item = get_concept(concept_id)
    if not item:
        raise HTTPException(status_code=404, detail="Concept not found.")
    problems_list = list_problems(concept_id=concept_id)
    return {"concept": item, "problems": problems_list}


@app.get("/api/problems")
def problems(concept_id: Optional[str] = Query(default=None)) -> list[dict]:
    return list_problems(concept_id=concept_id)


@app.get("/api/problems/{problem_id}")
def problem(problem_id: int) -> dict:
    item = get_problem(problem_id)
    if not item:
        raise HTTPException(status_code=404, detail="Problem not found.")
    return item


@app.post("/api/custom-questions")
def create_question(payload: CustomQuestionRequest, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    creator_id = (current_user and current_user.get("uid")) or payload.creator_id or "anonymous"
    new_prob = create_custom_problem(
        creator_id=creator_id,
        title=payload.title,
        description=payload.description,
        concept_id=payload.concept_id,
        difficulty=payload.difficulty,
        starter_code=payload.starter_code,
        test_cases=payload.test_cases,
        expected_behavior=payload.expected_behavior
    )
    return new_prob


@app.get("/api/custom-questions")
@app.get("/api/custom-questions/{creator_id}")
def get_custom_questions(creator_id: Optional[str] = None) -> list[dict]:
    return list_custom_problems(creator_id)


# --- 4. CODE SUBMISSION & MULTI-AGENT WORKFLOW ---

@app.post("/api/run")
def run_code(payload: Submission, current_user: dict = Depends(get_current_user)) -> dict:
    """Execute code against problem tests in an isolated sandbox (P-01: requires authentication)."""
    if len(payload.code) > 15000:
        raise HTTPException(status_code=413, detail="Payload Too Large: Code exceeds 15,000 character cap.")
    item = get_problem(payload.problem_id)
    if not item:
        raise HTTPException(status_code=404, detail="Problem not found.")
    execution = evaluate(payload.code, payload.problem_id)
    return {"execution": execution}


@app.post("/api/submit")
def submit(payload: Submission, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Code submission requires a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if current_user.get("role") != "teacher":
        if current_user.get("uid") != payload.learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You cannot submit work on behalf of another learner."
            )

    item = get_problem(payload.problem_id)
    if not item:
        raise HTTPException(status_code=404, detail="Problem not found.")

    # P-13: Validate response_time against client idle anomalies and non-finite values
    raw_rt = payload.response_time
    if raw_rt is None or str(raw_rt) in ("nan", "inf", "-inf"):
        safe_response_time = 30.0
    else:
        try:
            val = float(raw_rt)
            if val < 0.0 or val > 7200.0:
                safe_response_time = 30.0
            else:
                safe_response_time = max(0.5, min(val, 1800.0))
        except (ValueError, TypeError):
            safe_response_time = 30.0

    # 1. Evaluate code in isolated sandbox
    execution = evaluate(payload.code, payload.problem_id)

    # 2. Invoke 6-Agent LangGraph Engine
    prior = get_state(payload.learner_id)
    graph_input = {
        "learner_id": payload.learner_id,
        "problem": item,
        "code": payload.code,
        "response_time": safe_response_time,
        "execution": execution,
        "prior_state": prior,
        "agent_activity": []
    }
    result = tutor_graph.invoke(graph_input)

    # 3. Resolve scaffolding payload
    if execution["passed"]:
        scaffolding_data = {
            "level": 0,
            "score": 0.0,
            "hint": "All test assertions passed successfully! Great work.",
            "focus": "None",
            "remediation_flag": False,
            "rationale": "Solution passed all assertions."
        }
    else:
        scaffolding_data = result.get("scaffolding", {})

    # 4. Persist attempt and updated state
    save_attempt_and_state(
        learner_id=payload.learner_id,
        problem_id=payload.problem_id,
        code=payload.code,
        passed=execution["passed"],
        error_type=result["diagnostic"]["error_type"],
        state=result["learner_state"],
        concept_id=result.get("concept_id", item.get("concept_id")),
        response_time=safe_response_time,
        scaffolding_level=scaffolding_data.get("level", 0 if execution["passed"] else 1),
        hints_used=result["learner_state"].get("hints_used", 0)
    )

    # 4b. Update session counters if active session_id is provided
    if payload.session_id:
        try:
            update_learning_session(payload.session_id, attempted=True, solved=execution["passed"])
        except Exception:
            pass

    # 5. Persist learning recommendation if generated
    rec = result.get("recommendation")
    if rec and isinstance(rec, dict):
        try:
            save_recommendation(
                learner_id=payload.learner_id,
                problem_id=rec.get("next_problem_id"),
                concept_id=rec.get("next_concept_id"),
                reason=rec.get("reason", "")
            )
        except Exception:
            pass

    return {
        "mode": llm.mode,
        "execution": execution,
        "diagnostic": result["diagnostic"],
        "learner_state": result["learner_state"],
        "similar_learners": result.get("similar_learners", []),
        "scaffolding": scaffolding_data,
        "reflection": result.get("reflection", ""),
        "recommendation": result.get("recommendation", {}),
        "agent_activity": result.get("agent_activity", [])
    }


# --- 5. LEARNER PROFILE, HISTORY & DASHBOARD ---

def check_learner_access(learner_id: str, current_user: Optional[dict]) -> None:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Access to private learner records requires a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if current_user.get("role") != "teacher":
        if current_user.get("uid") != learner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: You do not have permission to access another learner's records."
            )


@app.get("/api/learner/{learner_id}")
def learner(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    check_learner_access(learner_id, current_user)
    return get_state(learner_id)


@app.get("/api/learner/{learner_id}/progress")
def learner_concept_progress(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    check_learner_access(learner_id, current_user)
    return get_concept_progress(learner_id)


@app.get("/api/progress/concepts/{learner_id}")
def learner_concept_progress_alias(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> list[dict]:
    check_learner_access(learner_id, current_user)
    prog = get_concept_progress(learner_id)
    concepts_list = list_concepts()
    result = []
    for c in concepts_list:
        cp = prog.get(c["id"], {})
        result.append({
            "concept_id": c["id"],
            "concept_name": c["title"],
            "category": c["category"],
            "progress_pct": int(cp.get("progress_pct", 0)),
            "mastery": float(cp.get("mastery", 0.35)),
            "attempts": int(cp.get("attempts_count", 0)),
            "successes": int(cp.get("success_count", 0))
        })
    return result


@app.get("/api/learner/{learner_id}/history")
def learner_history(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> list[dict]:
    check_learner_access(learner_id, current_user)
    return history(learner_id)


@app.get("/api/history/{learner_id}")
def learner_history_alias(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> list[dict]:
    check_learner_access(learner_id, current_user)
    return history(learner_id)


@app.get("/api/learner/{learner_id}/recommendation")
def recommendation(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    check_learner_access(learner_id, current_user)
    state = get_state(learner_id)
    concepts = list_concepts()
    # Find lowest mastery concept or first concept with incomplete progress
    prog = get_concept_progress(learner_id)
    for c in concepts:
        cp = prog.get(c["id"])
        if not cp or cp["mastery"] < 0.70:
            probs = list_problems(c["id"])
            p = probs[0] if probs else {"id": 1, "title": "Sum of an Array"}
            return {
                "learner_id": learner_id,
                "next_problem_id": p["id"],
                "next_problem_title": p.get("title", ""),
                "next_concept_id": c["id"],
                "topic": c["title"],
                "difficulty": c["difficulty"],
                "reason": f"Reinforce your understanding of '{c['title']}' based on your recent performance profile."
            }
    return {
        "learner_id": learner_id,
        "next_problem_id": 1,
        "next_concept_id": "variables",
        "topic": "Python Review",
        "difficulty": "easy",
        "reason": "Great work! You have made progress across the curriculum. Review or attempt custom problems."
    }


@app.get("/api/learner/{learner_id}/hints/{problem_id}")
def learner_problem_hints(learner_id: str, problem_id: int, current_user: Optional[dict] = Depends(get_optional_user)) -> list[dict]:
    check_learner_access(learner_id, current_user)
    return get_problem_hints(learner_id, problem_id)


def _generate_progressive_hint_content(problem: dict, level: int, code: str = "") -> str:
    """
    Generate progressive pedagogical hints (Phase 3.3):
    - Level 1: Subtle conceptual nudge / guiding question.
    - Level 2: Specific direction, constraints, and relevant functions/formula.
    - Level 3: Stronger clue, partial approach, and pseudocode.
    - Level 4: Complete step-by-step logic explanation and walkthrough.
    """
    title = problem.get("title", "")
    topic = problem.get("topic") or problem.get("concept_id") or "Python"
    expected = problem.get("expected_behavior", "")

    if level == 1:
        if "sum" in title.lower():
            return "Consider the accumulation pattern: how do you keep track of a total value as you examine each item in a collection?"
        if "max" in title.lower() or "largest" in title.lower():
            return "Think about keeping a 'current best' variable as you inspect elements one by one. How should you safely initialize it?"
        if "palindrome" in title.lower():
            return "A palindrome reads the same forwards and backwards. What transformations (casing, spaces) should happen before comparing?"
        if "vowel" in title.lower():
            return "What constitutes a vowel in both lowercase and uppercase? How can Python quickly check if a character belongs to a group?"
        if "two sum" in title.lower():
            return "If you are looking for two numbers that add up to a target, what arithmetic relationship connects each number to its partner?"
        return f"Reflect on the core objective of '{title}': what is the primary invariant or transformation required on the input?"

    elif level == 2:
        if "sum" in title.lower():
            return "Initialize a counter (e.g. `total = 0`) before your loop. In each step, add the current item: `total += item`. Ensure you return `total` only after the loop ends."
        if "max" in title.lower() or "largest" in title.lower():
            return "Initialize `max_val = numbers[0]` (rather than 0, so it handles negative numbers). If a number is greater than `max_val`, update it: `if num > max_val: max_val = num`."
        if "palindrome" in title.lower():
            return "First sanitize the input: `cleaned = ''.join(c.lower() for c in text if c.isalnum())`. Then check if `cleaned == cleaned[::-1]`."
        if "vowel" in title.lower():
            return "Define `vowels = set('aeiouAEIOU')`. Loop through each character in the text and check `if char in vowels: count += 1`. Return `count`."
        if "two sum" in title.lower():
            return "For each number `num`, calculate `needed = target - num`. Use a dictionary to store `{num: index}` for each number seen so far."
        return f"Direction for {title}: Review the expected behavior `{expected}`. Check boundary cases such as empty inputs or single-element inputs."

    elif level == 3:
        if "sum" in title.lower():
            return (
                "Pseudocode Approach:\n"
                "1. total = 0\n"
                "2. for number in arr:\n"
                "       total = total + number\n"
                "3. return total\n\n"
                "*Tip:* Alternatively, Python's built-in `sum(arr)` accomplishes this in linear time."
            )
        if "max" in title.lower():
            return (
                "Pseudocode Approach:\n"
                "1. if not numbers: return None\n"
                "2. current_max = numbers[0]\n"
                "3. for val in numbers[1:]:\n"
                "       if val > current_max:\n"
                "           current_max = val\n"
                "4. return current_max"
            )
        if "palindrome" in title.lower():
            return (
                "Pseudocode Approach:\n"
                "1. cleaned = ''.join(c.lower() for c in text if c.isalnum())\n"
                "2. return cleaned == cleaned[::-1]"
            )
        if "two sum" in title.lower():
            return (
                "Pseudocode Approach:\n"
                "1. seen = {}\n"
                "2. for i, num in enumerate(numbers):\n"
                "       diff = target - num\n"
                "       if diff in seen:\n"
                "           return [seen[diff], i]\n"
                "       seen[num] = i\n"
                "3. return None"
            )
        return (
            f"Pseudocode Structure for {title}:\n"
            "1. Validate input parameters and handle empty/edge cases.\n"
            "2. Initialize state accumulator or container.\n"
            "3. Perform step-by-step traversal.\n"
            "4. Return the aggregated or transformed result."
        )

    else:
        return (
            f"### Complete Solution Logic Walkthrough for '{title}'\n\n"
            f"**1. Problem Invariant:** The function must satisfy `{expected}`.\n"
            "**2. Step-by-Step Logic:**\n"
            "- **Initialization:** Declare variables to store the intermediate result before any looping starts.\n"
            "- **Traversal:** Inspect each item sequentially. Be careful not to return prematurely inside the loop body!\n"
            "- **State Transformation:** Apply the required arithmetic, comparison, or string operation.\n"
            "- **Output Return:** After completing the traversal, return the final accumulated result.\n"
            "**3. Complexity Analysis:** This solution runs in $O(n)$ time using $O(1)$ extra memory."
        )


@app.post("/api/hint/progressive")
def request_progressive_hint(payload: ProgressiveHintRequest, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """Phase 3.3: Dynamic progressive hint ladder (Hint 1: Nudge -> Hint 2: Direction -> Hint 3: Pseudocode -> Level 4: Walkthrough)."""
    check_learner_access(payload.learner_id, current_user)
    problem = get_problem(payload.problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found.")

    level = max(1, min(4, payload.level))
    focus_map = {1: "Conceptual Nudge", 2: "Specific Direction", 3: "Pseudocode Approach", 4: "Solution Walkthrough"}
    focus = focus_map.get(level, "Conceptual")

    hint_text = _generate_progressive_hint_content(problem, level, payload.code)

    # Persist hint to SQLite
    try:
        save_hint(
            learner_id=payload.learner_id,
            problem_id=payload.problem_id,
            level=level,
            hint_text=hint_text,
            focus=focus
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "level": level,
        "title": f"Hint {level}: {focus}",
        "hint": hint_text,
        "focus": focus,
        "max_level": 4,
        "problem_id": payload.problem_id
    }


# --- 6. SESSION MANAGEMENT & TRACKING ---

class SessionStartRequest(BaseModel):
    learner_id: str


@app.post("/api/sessions/start")
def session_start(payload: SessionStartRequest, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    check_learner_access(payload.learner_id, current_user)
    return start_learning_session(payload.learner_id)


@app.post("/api/sessions/{session_id}/end")
def session_end(session_id: int, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Ending a learning session requires a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    session = get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if current_user.get("role") != "teacher" and current_user.get("uid") != session["learner_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You cannot end another learner's session."
        )
    res = end_learning_session(session_id)
    return {"status": "ok", "session_id": session_id, "session": res}


@app.get("/api/sessions/{learner_id}")
def session_list(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> list[dict]:
    check_learner_access(learner_id, current_user)
    return get_learning_sessions(learner_id)


# --- 7. MULTI-TURN CONVERSATIONAL AI TUTOR ---

@app.get("/api/chat/{learner_id}")
def chat_history(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> list[dict]:
    check_learner_access(learner_id, current_user)
    return get_chat_history(learner_id)


@app.post("/api/chat")
def chat(payload: ChatRequest, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    check_learner_access(payload.learner_id, current_user)
    # Save student message
    save_chat_message(
        learner_id=payload.learner_id,
        role="user",
        content=payload.message,
        problem_id=payload.problem_id
    )

    # Fetch recent conversation context (last 6 messages)
    prev_messages = get_chat_history(payload.learner_id, limit=6)
    history_context = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in prev_messages[:-1])

    # Check if this is problem-specific or general Python inquiry
    current_problem = get_problem(payload.problem_id) if payload.problem_id else None

    # R-26: Fetch learner cognitive state and inject pedagogical profile into chat context
    learner_st = get_state(payload.learner_id)
    mastery_val = learner_st.get("mastery", 0.35)
    conf_val = learner_st.get("confidence", 0.5)
    load_val = learner_st.get("cognitive_load", 0.3)
    fails_val = learner_st.get("consecutive_fails", 0)

    learner_profile_instruction = (
        f"Learner Profile Context: Mastery={mastery_val:.2f}, Confidence={conf_val:.2f}, "
        f"Cognitive Load={load_val:.2f}, Consecutive Failures={fails_val}. "
        f"Pedagogical Tone: {'The student is experiencing high difficulty or cognitive load. Provide extra encouragement, break concepts into small intuitive steps, and avoid technical jargon.' if (conf_val < 0.4 or fails_val >= 2 or load_val > 0.6) else 'The student is confident and progressing well. Challenge them with conceptual depth.'}\n"
    )

    if current_problem:
        prob_context = f"Current Problem: {current_problem['title']} - {current_problem['description']}\nExpected: {current_problem.get('expected_behavior', '')}\n"
    else:
        prob_context = "No specific problem active; student is asking a general Python question.\n"

    system_prompt = (
        "You are an encouraging, expert Python AI tutor. "
        f"{learner_profile_instruction}"
        "If the student asks a general Python question (e.g. explaining data types, loops, syntax, or concepts), provide a clear, insightful explanation with a short code example. "
        "If the student asks about solving their current coding problem, give a Socratic hint or guiding clue without writing the complete solution directly."
    )

    prompt = (
        f"{prob_context}"
        f"Recent Conversation:\n{history_context}\n\n"
        f"Student Question: {payload.message}"
    )

    fallback = generate_contextual_socratic_fallback(
        message=payload.message,
        problem=current_problem,
        learner_state=learner_st
    )

    reply = llm.tutor_reply(prompt, fallback, system_prompt=system_prompt)

    # Save tutor response
    save_chat_message(
        learner_id=payload.learner_id,
        role="assistant",
        content=reply,
        problem_id=payload.problem_id
    )

    return {
        "mode": llm.mode,
        "reply": reply
    }


# --- 7. EVALUATION METRICS ENGINE ---

@app.get("/api/metrics/{learner_id}")
def evaluation_metrics(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """Calculate and return research evaluation metrics from actual database interaction records."""
    check_learner_access(learner_id, current_user)
    attempts = history(learner_id)
    total_attempts = len(attempts)
    solved = len([a for a in attempts if a["passed"]])
    failed = total_attempts - solved
    total_hints = sum(a.get("hints_used", 0) for a in attempts)
    times = [a.get("response_time", 0.0) for a in attempts if a.get("response_time", 0.0) > 0]
    avg_time = round(sum(times) / len(times), 1) if times else 0.0

    task_completion_rate = round(solved / total_attempts, 2) if total_attempts else 0.0
    avg_hints_per_problem = round(total_hints / max(1, len({a["problem_id"] for a in attempts})), 2) if attempts else 0.0
    hint_efficiency = round(solved / max(1, total_hints), 2) if total_hints else 1.0

    # Calculate Learning Gain: R-15 / C-07 resolution
    # Grounded against the calibrated BKT prior P(L0)=0.20 rather than an arbitrary 0.35 constant
    st = get_state(learner_id)
    current_mastery = float(st.get("mastery", 0.20))
    bkt_prior = 0.20
    model_estimated_mastery_gain = round(max(0.0, current_mastery - bkt_prior) / (1.0 - bkt_prior), 2)
    learning_gain = model_estimated_mastery_gain

    latest_db_metric = get_latest_metrics(learner_id)
    satisfaction = latest_db_metric.get("satisfaction_score") if latest_db_metric else None

    # Persist updated calculation
    save_evaluation_metric(
        learner_id=learner_id,
        learning_gain=learning_gain,
        hint_efficiency=hint_efficiency,
        avg_hints_per_problem=avg_hints_per_problem,
        task_completion_rate=task_completion_rate,
        time_to_completion=avg_time,
        satisfaction_score=satisfaction
    )

    return {
        "learner_id": learner_id,
        "learning_gain": learning_gain,
        "model_estimated_mastery_gain": model_estimated_mastery_gain,
        "hint_efficiency": hint_efficiency,
        "avg_hints_per_problem": avg_hints_per_problem,
        "task_completion_rate": task_completion_rate,
        "time_to_completion": avg_time,
        "satisfaction_score": satisfaction,
        "total_attempts": total_attempts,
        "problems_solved": solved
    }


@app.post("/api/metrics/satisfaction")
def submit_satisfaction(payload: SatisfactionRequest, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    check_learner_access(payload.learner_id, current_user)
    current = evaluation_metrics(payload.learner_id, current_user=current_user)
    save_evaluation_metric(
        learner_id=payload.learner_id,
        learning_gain=current["learning_gain"],
        hint_efficiency=current["hint_efficiency"],
        avg_hints_per_problem=current["avg_hints_per_problem"],
        task_completion_rate=current["task_completion_rate"],
        time_to_completion=current["time_to_completion"],
        satisfaction_score=payload.score
    )
    return {"status": "ok", "satisfaction_score": payload.score}


# --- 8. LONGITUDINAL ANALYTICS & REFLECTION (R-03, R-13, R-18, R-25) ---

@app.get("/api/learner/{learner_id}/state-history")
@app.get("/api/learner/{learner_id}/cognitive-history")
def learner_state_history(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """R-13: Fetch longitudinal cognitive state history and ranked weak topics for student dashboard."""
    check_learner_access(learner_id, current_user)
    history_records = get_state_history(learner_id, limit=50)
    weak_topics = get_weakest_concepts(learner_id, limit=5)
    return {
        "learner_id": learner_id,
        "state_history": history_records,
        "weak_topics": weak_topics
    }


@app.get("/api/learner/{learner_id}/misconceptions")
def learner_misconceptions(learner_id: str, current_user: Optional[dict] = Depends(get_optional_user)) -> list[dict]:
    """R-03: Retrieve recurring misconception pattern tracking for the learner."""
    check_learner_access(learner_id, current_user)
    return get_learner_misconceptions(learner_id)


@app.post("/api/reflection/submit")
def submit_reflection(payload: ReflectionSubmitRequest, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """R-25: Capture and persist student metacognitive reflection answer."""
    check_learner_access(payload.learner_id, current_user)
    record = save_reflection_response(
        learner_id=payload.learner_id,
        problem_id=payload.problem_id,
        prompt_text=payload.prompt_text,
        response_text=payload.response_text,
        session_id=payload.session_id
    )
    return {"status": "ok", "reflection": record}


@app.post("/api/metrics/survey")
def submit_survey(payload: SurveySubmitRequest, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """R-18: Multi-item Likert survey evaluating usefulness, clarity, hint adequacy, and adaptivity."""
    check_learner_access(payload.learner_id, current_user)
    record = save_satisfaction_survey(
        learner_id=payload.learner_id,
        session_id=payload.session_id,
        usefulness_score=payload.usefulness_score,
        clarity_score=payload.clarity_score,
        hint_adequacy_score=payload.hint_adequacy_score,
        perceived_adaptivity_score=payload.perceived_adaptivity_score,
        comments=payload.comments or ""
    )
    return {"status": "ok", "survey": record}


# --- 9. DIAGNOSTIC PLACEMENT ASSESSMENT (R-24, F-01) ---

@app.get("/api/assessment/placement")
def placement_quiz() -> list[dict]:
    """R-24: Retrieve diagnostic placement quiz questions for initial student onboarding."""
    return get_placement_quiz()


@app.post("/api/assessment/placement/submit")
def submit_placement(payload: PlacementSubmitRequest, current_user: Optional[dict] = Depends(get_optional_user)) -> dict:
    """R-24: Evaluate placement quiz and calibrate learner's initial BKT priors per concept area."""
    check_learner_access(payload.learner_id, current_user)
    result = evaluate_placement_answers(payload.answers)
    
    # Calibrate initial mastery priors in database
    from .database import update_concept_progress_db
    for concept_id, prior_val in result["concept_priors"].items():
        try:
            update_concept_progress_db(
                learner_id=payload.learner_id,
                concept_id=concept_id,
                mastery=prior_val,
                confidence=0.70 if prior_val > 0.5 else 0.40,
                confusion=0.10 if prior_val > 0.5 else 0.40,
                cognitive_load=0.20,
                passed=(prior_val > 0.5),
                hints=0
            )
        except Exception:
            pass

    return {
        "status": "ok",
        "result": result
    }
