# CodePath: an adaptive Python tutor

Implementation of the **Cognitive-State Guided Multi-Agent Adaptive Scaffolding Framework (CSMASF)** for the project *Adaptive Multi-Agent AI Tutoring System for Personalized Programming Education* (23CSE498, Amrita School of Computing).

Learners write Python in a real workspace. Six agents on a cyclic LangGraph diagnose each attempt, estimate learner state, look at what helped in similar situations, choose how much help fits, ask a reflective question about the learner's own code when it helps and reply to the answer, and plan the next step: each technique at the easy level, then medium, then hard, then the next topic. The learner sees one coordinated tutor that gives the smallest useful hint, never the solution, takes a different approach each time they ask, and offers further help rather than pushing it. Questions from other sites can be pasted or imported from a link, and work with the same tutor. Each learner has a profile showing how much they have done, how they have improved, and the tutor's estimate of their learning state per topic, and teachers see the same measures for their class.

> **Status:** tested as software, including in real browsers and against real Docker sandboxes. **It has not been evaluated with real learners, so there is no evidence yet that it improves learning.** See [limitations](docs/limitations.md).

## Quick start

You need Docker (running), [uv](https://docs.astral.sh/uv/), and Node.js 20 or later. No AI key is needed.

```bash
./scripts/setup.sh
```

```bash
./scripts/dev.sh
```

Open http://127.0.0.1:5173 and press **Try as a learner** or **Try as a teacher**. A 5-minute script is in [docs/demo.md](docs/demo.md).

`setup.sh` creates `.env` with fresh secrets, starts PostgreSQL on port 5544, builds the sandbox image, installs everything, runs migrations and loads content. It is safe to run again, and migrations keep existing data.

### Doing it by hand

```bash
cp .env.example .env    # then set RUNNER_TOKEN to a long random value
docker compose up -d db
docker build -t csmasf-sandbox:py312 runner/sandbox
```

```bash
cd runner && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/uvicorn runner_service.main:app --host 127.0.0.1 --port 8102
```

```bash
cd backend && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8101
```

```bash
cd frontend && npm ci && npx vite --host 127.0.0.1 --port 5173
```

### Everything in containers

```bash
docker compose --profile full up --build
```

Then open http://127.0.0.1:8080. Requires `RUNNER_TOKEN` in `.env`. Read the Docker socket note in [docs/security.md](docs/security.md) first.

### No Docker?

Set `RUNNER_BACKEND=local_dev_unsafe` in `.env` to run code without container isolation, on your own machine, with code you trust. You still need a PostgreSQL server, set in `DATABASE_URL`. The app shows a warning banner in this mode.

## Configuration

Everything is in `.env`, documented in [.env.example](.env.example).

| Setting | Purpose |
|---|---|
| `LLM_PROVIDER` | `none` (default, built-in hints), `openai`, `anthropic` or `ollama`. See [docs/models.md](docs/models.md). |
| `TEACHER_INVITE_CODE` | Needed for teacher sign-up. Empty disables it. |
| `DEMO_MODE`, `RETRIEVAL_ALLOW_SYNTHETIC` | Demo access and synthetic records. Turn both off for real use. |
| `RUNNER_BACKEND` | `docker`, or the explicit `local_dev_unsafe`. |
| `IMPORT_PAGE_FETCH`, `IMPORT_BLOCKED_DOMAINS` | Whether link import may open external pages, and domains it must never open. Paste always works. |
| `backend/app/tutoring/policy.yaml` | All DSDA, estimation and planner values. |

## Run the tests

With PostgreSQL running and the sandbox image built:

```bash
cd runner && .venv/bin/python -m pytest
```

The backend tests need the execution service running. They use their own database. Run the suites one at a time, because they all start Docker containers:

```bash
cd backend && .venv/bin/python -m pytest
```

```bash
cd frontend && npm test
```

The browser tests need the full stack running, with rate limits raised for the API, because they sign in many times:

```bash
RATE_AUTH_PER_MINUTE=100000 RATE_RUN_PER_MINUTE=100000 RATE_SUBMIT_PER_MINUTE=100000 RATE_HINT_PER_MINUTE=100000 RATE_IMPORT_PER_MINUTE=100000 ./scripts/dev.sh
```

```bash
cd frontend && npx playwright install chromium && npm run e2e
```

To use an installed Chrome instead of downloading a browser, run `E2E_CHROME_CHANNEL=chrome npm run e2e`.

Check all curriculum problems against the real sandbox:

```bash
cd backend && PYTHONPATH=. .venv/bin/python ../scripts/verify_content.py
```

Latest results: [docs/test-results.md](docs/test-results.md).

## Adding problems and lessons

There are 496 problems across 17 topics, at least 19 in each. 406 of them are written in `scripts/problem_bank`, in a compact form: hand-written examples are checked against the reference solution, and hidden answers are worked out from it. Rebuild after a change, then reseed and verify:

```bash
backend/.venv/bin/python scripts/problem_bank/build.py
```

```bash
cd backend && PYTHONPATH=. .venv/bin/python -m app.seed
```

Extra hidden tests (about 32 per problem) are generated with the reference solution supplying every answer, and chosen to cover different kinds of case. Inputs come either from what a problem's own examples share, or, for problems with rules the examples cannot show (trees, linked lists, graphs, grids, operation lists, "exactly one answer"), from a generator written for that problem in `scripts/problem_bank/custom_inputs.py` that only produces valid inputs. Regenerate them after changing problems, then reseed and run the content check:

```bash
backend/.venv/bin/python scripts/problem_bank/extra_tests.py
```

To check the agents end to end against a running development stack, run the audit. It prints a report of every agent's output in each scenario, and exits with an error if a check fails:

```bash
backend/.venv/bin/python scripts/agent_audit.py http://127.0.0.1:8101 > docs/agent-audit-run.md
```

Topic notes are in `content/notes/topics.yaml`, and approach guidance for each technique is in `content/notes/techniques_*.yaml`. Lessons are in `content/guides`, one file per group of topics. Every problem's technique must appear in its topic's lesson, and every lesson example must run, which the content tests check.

## Documentation

| Document | Contents |
|---|---|
| [Faculty guide](docs/faculty-guide.md) | What happens after a submission, each agent, DSDA, failures, evaluation |
| [Traceability](docs/traceability.md) | Every requirement, its source, implementation, tests and status |
| [Architecture](docs/architecture.md) | Components, graph, sequence, event semantics, failure handling |
| [Agents](docs/agents.md) | Inputs, outputs and method for each agent |
| [DSDA](docs/dsda.md) | Decision format, help ladder, strategies, score, rules, worked example, configuration |
| [Repeated-hint bug report](docs/bug-repeated-hint.md) | Root cause, data flow before and after, and the tests that prove the fix |
| [Agent audit](docs/agent-audit.md) | Each agent's inputs, outputs, issues found, fixes, tests and status, with [the last audit run](docs/agent-audit-run.md) |
| [Importing questions](docs/data-imports.md) | Paste and link import, what each site allows, labelling of tests |
| [Models](docs/models.md) | What uses an LLM, providers, fallback, cost |
| [Data](data/README.md) | CodeNet fields, provenance, import workflow, synthetic data |
| [Security and privacy](docs/security.md) | Isolation, limits, data handling |
| [Evaluation](docs/evaluation.md) | Metrics, formulas, planned study |
| [Test results](docs/test-results.md) | What ran, what passed, what remains unverified |
| [Limitations](docs/limitations.md) | What this does not do yet |
| [Decisions](docs/decisions.md) | Assessment of the earlier code, and reversible choices |
| [Demo](docs/demo.md) | A short walkthrough |

## Language roadmap

Python is fully supported, and only languages that really run are ever shown. Next: JavaScript, then Java or C++, once the Python workflow has proven stable with real learners.

## Project team

Kataru Reddy Eswar, Bharath Bommineni, Chimmili Lokesh, Ramisetti Gowtham Tej. Guide: Ms. Anju Sukumar.
