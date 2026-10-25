# Adaptive Multi-Agent AI Tutoring System
### Cognitive-State Guided Multi-Agent Adaptive Scaffolding Framework (CSMASF)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-FF6F00.svg)](https://www.langchain.com/langgraph)
[![React](https://img.shields.io/badge/Frontend-React%2019-61DAFB.svg)](https://react.dev/)
[![ChromaDB](https://img.shields.io/badge/Vector%20Store-ChromaDB-purple.svg)](https://www.trychroma.com/)
[![Tests](https://img.shields.io/badge/Pytest-54%20Passed-success.svg)]()

---

## 1. Executive Summary & Overview

The **Adaptive Multi-Agent AI Tutoring System** is an intelligent, personalized computer science learning platform designed to guide students through Python programming mastery. Grounded in the **Cognitive-State Guided Multi-Agent Adaptive Scaffolding Framework (CSMASF)**, the system orchestrates 6 specialized AI agents to deliver real-time Socratic guidance, model conceptual understanding, regulate cognitive load, match students with peer intervention archetypes, and provide personalized next-step learning trajectories without prematurely leaking complete solutions.

### Core Architectural Capabilities
- **6-Agent LangGraph Orchestration**: Decentralized, modular agent workflow coordinating diagnosis, cognitive modeling, vector similarity search, adaptive scaffolding, metacognitive reflection, and curriculum planning.
- **Bayesian Knowledge Tracing (BKT)**: Probabilistic mastery estimation based on Corbett & Anderson's classical formulation ($P(L_0), P(T), P(G), P(S)$).
- **Behavioral Cognitive State Modeling (EWMA)**: Real-time tracking of learner confidence, confusion, and cognitive load using Exponentially Weighted Moving Averages.
- **Dynamic Scaffolding Decision Algorithm (DSDA v2.1)**: Multi-gate decision engine computing a continuous **Cognitive Struggle Index (CSI)**, enforcing monotonic assistance escalation, and rotating orthogonal pedagogical focuses (`Conceptual`, `Tracing`, `Algorithmic`, `Structural`).
- **8D Vector Memory Retrieval (ChromaDB)**: k-Nearest Neighbor retrieval over historical learner profiles to select peer-tested pedagogical intervention strategies.
- **Layered Code Execution Harness**: AST-based static safety validation blocking file system, network, and reflection vectors (`__subclasses__`, `__globals__`), executing student submissions in isolated subprocesses with strict execution limits.
- **Curated Problem Library & IBM Project CodeNet**: 49-concept Python curriculum across 4 pillars alongside competitive programming challenges from the IBM CodeNet dataset.
- **Dual Role Dashboards**: Real-time student learning workspace with Monaco Editor and an instructor portal for cohort mastery and hint analytics.

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Client["Frontend Client (React 19 + Monaco Editor)"]
        UI_Editor[Monaco Code Workspace & Active Timer]
        UI_Dash[Learner Dashboard & Cognitive Gauges]
        UI_Teacher[Teacher Cohort Portal]
        UI_Chat[Socratic AI Tutor Chat]
    end

    subgraph Gateway["FastAPI REST API Gateway (backend/app/main.py)"]
        AUTH["/api/auth/* (PBKDF2 + HMAC Signed Tokens)"]
        SUBMIT["/api/submit (Workflow Trigger)"]
        LEARNER["/api/learner/* & /api/metrics/*"]
        SESSIONS["/api/sessions/* (Session Tracking)"]
    end

    subgraph Sandbox["Execution Harness (code_runner.py)"]
        AST_SEC[AST Static Safety Validator]
        SUBPROC[Subprocess Sandbox: 3.0s Timeout, -I -S]
    end

    subgraph Graph["LangGraph 6-Agent Engine (tutor_graph.py)"]
        START([START]) --> DIAG[Diagnostic Agent]
        DIAG --> STATE[Learner State Agent]
        STATE --> SIM[Similar Learner Retrieval Agent]
        SIM --> BRANCH{Test Cases Passed?}
        BRANCH -- No --> SCAFF[Adaptive Scaffolding Agent (DSDA v2.1)]
        BRANCH -- Yes --> REFL[Reflection Agent]
        SCAFF --> REFL
        REFL --> PLAN[Learning Planner Agent]
        PLAN --> END_NODE([END])
    end

    subgraph Memory["Persistence & Vector Stores"]
        SQL[(Authoritative SQLite DB: tutor.db)]
        VEC[(ChromaDB: 8D Archetype Profiles)]
        LLM["OpenAI LLM / Fallback Matrix"]
    end

    %% Flow connections
    UI_Editor -->|Run / Submit Code| SUBMIT
    SUBMIT --> AST_SEC --> SUBPROC
    SUBPROC -->|Execution Results| SUBMIT
    SUBMIT --> Graph
    STATE <-->|Read / Write Concept State| SQL
    SIM <-->|8D Profile k-NN Query| VEC
    SCAFF -.->|Structured Prompt| LLM
    SCAFF -->|Persist Delivered Hint| SQL
    PLAN -->|Persist Recommendation| SQL
    Graph -->|Full Feedback Object| SUBMIT
    SUBMIT --> UI_Editor
```

---

## 3. The Six Specialized AI Agents

| Agent Name | Primary Responsibility | Input Evidence | Primary Output |
| :--- | :--- | :--- | :--- |
| **Diagnostic Agent** | Classifies failure modes, categorizes errors (`syntax`, `assertion`, `timeout`, `recursion`), and extracts structural misconceptions. | Traceback, AST structure, test inputs/outputs | Error classification, misconception string, plain-language diagnostic explanation. |
| **Learner State Agent** | Updates probabilistic BKT mastery, EWMA confidence, confusion, and cognitive load indicators. Separates problem-scoped from concept-scoped failures. | Test outcome, response time, problem hint history, previous concept state | Updated BKT $P(L_t)$, confidence, confusion, cognitive load, problem failure streak $F_{prob}$. |
| **Similar Learner Agent** | Assembles an 8-dimensional normalized profile vector and retrieves the 2 nearest historical peer archetypes via ChromaDB. | Normalized state: $[M, \text{Conf}, \text{Confusion}, L_{cog}, \text{Prog}, H_{ratio}, E_{freq}, T_{stress}]$ | Top-2 similar learner archetypes and proven pedagogical intervention strategies. |
| **Adaptive Scaffolding Agent** | Executes the **DSDA v2.1** engine, determining assistance level (1-4), orthogonal focus, and pedagogical rationale. | Cognitive state, hint history, failure streaks, diagnostic data, peer strategy | Scaffolding level, focus dimension, Socratic hint, remediation flag, rationale. |
| **Reflection Agent** | Formulates metacognitive prompts prompting the learner to reflect on algorithmic Big-O complexity or trace state divergence. | Test outcome, code AST, problem objectives, error analysis | Socratic reflection prompt encouraging self-regulation. |
| **Learning Planner Agent** | Analyzes prerequisite concept graph and mastery to determine next optimal learning step. | Concept graph, BKT mastery, confusion level, failure count | Recommended action (`advance`, `reinforce`, `remediate`, `retry`), target problem ID, explainable reason. |

---

## 4. Mathematical Modeling & Algorithmic Foundations

### A. Bayesian Knowledge Tracing (BKT)
Mastery probability $P(L_t)$ updates conditionally upon student performance:

$$\text{If passed: } P(L_t \mid \text{Correct}) = \frac{P(L_{t-1}) \cdot (1 - P(S))}{P(L_{t-1}) \cdot (1 - P(S)) + (1 - P(L_{t-1})) \cdot P(G)}$$

$$\text{If failed: } P(L_t \mid \text{Incorrect}) = \frac{P(L_{t-1}) \cdot P(S)}{P(L_{t-1}) \cdot P(S) + (1 - P(L_{t-1})) \cdot (1 - P(G))}$$

$$\text{Knowledge Transition: } P(L_t) = P(L_t \mid \text{Observation}) + (1 - P(L_t \mid \text{Observation})) \cdot P(T)$$

- Default parameters: Prior $P(L_0) = 0.20$, Transition $P(T) = 0.15$, Guess $P(G) = 0.20$, Slip $P(S) = 0.10$.

### B. Cognitive-State Tracking (EWMA)
Cognitive indicators are smoothed across sequential observations with decay factor $\alpha = 0.70$:
$$S_t = \alpha \cdot S_{t-1} + (1 - \alpha) \cdot \text{Signal}_t$$

### C. Dynamic Scaffolding Decision Algorithm (DSDA v2.1)
1. **Safe Time Stress**:
   $$\bar{t}_{safe} = \max(15.0, \bar{t}_{base} \text{ if } \bar{t}_{base} > 0 \text{ else } 60.0)$$
   $$T_{stress} = \min\left(1.0, \max\left(0.0, \frac{t_{resp} - 0.5 \bar{t}_{safe}}{1.5 \bar{t}_{safe}}\right)\right)$$
2. **Continuous Cognitive Struggle Index (CSI)**:
   $$\text{Raw} = 0.25(1 - M) + 0.25\Phi(F) + 0.20\text{Conf} + 0.15L_{cog} + 0.10H_{sat} + 0.05T_{stress}$$
   $$\text{Uncertainty: } U = \exp\left(-\frac{N_{obs}}{3.0}\right)$$
   $$\text{CSI} = (1 - U) \cdot \text{Raw} + U \cdot 0.35$$
   - Failure Penalty: $\Phi(F) = \min(1.0, F^2 / 9.0)$
   - Hint Saturation: $H_{sat} = \min(1.0, N_{hints} / 3.0)$
3. **Monotonic Escalation Gate**:
   - Initial failure: $L_{final} = \min(L_{base}, 2)$ (prevents premature Level 3/4 hints).
   - Repeat failure: $L_{final} = \min(4, \max(L_{base}, L_{prev} + 1))$ (escalates by at most 1 level per failure).
4. **Orthogonal Strategy Pivoting**:
   If candidate focus matches the immediately preceding hint delivered on this problem, rotate focus ($\text{Conceptual} \rightarrow \text{Tracing} \rightarrow \text{Algorithmic} \rightarrow \text{Conceptual}$) to provide an alternative instructional strategy.

---

## 5. Security Architecture

- **AST Validation**: Statically inspects syntax trees before execution. Rejects forbidden modules (`os`, `sys`, `subprocess`, `socket`, `shutil`) and calls (`eval`, `exec`, `open`, `compile`).
- **Introspection & Reflection Blocking**: Forbids Python reflection vectors including `__subclasses__`, `__globals__`, `__builtins__`, `__bases__`, `getattr`, `setattr`, and `vars`.
- **Subprocess Isolation**: Submissions run using `python3 -I -S` in temporary directories with an empty `PYTHONPATH` and a hard 3.0-second timeout.
- **Authorization & Data Isolation**: All student data endpoints verify the Bearer token. Students cannot access or submit data on behalf of another learner; instructors have read-only cohort access.

---

## 6. Getting Started & Setup Instructions

### Prerequisites
- macOS or Linux
- Python 3.10+ (tested with Python 3.10 through 3.14)
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# Navigate to repository root
cd /path/to/AdaptiveAItutor

# Install backend dependencies
pip3 install -r backend/requirements.txt

# Run database migrations and seed default problems/users
PYTHONPATH=backend python3 -c "from app.database import initialize_database; initialize_database(); print('Database initialized!')"

# Start the FastAPI backend server (port 8001)
PYTHONPATH=backend python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 2. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install

# Start Vite development server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 3. Default Demo Accounts
The database automatically seeds two default accounts for 1-click evaluation:
- **Demo Student**: `demo@student.edu` / `demo123` (Accesses interactive Monaco practice workspace, cognitive gauges, and chat)
- **Demo Teacher**: `teacher@adaptive.edu` / `teacher123` (Accesses cohort mastery table, hint metrics, and time analytics)

---

## 7. Automated Testing & Verification

The test suite validates pedagogical algorithms, API contracts, RBAC isolation, security harnesses, and agent workflows.

Run all tests:
```bash
PYTHONPATH=backend python3 -m pytest backend/tests/test_learning_algorithms.py backend/tests/test_api.py -v
```

### Test Suite Summary (54 Passed)
- **`backend/tests/test_learning_algorithms.py`** (38 tests):
  - Bayesian Knowledge Tracing: Initial prior, correct response convergence, incorrect decay, boundary clamping.
  - EWMA Indicators: Confidence decay, confusion signals, cognitive load stress factors.
  - DSDA v2.1: Safe time stress, CSI uncertainty attenuation, Gates 1-6 (Success, Security, Stub, Syntax, ZPD saturation, Expert blindspot), monotonic escalation, and focus strategy rotation.
- **`backend/tests/test_api.py`** (16 tests):
  - Health check and system dependencies.
  - User registration and login contract (supporting both `name` and `full_name`).
  - Seeded demo account authentication (Student & Teacher).
  - Role-based access control and cross-learner data isolation.
  - 6-Agent LangGraph workflow execution on correct and incorrect code.
  - Code execution security (AST forbidden module and reflection exploit blocking).
  - Session lifecycle tracking and recommendations persistence.
  - Problem-scoped hint history retrieval.

---

## 8. Research Evaluation Criteria

The system provides measurable metrics for educational data mining and learning science research:

$$\text{Normalized Learning Gain: } G = \frac{\text{PostTest} - \text{PreTest}}{1 - \text{PreTest}}$$

- **Hint Efficiency**: Problems solved successfully following a hint intervention divided by total hints requested.
- **Task Completion Rate**: Percentage of curriculum coding challenges completed without abandoning the problem.
- **Time to Completion**: Active coding duration recorded via the frontend stopwatch harness.
- **Learner Satisfaction**: 5-point Likert scale rating recorded via `/api/metrics/satisfaction`.
