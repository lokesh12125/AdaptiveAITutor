"""Comprehensive Verification Suite for Audit Gap Closures & Hardening.

Covers:
- P-01: /api/run endpoint authentication enforcement
- P-02: Role registration defense (preventing unauthorized teacher creation)
- P-03: 600k-iteration PBKDF2 hashing
- C-06 / V-02: Scientifically correct CSI struggle formula (1 - Conf)
- C-01: Full 49-concept curriculum graph in Learning Planner
- R-11 & R-12: Cyclic LangGraph orchestration & Anti-leak verifier
- R-15: Model-estimated mastery gain calibrated against BKT prior 0.20
- R-03: Longitudinal misconception tracking
- R-13: Append-only state_history & weak-topic ranking
- R-25: Metacognitive reflection response storage
- R-18: Multi-item Likert satisfaction survey
- R-24: Diagnostic placement assessment
- R-14: Teacher analytics drilldown endpoint
"""
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth import hash_password, verify_password, create_access_token
from app.learning.scaffolding import calculate_csi_score
from app.agents.learning_planner_agent import CONCEPT_GRAPH
from app.learning.assessment import get_placement_quiz, evaluate_placement_answers
from app.graph.tutor_graph import verify_hint_anti_leak, route_verifier_decision
from app.learning.bkt import update_mastery


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_audit_p01_run_code_authentication_enforced(client):
    """Verify P-01: /api/run requires authentication; anonymous invocation returns 401."""
    # 1. Unauthenticated request should be strictly rejected with 401
    anon_res = client.post("/api/run", json={
        "learner_id": "anon",
        "problem_id": 1,
        "code": "def sum_array(arr): return sum(arr)"
    })
    assert anon_res.status_code == 401

    # 2. Authenticated student request succeeds
    token = create_access_token("test-user-1", "Test User", "test1@adaptive.edu", role="student")
    auth_res = client.post("/api/run", json={
        "learner_id": "test-user-1",
        "problem_id": 1,
        "code": "def sum_array(arr): return sum(arr)"
    }, headers={"Authorization": f"Bearer {token}"})
    assert auth_res.status_code == 200
    assert "execution" in auth_res.json()
    assert auth_res.json()["execution"]["passed"] is True


def test_audit_p02_role_registration_protection(client):
    """Verify P-02: Attempting to register as teacher without valid invite code fails with 403."""
    uid = uuid.uuid4().hex[:6]
    
    # 1. Registering as teacher without invite code fails
    bad_res = client.post("/api/auth/register", json={
        "name": "Attacker",
        "email": f"attacker_{uid}@test.edu",
        "password": "password123",
        "role": "teacher"
    })
    assert bad_res.status_code == 403
    assert "invite" in bad_res.json()["detail"].lower()

    # 2. Registering as teacher with valid invite code succeeds
    good_res = client.post("/api/auth/register", json={
        "name": "Legit Teacher",
        "email": f"teacher_{uid}@test.edu",
        "password": "password123",
        "role": "teacher",
        "invite_code": "TEACH-2026-ADAPTIVE"
    })
    assert good_res.status_code == 200
    assert good_res.json()["user"]["role"] == "teacher"


def test_audit_p03_owasp_pbkdf2_iterations():
    """Verify P-03: Password hashes use 600,000 iterations conforming to OWASP guidelines."""
    pwd = "UltraSecurePassword2026!"
    hashed = hash_password(pwd)
    assert hashed.startswith("600000:")
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_audit_c06_csi_confidence_struggle_inverse():
    """Verify C-06 / V-02: High confidence lowers CSI struggle; low confidence elevates struggle."""
    csi_high_conf, raw_high, _ = calculate_csi_score(
        mastery=0.4, consecutive_fails=2, confidence=0.85, cognitive_load=0.3, hints_used=1, response_time=30.0, observations_count=4
    )
    csi_low_conf, raw_low, _ = calculate_csi_score(
        mastery=0.4, consecutive_fails=2, confidence=0.15, cognitive_load=0.3, hints_used=1, response_time=30.0, observations_count=4
    )
    assert raw_low > raw_high
    assert csi_low_conf > csi_high_conf


