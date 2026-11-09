# Requirements traceability

**Source:** R = stated in the report (`projectphase.pdf`). U = additional UX or product requirement from the project brief, not in the report. P = implementation choice proposed here, because the report leaves it open.
**Status:** Done = implemented and covered by tests that ran. Partial = works, with limits noted. Open = not done, or needs a decision.

Test files: `pol` = `backend/tests/test_policy.py`, `agt` = `test_agents.py`, `pip` = `test_pipeline.py`, `api` = `test_api.py`, `con` = `test_content.py`, `run` = `runner/tests/`, `e2e` = `frontend/e2e/learner.spec.ts`, `a11y` = `frontend/e2e/a11y.spec.ts`, `vit` = Vitest.

## Report requirements

| Requirement | Source | Implementation | Tests | Status |
|---|---|---|---|---|
| Multiple collaborating agents, not one model | R §3 p.2 | Six agents in `tutoring/` | `pip` all-stages test | Done |
| Cognitive modelling of mastery, confidence, confusion, load, progress | R §3 p.2 | `cognitive.py`. Estimates with evidence, or unknown. | `agt`, `pip` | Done. Not validated against external measures. |
| Misunderstanding patterns tracked | R §5 p.3 | Issue keys and repeat counts in `diagnostics` | `agt`, `pip` | Done |
| Similar learner retrieval by cosine over multidimensional profiles | R §3 p.2 | `retrieval.py`, 14-dimension vectors | `api`, `pip` | Done |
| k-NN (given as an example) | R §5 p.3 | Top candidates from ChromaDB, then re-ranking | `api` | Done |
| Hybrid retrieval with PostgreSQL and ChromaDB | R §6.3 p.8 | Chroma for similarity, PostgreSQL for outcomes | `pip`, `api` | Done |
| Recover past successful learning tools | R §6.3 p.8 | `intervention_cases` from real hint outcomes | `pip`, `api` | Partial. No real outcomes exist yet, so the demo uses labelled synthetic records. |
| Scoring algorithm using mastery, confidence, hint history, response time | R §3 p.3 | DSDA score. Time acts through the load estimate. | `pol` | Done. Weights unvalidated. |
| DSDA computes assistance from cognitive load and sets number of tips | R §6.3 p.8 | Load input and a level. "Number of tips" interpreted as one hint per action, escalating. | `pol` | Partial: interpretation recorded here. |
| Formula, weights, levels | **Not in report** | Proposed in `docs/dsda.md` | `pol` | Done, as a proposal |
| Adaptive Difficulty Progression from mastery and progress | R §6.3 p.8 | `planner.py` | `agt`, `api` | Done |
| Cyclic graph with six agents | R §6.3 p.8 | `graph.py`, with `interrupt` and a PostgreSQL checkpoint | `pip` cycle test | Done |
| Sequential processing | R §5.1 p.4 | Agents in order within each cycle | `pip` | Done |
| LangGraph | R §5 p.3 | `graph.py` | `pip` | Done |
| Prevent direct source code leakage | R §6.3 p.8 | Validator, no solutions in prompts, bounded retry | `agt`, `pip` | Done with a scripted model. **Real model unverified.** |
| Socratic methods | R §6.3 p.8 | Help ladder starting with questions | `agt` | Done |
| Reflection prompts | R §5.1 p.4 | `reflection.py` | `agt`, `pip`, `e2e` | Done |
| Next problem recommendation | R §5.1 p.4 | `planner.py` | `agt`, `api`, `e2e` | Done |
| Web platform | R §5 p.3 | `frontend/` | `e2e` | Done |
| Student and teacher dashboards with mastery, success, hints, state changes, recommendations | R §5 p.3 | Progress and Teacher screens | `api`, `e2e` | Done |
| CodeNet as primary dataset: questions, accepted, rejected, behaviour | R §4 p.3 | Fields checked. Aggregate importer, tested on a made-up fixture. 7 adapted problems. | `api` | **Partial.** Real CodeNet data has not been imported (see below). |
| Learning gain | R §5.2 p.4 | Pre and post checks only | `api`, `e2e` | Done as a mechanism. No real data. |
| Hint efficiency, hints per problem | R §5.2 p.4 | `analytics.py` | `api` | Done |
| Completion rate, time to completion | R §5.2 p.4 | `analytics.py` | `api` | Done |
| Likert satisfaction | R §5.2 p.4 | Survey with 4 items | `api`, `e2e` | Done |
| Test effectiveness | R §3 p.3 | Plan in `docs/evaluation.md` | None | **Open.** No study has run, so there is no effectiveness evidence. |

