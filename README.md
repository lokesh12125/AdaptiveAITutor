# Adaptive Multi-Agent AI Tutor

A FastAPI + LangGraph prototype for personalized Python practice. The six graph nodes are Diagnostic, Learner State, Similar Learner Retrieval, Adaptive Scaffolding, Reflection, and Learning Planner. Learner-state scores are interaction-based estimates, not clinical measurements. Similar profiles are synthetic demo records only.

## Run it

1. Put `OPENAI_API_KEY=...` in `backend/.env` (already done in this workspace). `python-dotenv` loads it from `backend/app/config.py`.
2. Backend: `cd backend` then `..\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000`
3. Frontend: `cd frontend`, `npm install`, then `npm run dev`
4. Open `http://localhost:5173`.

## Demo Mode

The server starts without an API key. If an OpenAI request fails because the key is invalid, unavailable, quota-limited, or the network is down, the request returns the deterministic tutoring fallback and reports `mode: "demo"`; it does not crash. No endpoint returns the API key.

## API

- `GET /api/health`, `/api/problems`, `/api/problems/{id}`
- `POST /api/submit` with `learner_id`, `problem_id`, `code`, optional `response_time`
- `GET /api/learner/{id}`, `/api/learner/{id}/history`, `/api/learner/{id}/recommendation`
- `POST /api/chat` with `learner_id`, `problem_id`, `message`

For a code review: LangGraph carries one shared `TutorState` through the six nodes. OpenAI enriches diagnostics and hints when available; deterministic logic keeps every other path runnable in Demo Mode.
