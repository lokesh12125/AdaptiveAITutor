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
| 300 to 400 problems, sorted by topic | U | 368 problems, `scripts/problem_bank`, `content/problems/bank.yaml`, `Library.tsx` | `con`, `e2e` | Done, now 496 |
| More problems in every topic | U | 128 new in `scripts/problem_bank/more_*.py`, at least 19 per topic | `con`, `verify_content` | Done |
| A detailed lesson for every topic, with prerequisites | U | `content/guides`, `Path.tsx`, `TryIt.tsx` | `con`, `e2e` | Done |
| Precise diagnosis with cause, concept, evidence and confidence | U §25 | `error_analysis.py`, `diagnostic.py` | `test_diagnosis`, `e2e` | Done |
| NameError told apart into its causes, with the goal inferred | U §25 | `analyse_name_error`, `_goal` | `test_diagnosis` | Done |
| Validation rejects generic, off-diagnosis and vague hints | U §25 | `diagnosis_violations` in `hints.py` | `test_diagnosis` | Done |
| Reasoning trail: raw error to whether the issue was resolved | U §25 | `InteractionRecord.reasoning`, `next_action`, `resolved` | `test_diagnosis` | Done |
| Detailed topic notes | U §26A | `content/notes/topics.yaml`, `Path.tsx` | `con`, `e2e` | Done, with text diagrams |
| Problem-level learning panel | U §26B | `learning.py`, `LearnPane.tsx`, `content/notes/techniques_*.yaml` | `con`, `e2e` | Done, guidance per technique |
| Learner-controlled modes | U §26C | `ModeSwitch.tsx`, `learning_mode` in `nodes.py` | `test_diagnosis`, `e2e` | Done |
| Test cases shown before running, editable, with added cases | U | `TestCases.tsx`, `_run_cases` in `service.py`, `CaseIn` | `test_api`, `e2e` | Done |
| More tests per problem | U | `scripts/problem_bank/extra_tests.py`, `custom_inputs.py`, `content/problems/extra_tests.yaml` | `con`, `verify_content` | Done: 487 of 496 have 30 or more, see limitations |
| 30 to 40 meaningful tests per question, by kind of case | U brief §2 | `choose` in `extra_tests.py`, `app/test_categories.py`, `LARGE`, `EFFICIENCY`, `SCRIPTS` in `custom_inputs.py` | `con`, `verify_content` | Done for 487 of 496, the rest have few possible inputs |
| Test sources and categories labelled, with their purpose | U brief §2 | `ProblemTest.origin`, `category`, `hidden_test_categories`, `TestCases.tsx`, `AddQuestion.tsx` | `test_api`, `e2e` | Done |
| Collapsible previously added questions below the import area | U brief §1 | `PreviousQuestions` in `AddQuestion.tsx` | `e2e`, `a11y` | Done |
| Agent audit report with evidence | U brief §4 | `docs/agent-audit.md`, `scripts/agent_audit.py`, `docs/agent-audit-run.md` | audit script, `test_hint_quality` | Done |
| Hints specific to the learner's code, never generic advice | U brief §3, §5, §6 | `_anchored_issue_hint`, `VAGUE`, `names_something_concrete` in `hints.py`, `_loop_facts` in `diagnostic.py` | `test_hint_quality`, audit script | Done |
| Every hint shows its concept | U brief §5 | `concept` in `compose.py`, `TutorPane.tsx` | `test_hint_quality` | Done |
| A profile per learner: totals, improvement, calendar, milestones | U | `profile.py`, `GET /me/profile`, `Profile.tsx`, `ProfileView.tsx` | `test_api`, `e2e`, `a11y` | Done |
| Learning-state measures in separate columns | U | `state_matrix` in `profile.py`, `ProfileView.tsx`, learners table in `Teacher.tsx` | `test_api`, `e2e` | Done |
| Teacher table of students with every measure, and each student's profile | U | `state_summary`, `student_detail` in `api/teacher.py`, `Teacher.tsx` | `test_api`, `e2e`, `a11y` | Done |
| The learner's own questions listed apart | U | `YourQuestions` in `AddQuestion.tsx`, "Your questions" group in `Library.tsx`, `ProblemSummary.created_at` | `test_api`, `e2e` | Done |
| Submission history with dates and code | U | `GET /problems/{id}/submissions`, `Submissions.tsx` | `test_api`, `e2e` | Done |
| Learn tab as continuous theory with approach tabs | U | `LearnPane.tsx`, `content/notes/approach_steps.yaml` | `e2e` | Done, per technique |
| Completion rate counts started problems | U | `learner_metrics` in `analytics.py` | `test_api`, `test_pipeline` | Done |
| Search across topics and problems | U §26D | `search_everything`, `Search.tsx` | `con`, `e2e` | Done |
| Type what is confusing, point at code, and rerun the six agents | U | `questions.py`, `TutorPane.tsx`, `POST /problems/{id}/hint` with `focus_start`, `focus_end` | `rep`, `e2e` | Done |
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

## Adaptive hinting, import and rebrand brief

Test files: `rep` = `backend/tests/test_repeated_hints.py`, `lnk` = `backend/tests/test_link_import.py`. These are new since the rest of this document.