## Screens and experience

| Requirement | Source | Implementation | Tests | Status |
|---|---|---|---|---|
| Light and dark themes, system default, persisted | U | `tokens.css`, `session.tsx` | `e2e`, `a11y` both themes | Done |
| Responsive desktop, tablet, phone | U | 3-column, 2-column, tabs | `e2e` responsive | Done |
| Loading, empty, success, partial and error states | U | Shared components | `e2e` | Done |
| Keyboard, focus, labels, reduced motion | U | Radix, skip link, shortcuts | `e2e`, `a11y` | Done. Automated checks only: no screen reader user test. |
| Not colour alone | U | Icons and text with every status | `a11y`, inspection | Done |
| Friendly onboarding, first exercise, plain language | U | `Onboarding.tsx`, planner | `e2e`, `api` | Done |
| Optional explanations | U | Walkthrough, `HelpDialog`, tooltips | `e2e` | Done |
| Shortcuts, compact layout, resizable panels, skip intros, filters | U | `Workspace.tsx`, `Library.tsx` | `e2e` | Done |
| Autosave per learner, problem and language, with restore | U | `useDraft.ts`, `drafts` table | `e2e`, `vit`, `pip` | Done |
| Reset warning | U | `Confirm` dialog | `e2e` | Done |
| Saving, saved and failed feedback | U | `SaveIndicator` | `e2e` | Done |
| Editor content preserved on failures | U | Results never touch the editor | `e2e` | Done |
| Tooltips and copy controls | U | `Tip`, `CopyButton` | `e2e` | Done |
| Sign-in, with demo clearly separate | U | `Welcome.tsx`, banner | `e2e`, `api` | Done |
| Student home | U | `Home.tsx` | `e2e` | Done |
| Problem library | U | `Library.tsx` | `e2e`, `api` | Done |
| Coding workspace | U | `workspace/` | `e2e` | Done |
| Progress | U | `Progress.tsx` | `e2e` | Done |
| Teacher dashboard with evidence and uncertainty | U | `Teacher.tsx`, `learner_flags` | `api`, `e2e` | Done |
| Settings and privacy controls | U | `Settings.tsx`, export, delete | `api`, `e2e` | Done |
| Results ordered: what happened, next, tests, detail, reflection | U | `ResultsPane`, `TutorPane` | `e2e`, inspection | Done |

## Coding and execution

| Requirement | Source | Implementation | Tests | Status |
|---|---|---|---|---|
| Capable editor: highlighting, numbers, indent, brackets | U | CodeMirror 6 | `e2e` | Done |
| Run, Submit and Hint are distinct | U | Separate endpoints and semantics | `pip`, `e2e` | Done |
| Stdout, errors, tests, timeout, infrastructure failure shown separately | U | `grading.py`, `ResultsPane` | `run`, `pip`, `e2e` | Done |
| No private tests, answers or solutions sent to clients | U | Public and internal results kept separate | `pip`, `api` | Done |
| Results tied to a snapshot, with stale label | U | `code_snapshots`, `stale-result` | `pip`, `e2e` | Done |
| No duplicates, no stale overwrites | U | Idempotency, per-learner queue | `pip` | Done |
| Cancellation | U | Runner `docker kill` | `pip` | Done |
| No agents on keystrokes, minimal activity signals | U | Agents run on actions only. No keystroke content. | `pip`, inspection | Done |
| Separate, isolated execution with all listed limits | U | `runner/` | `run` isolation tests | Done on this machine. Not audited. |
| No silent unsafe fallback | U | Explicit `RUNNER_BACKEND`, UI banner | `run`, inspection | Done |

## Agents, policy and honesty

