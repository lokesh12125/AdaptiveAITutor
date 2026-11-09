# Agent contracts

The report names the six agents and gives each a one-line role (§5.1, p.4). These inputs, outputs and methods are this project's implementation. Types are in `backend/app/tutoring/contracts.py`. Agents are plain functions, while graph nodes (`nodes.py`) handle loading, recording and fallbacks. All learner-state writes happen together in `finalize`.

| Agent | Technique | Uses an LLM? | Student sees |
|---|---|---|---|
| Diagnostic | Runner output, test comparison, AST analysis | Only when rules are unsure, and it can only add an inference | Summary, facts, possible cause |
| Cognitive State | Weighted BKT, rule scores with evidence | No | Estimates, on request |
| Similar Learner Retrieval | Cosine search, then re-ranking and aggregation | No | One line, only when it changed the help |
| Adaptive Scaffolding | DSDA rules, templates or LLM wording, a validator | Wording only | The hint and why |
| Reflection | Rules with templates | Optional rewording | One question, sometimes |
| Learning Planner | Rules over mastery, prerequisites, dependence | No | Next step and why |

## 1. Diagnostic (`diagnostic.py`)

**In:** verdict, internal test results, code snapshot, problem, previous issue keys.
**Out:** `category`, `issue_key`, `title`, `student_summary`, `facts[]`, `inferences[]`, `concepts[]`, `affected_lines[]`, `confidence`, `uncertain`, `repeat_count`, `tests_passed`, `tests_total`.

- **Facts** come only from the runner, tests or code analysis. **Inferences** are separate, each with a confidence level.
- Line numbers come only from the runner or the AST. An LLM's line number is dropped unless it exists in the code.
- Hidden test values may inform a broad category, but never appear in text. The LLM sees public evidence only.
- Asking again about identical code does not count as a repeat of the issue.

Detected issues include missing colons, indentation, brackets, unfinished strings, `=` versus `==`, exception types, empty functions, printing instead of returning, a return inside a loop, off-by-one boundaries, wrong result type or order, text format differences, edge cases, endless loops and recursion with no base case.

## 2. Cognitive State (`cognitive.py`, method `cs-1.0`)

**In:** prior topic state, the verdict and issue, earlier graded attempts, hint history and outcomes, active time, optional self-report.
**Out:** `mastery {value, low, high, band, evidence_weight, updated, explanation}`, `confidence`, `confusion`, `cognitive_load`, `progress`, each with evidence lines, plus `state_version`, `method_version` and `timestamp`.

| Estimate | Method | Unknown when |
|---|---|---|
| Mastery, per topic | BKT, with each observation weighted: solved alone 1.0, solved with hints 0.8 to 0.2 by level, logic failure 0.8, syntax 0.15, imported problems × 0.5, identical code 0, hints 0. Range narrows with evidence. | Band is "not enough evidence" below 1.5 evidence weight |
| Confidence | The learner's own rating only | No rating given |
| Confusion | Two independent signals for "high": repeated issue, unhelpful hint, shifting errors, saying they are stuck | Single failure with no history |
| Cognitive load | Two signals for "high": long time, 3 or more hints, repeated zero scores, saying it feels like a lot. Time alone reaches "moderate" at most. | No time or attempts recorded |
| Progress | Trend in tests passed | No earlier graded attempt |

These are behavioural estimates, and the UI says so. They are not medical or psychological findings, and they have not been validated against an external measure.

## 3. Similar Learner Retrieval (`retrieval.py`, vectors `sv-1`)

**In:** a 14-dimension situation vector, category, issue, topic, difficulty.
**Out:** `reliable`, `reason`, `suggested_level`, `suggested_strategy`, `effectiveness`, `support`, `provenance`, `mean_similarity`, aggregate `evidence[]`.

- **Vector:** mastery, confidence, confusion, load, progress, difficulty, attempts and hints, each centred on 0, plus a one-hot error group. Centring matters because cosine ignores magnitude: without it, `[0.2, 0.2]` and `[0.8, 0.8]` look identical. Unknown values are 0.
- **ChromaDB** finds candidates, filtered by error group. **PostgreSQL** holds what happened next.
- **Re-ranking** weights similarity by issue match, topic match and difficulty closeness.
- **Reliability:** at least 5 candidates at similarity 0.72 or higher, and at least 3 for the chosen approach. Otherwise it returns "no reliable match".
- **Effectiveness** is a smoothed share of cases followed by progress. It does not show that the intervention caused the progress.
- Measured (`live`) cases are preferred over synthetic ones. Synthetic cases can be turned off, and the learner is told when they were used. Output contains no identities or code.

## 4. Adaptive Scaffolding (`dsda.py`, `hints.py`)

Three separate steps: **policy, generation, validation.** See [dsda.md](dsda.md).

**In:** diagnostic, cognitive output, retrieval output, hint history, trigger, request size, preferences.
**Out:** `action`, `level`, `strategy`, `focus_issue`, `timing`, `presentation`, `reason_codes`, `reason_student`, `score`, `policy_version`, then a validated `text` and `source`.

## 5. Reflection (`reflection.py`)

**In:** category, issue, solved?, load, pending prompts, attempts, hint text.
**Out:** `action` (ask, defer or skip), `prompt`, `reason`, `source`.

Asks after a solve, or after 3 failed attempts. Defers when load is high. Skips syntax slips, a pending question, or a recent prompt. Avoids repeating the hint. Answers are stored later as separate events, and a question is never treated as answered.

## 6. Learning Planner (`planner.py`)

**In:** unit mastery and evidence, prerequisites, solved and attempted problems, current problem, attempts, hint level, goal, experience.
**Out:** `action`, `title`, `reason`, `reason_codes`, problem and unit, `keep_current_active`, `alternatives[]`.

| Situation | Recommendation |
|---|---|
| Not solved | Stay on this problem |
| Stuck (4 or more attempts) with a weak prerequisite | Suggest the prerequisite. The current task stays saved. |
| Solved with L3 or L4, or mostly with hints | A similar problem, independently |
| Solved once | A similar problem. One success never advances. |
| Secure: mastery ≥ 0.75, 2 or more independent solves, evidence ≥ 2.5 | Harder problem, or next topic |
| New learner | The first exercise, or a topic matching their goal |

Every recommendation comes with its reason, and all topics stay open.

## Observability

Each stage writes an `agent_steps` row with status, reason, duration, summaries, retries, error, and model metadata. `GET /api/runs/{id}/trace` shows it for your own run outside production. Prompts, hidden tests and reference solutions are not stored there.