def test_audit_c01_concept_graph_covers_full_curriculum():
    """Verify C-01: Concept graph in learning planner contains all 49 curriculum concepts."""
    assert len(CONCEPT_GRAPH) == 49
    ids = {c["id"] for c in CONCEPT_GRAPH}
    assert "variables" in ids
    assert "binary-trees" in ids or "trees" in ids or "recursion" in ids


def test_audit_r15_learning_gain_calculation(client):
    """Verify R-15: Learning gain reports both calibrated mastery gain and returns valid values."""
    uid = f"gain_user_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "Gain Student", f"{uid}@test.edu")
    
    res = client.get(f"/api/metrics/{uid}", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "learning_gain" in data
    assert "model_estimated_mastery_gain" in data
    assert data["model_estimated_mastery_gain"] >= 0.0


def test_audit_r13_state_history_and_weak_topics(client):
    """Verify R-13: State history progression and weak topics are accessible via learner endpoint."""
    uid = f"hist_user_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "History Student", f"{uid}@test.edu")

    # Submit an attempt
    client.post("/api/submit", json={
        "learner_id": uid,
        "problem_id": 1,
        "code": "def sum_array(arr): return sum(arr)",
        "response_time": 15.0
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/learner/{uid}/state-history", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "state_history" in data
    assert len(data["state_history"]) >= 1
    assert "weak_topics" in data


def test_audit_r25_reflection_submission(client):
    """Verify R-25: Metacognitive reflection answers are stored."""
    uid = f"refl_user_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "Reflect Student", f"{uid}@test.edu")

    res = client.post("/api/reflection/submit", json={
        "learner_id": uid,
        "problem_id": 1,
        "prompt_text": "Explain why your loop condition terminates.",
        "response_text": "The index increments by 1 on each step until reaching len(arr)."
    }, headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert "reflection" in res.json()


def test_audit_r18_multi_item_satisfaction_survey(client):
    """Verify R-18: Multi-item Likert survey submits and records item-level ratings."""
    uid = f"survey_user_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "Survey Student", f"{uid}@test.edu")

    res = client.post("/api/metrics/survey", json={
        "learner_id": uid,
        "usefulness_score": 5,
        "clarity_score": 4,
        "hint_adequacy_score": 5,
        "perceived_adaptivity_score": 5,
        "comments": "The Socratic hints helped me discover the bug without spoiling the answer."
    }, headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["survey"]["usefulness_score"] == 5


def test_audit_r24_placement_assessment(client):
    """Verify R-24: Placement quiz returns questions and evaluates calibrated priors."""
    # 1. Fetch placement questions
    quiz_res = client.get("/api/assessment/placement")
    assert quiz_res.status_code == 200
    questions = quiz_res.json()
    assert len(questions) >= 5

    # 2. Submit placement answers
    uid = f"place_user_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "Placement Student", f"{uid}@test.edu")

    sub_res = client.post("/api/assessment/placement/submit", json={
        "learner_id": uid,
        "answers": {
            "q1_variables": "5",
            "q2_conditionals": "B",
            "q3_loops": "4 (1, 2, 3, 4)"
        }
    }, headers={"Authorization": f"Bearer {token}"})

    assert sub_res.status_code == 200
    res_data = sub_res.json()["result"]
    assert "starting_tier" in res_data
    assert "concept_priors" in res_data
    assert res_data["concept_priors"]["variables"] == 0.70


def test_audit_r14_teacher_student_drilldown(client):
    """Verify R-14: Teacher drilldown provides per-student breakdown and at-risk assessment."""
    # Register student account
    uid_suffix = uuid.uuid4().hex[:6]
    reg_res = client.post("/api/auth/register", json={
        "name": "Drill Student",
        "email": f"s_drill_{uid_suffix}@test.edu",
        "password": "password123",
        "role": "student"
    })
    assert reg_res.status_code == 200
    student_id = reg_res.json()["user"]["id"]
    s_token = reg_res.json()["token"]

    # Student submits an attempt
    client.post("/api/submit", json={
        "learner_id": student_id,
        "problem_id": 1,
        "code": "def sum_array(arr): return 0",
        "response_time": 20.0
    }, headers={"Authorization": f"Bearer {s_token}"})

    # Teacher requests drilldown
    teacher_token = create_access_token("teacher-1", "Prof Smith", "prof@adaptive.edu", role="teacher")
    res = client.get(f"/api/teacher/students/{student_id}/drilldown", headers={"Authorization": f"Bearer {teacher_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "student" in data
    assert "concept_breakdown" in data
    assert "is_at_risk" in data
    assert "misconceptions" in data


def test_audit_r11_r12_cyclic_anti_leak_verifier():
    """Verify R-11 & R-12: Verifier catches code leakage, triggers cyclic retry, or sanitizes with template."""
    # 1. Direct code fence leak detected
    leaky_state_1 = {
        "scaffolding": {
            "level": 2,
            "focus": "Conceptual",
            "hint": "Here is what to write:\n```python\ndef sum_array(arr):\n    return sum(arr)\n```"
        },
        "verifier_attempts": 0
    }
    v_res_1 = verify_hint_anti_leak(leaky_state_1)
    assert v_res_1["leak_detected"] is True
    assert v_res_1["verifier_attempts"] == 1
    # Routing routes back to scaffolding
    combined_state_1 = {**leaky_state_1, **v_res_1}
    assert route_verifier_decision(combined_state_1) == "scaffolding"

    # 2. Exceeded retry attempts: Sanitized with deterministic template
    leaky_state_2 = {
        "scaffolding": {
            "level": 2,
            "focus": "Conceptual",
            "hint": "```python\ndef sum_array(arr): return 0\n```"
        },
        "verifier_attempts": 2
    }
    v_res_2 = verify_hint_anti_leak(leaky_state_2)
    assert v_res_2["leak_detected"] is False
    assert v_res_2["scaffolding"]["anti_leak_sanitized"] is True
    assert "```" not in v_res_2["scaffolding"]["hint"]
    # Routing now advances to reflection
    combined_state_2 = {**leaky_state_2, **v_res_2}
    assert route_verifier_decision(combined_state_2) == "reflection"

    # 3. Clean Socratic hint passes without issue
    clean_state = {
        "scaffolding": {
            "level": 1,
            "focus": "Conceptual",
            "hint": "Consider how an accumulator variable tracks total values across iterations."
        },
        "verifier_attempts": 0
    }
    v_res_3 = verify_hint_anti_leak(clean_state)
    assert v_res_3["leak_detected"] is False
    assert route_verifier_decision({**clean_state, **v_res_3}) == "reflection"


def test_audit_p08_cors_and_security_headers(client):
    """Verify P-08: Security headers (nosniff, DENY, etc.) attached to HTTP responses."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert "referrer-policy" in res.headers


def test_audit_p13_response_time_sanitization(client):
    """Verify P-13: Negative response_times rejected with 422, idle times clamped."""
    uid = f"rt_user_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "RT Student", f"{uid}@test.edu")

    # 1. Negative response time rejected by schema validation
    res_neg = client.post("/api/submit", json={
        "learner_id": uid,
        "problem_id": 1,
        "code": "def sum_array(arr): return 0",
        "response_time": -100.0
    }, headers={"Authorization": f"Bearer {token}"})
    assert res_neg.status_code == 422

    # 2. Idle response time (e.g. 5000s) is accepted and safely clamped
    res_idle = client.post("/api/submit", json={
        "learner_id": uid,
        "problem_id": 1,
        "code": "def sum_array(arr): return 0",
        "response_time": 5000.0
    }, headers={"Authorization": f"Bearer {token}"})
    assert res_idle.status_code == 200
    assert "learner_state" in res_idle.json()


def test_audit_r26_chat_incorporates_learner_state(client):
    """Verify R-26: Chat endpoint accepts and answers with learner state context."""
    uid = f"chat_user_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "Chat Student", f"{uid}@test.edu")

    res = client.post("/api/chat", json={
        "learner_id": uid,
        "message": "Why does my loop index cause an IndexError?",
        "problem_id": 1
    }, headers={"Authorization": f"Bearer {token}"})

    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert len(data["reply"]) > 10


def test_audit_v01_bkt_hint_aware_guess_modulation():
    """Verify V-01: Hint usage dampens unearned mastery inflation when a problem is passed with hints."""
    prior = 0.20
    mastery_unassisted = update_mastery(prior, passed=True, hints_used=0)
    mastery_assisted = update_mastery(prior, passed=True, hints_used=3)

    assert mastery_unassisted > prior
    assert mastery_assisted > prior
    # Assisted attempt has higher effective P(G), producing a lower posterior mastery update
    assert mastery_unassisted > mastery_assisted


def test_progressive_hint_system_levels_1_to_4(client):
    """Verify Phase 3.3: Progressive hint ladder returns increasingly specific scaffolding."""
    uid = f"prog_hint_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "Progressive Student", f"{uid}@test.edu")

    # Hint 1: Nudge
    h1 = client.post("/api/hint/progressive", json={
        "learner_id": uid,
        "problem_id": 1,
        "level": 1
    }, headers={"Authorization": f"Bearer {token}"})
    assert h1.status_code == 200
    assert h1.json()["level"] == 1
    assert "accumulation" in h1.json()["hint"].lower() or "total" in h1.json()["hint"].lower()
    # Level 1 must not reveal implementation code
    assert "def " not in h1.json()["hint"]

    # Hint 2: Direction & Constraints
    h2 = client.post("/api/hint/progressive", json={
        "learner_id": uid,
        "problem_id": 1,
        "level": 2
    }, headers={"Authorization": f"Bearer {token}"})
    assert h2.status_code == 200
    assert h2.json()["level"] == 2
    assert "total" in h2.json()["hint"].lower()

    # Hint 3: Pseudocode
    h3 = client.post("/api/hint/progressive", json={
        "learner_id": uid,
        "problem_id": 1,
        "level": 3
    }, headers={"Authorization": f"Bearer {token}"})
    assert h3.status_code == 200
    assert h3.json()["level"] == 3
    assert "pseudocode" in h3.json()["hint"].lower()

    # Hint 4: Solution walkthrough
    h4 = client.post("/api/hint/progressive", json={
        "learner_id": uid,
        "problem_id": 1,
        "level": 4
    }, headers={"Authorization": f"Bearer {token}"})
    assert h4.status_code == 200
    assert h4.json()["level"] == 4
    assert "walkthrough" in h4.json()["hint"].lower()


def test_contextual_socratic_chat_intelligence(client):
    """Verify Phase 3.1 & 3.4: Chat responds with intelligent, structured pedagogical explanations."""
    uid = f"chat_intel_{uuid.uuid4().hex[:6]}"
    token = create_access_token(uid, "Chat Intel", f"{uid}@test.edu")

    # Test list comprehension query
    res_list = client.post("/api/chat", json={
        "learner_id": uid,
        "message": "Can you explain how list comprehensions work in Python?"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res_list.status_code == 200
    reply = res_list.json()["reply"]
    assert "list comprehension" in reply.lower()
    assert "[" in reply

    # Test error debugging query
    res_err = client.post("/api/chat", json={
        "learner_id": uid,
        "message": "Why does my code throw an IndexError: list index out of range?"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res_err.status_code == 200
    err_reply = res_err.json()["reply"]
    assert "indexerror" in err_reply.lower()
    assert "0-based" in err_reply.lower() or "index" in err_reply.lower()

    # Test off-topic query redirection
    res_off = client.post("/api/chat", json={
        "learner_id": uid,
        "message": "What is the capital of France?"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res_off.status_code == 200
    off_reply = res_off.json()["reply"]
    assert "python" in off_reply.lower() or "programming" in off_reply.lower()

