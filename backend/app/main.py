"""FastAPI main application router for the Adaptive Multi-Agent AI Tutoring System."""
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Security, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

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
)
from .graph.tutor_graph import tutor_graph
from .services.code_runner import evaluate
from .services.llm_service import llm
from .services.vector_store import vector_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="Adaptive Multi-Agent AI Tutoring Platform", lifespan=lifespan)

# Standardized CORS permissions
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REQUEST & RESPONSE SCHEMAS ---

class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=4, max_length=100)
    role: str = Field(default="student")


class LoginRequest(BaseModel):
    email: str
    password: str


class Submission(BaseModel):
    learner_id: str = Field(min_length=1, max_length=80)
    problem_id: int
    code: str = Field(min_length=1, max_length=15000)
    response_time: float = Field(default=0.0, ge=0.0, le=86400.0)


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
    user_id = f"user-{uuid.uuid4().hex[:8]}"
    pwd_hash = hash_password(payload.password)
    user = create_user(user_id=user_id, name=payload.name, email=payload.email, password_hash=pwd_hash, role=payload.role)
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
def run_code(payload: Submission) -> dict:
    item = get_problem(payload.problem_id)
    if not item:
        raise HTTPException(status_code=404, detail="Problem not found.")
    execution = evaluate(payload.code, payload.problem_id)
    return {"execution": execution}


@app.post("/api/submit")
def submit(payload: Submission) -> dict:
    item = get_problem(payload.problem_id)
    if not item:
        raise HTTPException(status_code=404, detail="Problem not found.")

    # 1. Evaluate code in isolated sandbox
    execution = evaluate(payload.code, payload.problem_id)

    # 2. Invoke 6-Agent LangGraph Engine
    prior = get_state(payload.learner_id)
    graph_input = {
        "learner_id": payload.learner_id,
        "problem": item,
        "code": payload.code,
        "response_time": payload.response_time,
        "execution": execution,
        "prior_state": prior,
        "agent_activity": []
    }
    result = tutor_graph.invoke(graph_input)

    # 3. Persist attempt and updated state
    save_attempt_and_state(
        learner_id=payload.learner_id,
        problem_id=payload.problem_id,
        code=payload.code,
        passed=execution["passed"],
        error_type=result["diagnostic"]["error_type"],
        state=result["learner_state"],
        concept_id=result.get("concept_id", item.get("concept_id")),
        response_time=payload.response_time,
        scaffolding_level=result.get("scaffolding", {}).get("level", 1),
        hints_used=result["learner_state"].get("hints_used", 0)
    )

    return {
        "mode": llm.mode,
        "execution": execution,
        "diagnostic": result["diagnostic"],
        "learner_state": result["learner_state"],
        "similar_learners": result.get("similar_learners", []),
        "scaffolding": result.get("scaffolding", {}),
        "reflection": result.get("reflection", ""),
        "recommendation": result.get("recommendation", {}),
        "agent_activity": result.get("agent_activity", [])
    }


# --- 5. LEARNER PROFILE, HISTORY & DASHBOARD ---

@app.get("/api/learner/{learner_id}")
def learner(learner_id: str) -> dict:
    return get_state(learner_id)


@app.get("/api/learner/{learner_id}/progress")
def learner_concept_progress(learner_id: str) -> dict:
    return get_concept_progress(learner_id)


@app.get("/api/progress/concepts/{learner_id}")
def learner_concept_progress_alias(learner_id: str) -> list[dict]:
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
def learner_history(learner_id: str) -> list[dict]:
    return history(learner_id)


@app.get("/api/history/{learner_id}")
def learner_history_alias(learner_id: str) -> list[dict]:
    return history(learner_id)


@app.get("/api/learner/{learner_id}/recommendation")
def recommendation(learner_id: str) -> dict:
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


# --- 6. MULTI-TURN CONVERSATIONAL AI TUTOR ---

@app.get("/api/chat/{learner_id}")
def chat_history(learner_id: str) -> list[dict]:
    return get_chat_history(learner_id)


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict:
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

    if current_problem:
        prob_context = f"Current Problem: {current_problem['title']} - {current_problem['description']}\nExpected: {current_problem.get('expected_behavior', '')}\n"
    else:
        prob_context = "No specific problem active; student is asking a general Python question.\n"

    system_prompt = (
        "You are an encouraging, expert Python AI tutor. "
        "If the student asks a general Python question (e.g. explaining data types, loops, syntax, or concepts), provide a clear, insightful explanation with a short code example. "
        "If the student asks about solving their current coding problem, give a Socratic hint or guiding clue without writing the complete solution directly."
    )

    prompt = (
        f"{prob_context}"
        f"Recent Conversation:\n{history_context}\n\n"
        f"Student Question: {payload.message}"
    )

    fallback = (
        "Python offers clear and readable syntax for this concept. "
        "Try isolating a small 2-line test example in your terminal, and observe how variable states change."
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
def evaluation_metrics(learner_id: str) -> dict:
    """Calculate and return research evaluation metrics from actual database interaction records."""
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

    # Calculate Learning Gain (G) = (Post - Pre) / (1 - Pre)
    # Estimate Pre-test from initial attempts and Post-test from recent mastery
    st = get_state(learner_id)
    current_mastery = float(st.get("mastery", 0.35))
    pre_mastery = 0.35
    learning_gain = round((current_mastery - pre_mastery) / max(0.05, 1.0 - pre_mastery), 2)

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
        "hint_efficiency": hint_efficiency,
        "avg_hints_per_problem": avg_hints_per_problem,
        "task_completion_rate": task_completion_rate,
        "time_to_completion": avg_time,
        "satisfaction_score": satisfaction,
        "total_attempts": total_attempts,
        "problems_solved": solved
    }


@app.post("/api/metrics/satisfaction")
def submit_satisfaction(payload: SatisfactionRequest) -> dict:
    current = evaluation_metrics(payload.learner_id)
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