| Requirement | Source | Implementation | Tests | Status |
|---|---|---|---|---|
| Typed contracts, distinct responsibilities | U | `contracts.py` | `agt` | Done |
| One coordinated tutor | U | `compose.py` | `pip`, `e2e` | Done |
| No self-escalating loop, waits for learner | U | `interrupt`, bounded validation | `pip`, `e2e` | Done |
| Record what ran, skipped or failed | U | `agent_steps` | `pip` | Done |
| Facts separate from inferences, no invented lines | U | `diagnostic.py` | `agt` | Done |
| Single failure or long time is not confusion or load | U | Two-signal rules | `agt` | Done |
| Passing is not proof of understanding | U | Weights, wide range, planner | `agt`, `pip` | Done |
| DSDA separates policy, generation, validation | U | `dsda.py`, `hints.py` | `pol`, `agt`, `pip` | Done |
| Configurable, labelled experimental | U | `policy.yaml` | `pol` | Done |
| All policy rules | U | See `docs/dsda.md` | `pol` | Done |
| LLM cannot override policy | U | Level from DSDA only | `pip` | Done |
| Provider adapter, keys on server, fallback labelled | U | `llm.py` | `api`, `pip` | Done with mocks. **Real provider unverified.** |
| "Why this hint?", "What does this estimate mean?" | U | `TutorPane`, `ResultsPane`, `Progress` | `e2e` | Done |
| Developer observability | U | Trace endpoint, correlation IDs | `pip` | Done |
| Metrics state denominators and limits | U | Definitions in API and UI | `api` | Done |
| No fake progress or decorative charts | U | Stages from `agent_steps`, charts from records | `pip`, inspection | Done |
| Synthetic data labelled and separate | U | `provenance`, `is_synthetic` | `api`, `e2e` | Done |

## Add Question, tests and paths

| Requirement | Source | Implementation | Tests | Status |
|---|---|---|---|---|
| Paste, parse, review, edit | U | `parser.py`, `AddQuestion.tsx` | `api`, `e2e` | Done |
| Import from a permitted source | U | Codeforces official API. Metadata only, since its API has no statements. | `api` mocked, one live check, `e2e` | Done for this source |
| No scraping, with guidance to paste | U | `sources.py` | `api`, `e2e` | Done |
| Source, retrieval time, missing fields shown | U | Draft fields, review notices | `api`, `e2e` | Done |
| Generated tests labelled, editable, not official | U | `testgen.py`, `TestsEditor` | `api`, `e2e` | Done |
| Categories: normal, minimal, boundary, repeated, negative, large | U | `testgen.py` | `api` | Done |
| Unknown answers marked "needs expected output" | U | Stays off until filled in | `api`, `e2e`, `vit` | Done |
| Invalid or unsafe definitions refused, large input handled | U | `validate_tests` | `api` | Done |
| Same six-agent workflow on imported problems | U | Normal problem format | `api`, `e2e` | Done |
| Edit and delete, private to owner | U | `api/imports.py` | `api`, `e2e` | Done |
| Stage-appropriate help ladder | U | DSDA | `pol`, `pip` | Done |
| Course-like paths for guided and self-directed use | U | 17 units, `Path.tsx` | `api`, `e2e`, `con` | Done |
| Python only, no unsupported languages shown | U | `LANGUAGES`, UI | `api`, `e2e` | Done |

## Engineering

| Requirement | Source | Implementation | Tests | Status |
|---|---|---|---|---|
| Typed API contracts | U | Pydantic, generated TypeScript types | `tsc` | Done |
| Server-side authorisation | U | Dependencies and ownership checks | `api` | Done |
| Environment config, no secrets committed | U | `.env`, `.gitignore` | Inspection | Done on this branch. The old secret stays in history. |
| Migrations | U | Alembic | Round trip, tests | Done |
| Structured errors, limits | U | `main.py`, `ratelimit.py` | `api` | Done |
| Linting and formatting | U | Ruff (Python), strict `tsc` | Ran clean | Partial: no ESLint or Prettier for TypeScript |
| Dev and production distinctions | U | `ENVIRONMENT`, startup checks | `api` | Done |

## Open decisions

1. **Commit and merge:** nothing is committed. The work is on branch `rebuild/csmasf-platform`.
2. **Old secret** in Git history: rewrite history or accept (see `docs/security.md`).
3. **Model provider:** the existing OpenAI key has no credit.
4. **CodeNet:** download metadata and run the importer, and confirm the dataset's licence.
5. **User study:** participants, approval, baseline.
6. **Multi-agent literature:** the report's novelty claim needs papers on multi-agent tutors.