| Requirement | Source | Implementation | Tests | Status |
|---|---|---|---|---|
| Diagnose and fix the repeated hint end to end | U §1 | [bug-repeated-hint.md](bug-repeated-hint.md) | `rep`, `e2e` | Done |
| Persistent interaction state | U §2 | `interaction_records`, `tutoring/history.py`, migration `0002` with backfill | `rep` | Done |
| Diagnostic compares versions, and separates fact from inference | U §2A | `diagnostic.py`: `evidence`, `comparison`, `comparison_facts` | `rep`, `agt` | Done |
| Cognitive State reads history, with uncertainty and evidence | U §2B | `cognitive.py` method `cs-1.2` | `rep`, `agt` | Done |
| Retrieval filters, and responds to state and history | U §2C | `retrieval.py`: filters, `exclude_strategies` | `rep` | Done. Synthetic data only, reliable for about 12% of states. |
| DSDA as a separate policy, with the required structure | U §3 | `dsda.py`, `contracts.py`, `policy.yaml` | `rep`, `pol` | Done. Weights are experimental. |
| Hint-history-aware policy, for each situation listed | U §2D | Strategy ladders and rules in `dsda.py`, text in `hints.py` | `rep`, `pol`, `e2e` | Done |
| Validation: repeats, relevance, leakage, invented evidence, length, vagueness, contradiction | U §4 | `hints.validate_hint`, `nodes.validate_hint_node` | `rep`, `agt` | Done with a scripted model. **Real model unverified.** |
| Retry, labelled fallback, logged failures | U §4 | `validate_hint_node`, `compose.BUILT_IN_NOTES` | `rep`, `pip` | Done |
| Themes, responsive layouts, keyboard, reduced motion | U §5, §23 | `tokens.css`, `base.css`, `Workspace.tsx` | `e2e` | Done. No testing with real screen reader users. |
| Progressive disclosure, and "why this help" | U §5, §23 | `TutorPane.tsx`, `ResultsPane.tsx` | `e2e` | Done |
| Editor: find and replace, indentation, undo, font size, wrap, panels, drafts | U §6 | `Editor.tsx`, `Workspace.tsx`, `useDraft.ts` | `e2e`, inspected | Done |
| Run, Submit and Hint are distinct, results tied to a code version | U §6 | `service.py`, `useActions.ts` | `pip`, `e2e` | Done |
| Safe execution boundary | U §7 | `runner/`, [security.md](security.md) | `run` | Done, not independently audited |
| Add Question: paste, with review | U §8, §22 | `AddQuestion.tsx`, `parser.py` | `lnk`, `api`, `e2e` | Done |
| Add Question: any link, best effort | U §8, §22 | `sources.py`, `fetcher.py`, `extract.py` | `lnk`, `e2e`, live checks | Partial by necessity: no named coding site allows reading its statement. See [data-imports.md](data-imports.md). |
| Respect terms, robots.txt, rate limits | U §22 | `fetcher.py`, `SOURCES` | `lnk` | Done for robots and signals. Terms were read by hand and reviewed by no lawyer. |
| Imported, learner and generated tests labelled, with no hidden-test claims | U §9, §22 | `testgen.py`, `AddQuestion.tsx`, `ProblemPane.tsx`, `compose.py` | `lnk`, `api`, `e2e` | Done |
| Imported question works with all agents and the dashboard | U §22 | Stored as a normal problem | `lnk` end-to-end test | Done |
| Course-like path with position, reasons, uncertainty, free choice | U §10 | `Path.tsx`, `planner.py` | `e2e`, `agt` | Done |
| Python first, with no unsupported languages shown | U §11 | Fixed label, roadmap in README | `e2e` | Done |
| Rebrand to CodePath | U §21 | Frontend, docs, metadata, storage migration | `e2e` name check, unit tests | Done. Old keys remain only in the migration code. |

## Agents as a tutor beside the learner

Test files: `rnp` = `backend/tests/test_reflection_and_planner.py`, `aud` = `scripts/agent_audit.py` (output in [agent-audit-run.md](agent-audit-run.md)). Findings and fixes are in [agent-audit.md](agent-audit.md).

| Requirement | Source | Implementation | Tests | Status |
|---|---|---|---|---|
| Learn from a problem opens the topic's lesson, not its problem list | U | `?tab=lesson` on every Learn link, in `ProblemPane.tsx`, `LearnPane.tsx`, `TutorPane.tsx`, `Library.tsx`, read by `Path.tsx` | `e2e` | Done |
| A lesson opened in a new tab or window keeps the theme on screen, even in a browser that has not saved it | U | `NewTabLink` and `withTheme` in `lib/theme.tsx` add `theme=` to the link; `index.html` applies it before the first paint, saves it and removes it from the address | `e2e`, unit | Done |
| Only the help the learner needs: no hint climbs the ladder unasked | U | `OFFER_NEXT_STEP` in `dsda.py` | `pol`, `pip`, `aud`, `e2e` | Done |
| Reflection works like a tutor: a question about the learner's own code, and a reply to the answer | U | `reflection.py` (`_anchored_prompt`, `respond_to_answer`), `api/workspace.py`, migration `0005` | `rnp`, `aud`, `e2e` | Done. Key ideas are spotted by keywords. |
| A reflection answer reaches the other agents | U | Confusion signal in `cognitive.py`, `planner.after_reflection` | `rnp`, `aud` | Done |
| Planner takes the learner from where they are to advanced work, step by step | U | Technique and difficulty sequencing, forward topics, `route`, fluent solves in `planner.py` and `nodes.load_planner_views` | `rnp`, `aud`, `e2e` | Done. Thresholds are a teaching judgement. |
| Home and the plan after a submission agree | U | One sequencing rule, fluent solves recorded per problem | `rnp`, `aud` | Done |

## Open decisions

1. **Commit and merge:** this work is uncommitted, on branch `Trellis`.
2. **Old secret** in Git history: rewrite history or accept (see `docs/security.md`).
3. **Model provider:** the existing OpenAI key has no credit.
4. **CodeNet:** download metadata and run the importer, and confirm the dataset's licence.
5. **User study:** participants, approval, baseline.
6. **Multi-agent literature:** the report's novelty claim needs papers on multi-agent tutors.
