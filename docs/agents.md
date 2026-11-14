# Agent contracts

The report names the six agents and gives each a one-line role (§5.1, p.4). These inputs, outputs and methods are this project's implementation. Types are in `backend/app/tutoring/contracts.py`. Agents are plain functions, while graph nodes (`nodes.py`) handle loading, recording and fallbacks. All learner-state writes happen together in `finalize`.

## Persistent interaction state

Every agent reads the learner's real history before producing output. `tutoring/history.py` loads it from the database for each agent, so nothing is taken on trust from the current request. History restarts after a problem is solved.

| State | Stored in |
|---|---|
| Learner, problem, topic, code version | `interaction_records`, `code_snapshots` |
| Submission and hint-request events, timestamps | `interaction_records.trigger`, `created_at`, `evaluations`, `learner_events` |
| Diagnostic result, test results, error type | `interaction_records.diagnostic`, `issue_key`, `tests_passed`, `diagnostics` |
| Previous hints, levels, strategies | `hints` |
| Previous learner responses | `hints.helpful`, `hints.outcome`, `reflections.answer`, `interaction_records.learner_input` |
| Previous cognitive estimates | `interaction_records.cognitive`, `learner_state_snapshots` |
| Previous retrieval results | `interaction_records.retrieval` |
| Previous DSDA decisions, policy version | `interaction_records.decision`, `policy_version` |
| Active working time | `interaction_records.active_seconds` |

| Agent | Technique | Uses an LLM? | Student sees |
|---|---|---|---|
| Diagnostic | Runner output, test comparison, AST analysis | Only when rules are unsure, and it can only add an inference | Summary, facts, possible cause |
| Cognitive State | Weighted BKT, rule scores with evidence | No | Estimates, on request |
| Similar Learner Retrieval | Cosine search, then re-ranking and aggregation | No | One line, only when it changed the help |
| Adaptive Scaffolding | DSDA rules, templates or LLM wording, a validator | Wording only | The hint and why |
| Reflection | Rules with templates | Optional rewording | One question, sometimes |
| Learning Planner | Rules over mastery, prerequisites, dependence | No | Next step and why |

## 1. Diagnostic (`diagnostic.py`)

**In:** verdict, internal test results, code snapshot, problem, previous issue keys, the previous version of the code and its result, hints already shown on this code.
**Out:** `category`, `issue_key`, `title`, `student_summary`, `facts[]`, `inferences[]`, `concepts[]`, `affected_lines[]`, `confidence`, `uncertain`, `repeat_count`, `tests_passed`, `tests_total`, `evidence`, `comparison`.

- **`evidence`** holds exact, visible details: error type, message, line, column, source line, the token Python stopped at, and a visible failing example. A line that does not exist in the code is never quoted. For wrong answers and timeouts it also holds the learner's main loop: its line, its source, its loop variable and the name it builds up, so hints can point at the learner's own code.
- **`comparison`** states how this version relates to the last: code changed, changed lines, same issue, moved further or back, change in tests passed. "Moved further" means failing at a later stage, such as a program that now runs after a syntax error.
- The code is re-analysed on every cycle. Execution is reused only for identical code, and only if the question's tests have not changed since.

- **Facts** come only from the runner, tests or code analysis. **Inferences** are separate, each with a confidence level.
- Line numbers come only from the runner or the AST. An LLM's line number is dropped unless it exists in the code.
- Hidden test values may inform a broad category, but never appear in text. The LLM sees public evidence only.
- Asking again about identical code does not count as a repeat of the issue.

Detected issues include missing colons, indentation, brackets, unfinished strings, `=` versus `==`, exception types, empty functions, printing instead of returning, a return inside a loop, off-by-one boundaries, wrong result type or order, text format differences, edge cases, endless loops and recursion with no base case.

Every result also gets a structured `diagnosis` from `error_analysis.py`: error class (syntax, name resolution, type, runtime, logic, timeout or output mismatch), likely cause, concept, location when reliably known, evidence, confidence, and a safe explanation.

A `NameError` is told apart as: missing import, a module used without importing it, a method called as a function, a misnamed built-in, a misspelling, a parameter typo, use before assignment, a name from another function, a missing function, or an undefined variable. To work out what the learner wanted, it reads the task text, the function's name, the arguments, the code's structure and the visible examples. Other errors are classified from the message and the code, such as text mixed with a number, a method that does not exist, or a value that is None.

When a wrong answer has no single obvious cause, the diagnostic runs the main loop on a failing visible example and records what the values did. The hints then use it: "When I ran `largest([-5, -2, -8])`, the loop ran 3 times: `n` went -5, -2, -8; `best` stayed 0", and the most direct hint names the local variable that never changed. Parameters are not reported as the clue, because a loop usually leaves them alone. Worked examples are matched to the cause of a runtime error, or taken from the topic's lesson for the same technique, never one that computes the same thing as the problem.

The response holds back the cause until the help has reached it, so seeing the result does not undo a first hint that asks the learner to think.

The diagnostic also reads any question and selected lines, through `questions.py`. It adds `question` (the text, intent and concept) and `focus` (the lines, what kind of statements they are, and the values a real traced run produced on a visible example). The other agents receive these like any other evidence. See [dsda.md](dsda.md#when-the-learner-asks-something).

## 2. Cognitive State (`cognitive.py`, method `cs-1.2`)

**In:** prior topic state, the verdict and issue, earlier graded attempts, hint history and outcomes, requests on this exact code, hints marked not helpful, the comparison with the previous version, active time, current or most recent self-report.
**Out:** `mastery {value, low, high, band, evidence_weight, updated, explanation}`, `confidence`, `confusion`, `cognitive_load`, `progress`, each with evidence lines, plus `state_version`, `method_version` and `timestamp`.

| Estimate | Method | Unknown when |
|---|---|---|
| Mastery, per topic | BKT, with each observation weighted: solved alone 1.0, solved with hints 0.8 to 0.2 by level, logic failure 0.8, syntax 0.15, imported problems × 0.5, identical code 0, hints 0. Range narrows with evidence. | Band is "not enough evidence" below 1.5 evidence weight |
| Confidence | The learner's own rating, carried forward on this problem until replaced | No rating given |
| Confusion | Two independent signals for "high": repeated issue, unhelpful hint, shifting errors, saying they are stuck, asking 3 or more times on the same code, marking a hint not helpful | Single failure with no history |
| Cognitive load | Two signals for "high": long time, 3 or more hints, repeated zero scores, saying it feels like a lot. Time alone reaches "moderate" at most. | No time or attempts recorded |
| Progress | Trend in tests passed on the same measure, or getting further than before. Unchanged code is no evidence either way. | Nothing comparable yet |

These are behavioural estimates, and the UI says so. They are not medical or psychological findings, and they have not been validated against an external measure.

## 3. Similar Learner Retrieval (`retrieval.py`, vectors `sv-1`)

**In:** a 14-dimension situation vector built from current state, category, issue, topic, difficulty, approaches this learner already saw here.
**Out:** `reliable`, `reason`, `suggested_level`, `suggested_strategy`, `effectiveness`, `support`, `provenance`, `mean_similarity`, aggregate `evidence[]`, `excluded_strategies`.

- **Vector:** mastery, confidence, confusion, load, progress, difficulty, attempts and hints, each centred on 0, plus a one-hot error group. Centring matters because cosine ignores magnitude: without it, `[0.2, 0.2]` and `[0.8, 0.8]` look identical. Unknown values are 0.
- **ChromaDB** finds candidates, filtered by error group. **PostgreSQL** holds what happened next.
- **Filtering** keeps cases with a known outcome, the same issue or topic, and difficulty within 0.35.
- **Re-ranking** weights similarity by issue match, topic match and difficulty closeness.
- **History:** approaches this learner has already seen on the issue are never suggested again.
- **Reliability:** at least 5 candidates at similarity 0.72 or higher, and at least 3 for the chosen approach. Otherwise it returns "no reliable match".
- **Effectiveness** is a smoothed share of cases followed by progress. It does not show that the intervention caused the progress.
- Measured (`live`) cases are preferred over synthetic ones. Synthetic cases can be turned off, and the learner is told when they were used. Output contains no identities or code.

## 4. Adaptive Scaffolding (`dsda.py`, `hints.py`)

Three separate steps: **policy, generation, validation.** See [dsda.md](dsda.md).

**In:** diagnostic, cognitive output, retrieval output, hint history and outcomes, strategies already used, hints on this exact code, time since the last hint and action, trigger, request size, preferences.
**Out:** `support_need_score`, `selected_level`, `strategy`, `reason_codes`, `evidence`, `presentation`, `constraints`, `await_learner_action`, `policy_version`, `action`, `timing`, `theme`, `reason_student`, then a validated `text` and `source`.

## 5. Reflection (`reflection.py`)

**In:** category, issue, solved?, load, pending prompts, questions already asked on this problem, attempts, hint text, and the cycle's context: failing call, actual and expected values, loop line and variable, result variable, line, and the problem's technique.
**Out:** `action` (ask, defer or skip), `prompt`, `kind`, `context`, `reason`, `source`.

Asks after a solve, or after 3 failed attempts. Defers when load is high. Skips syntax slips, a pending question, or a recent prompt. Avoids repeating the hint. The question names the learner's own example, loop and variable, or after a solve, the technique ("This problem used running totals...").

**Answer:** `POST /reflections/{id}/answer` runs `respond_to_answer(kind, context, answer, code)`, which returns `ReflectionReply`: `quality` (specific, partial, unsure or brief), `feedback`, and `matched` (the key ideas the answer named). The reply confirms what the learner got right and pushes one step further, gives one concrete thing to check, or, for "I don't know", says that is fine and gives one small thing to try. It never grades, never shows code and never names the fix. The answer, reply and quality are stored on the `Reflection` row and logged as a learner event.

**Effects:** an unsure answer counts as one confusion signal in the next Cognitive State cycle. After a solve, an unsure answer holds back a plan that was moving on: the planner suggests one more problem of the same technique (`REFLECTION_UNSURE`), returned as `next` in the answer response. When the plan shown with the question (read from that run's planner step) already gives one more problem of the technique, `next` is empty, so nothing is said twice. Clear, partial and short answers leave the plan alone.

## 6. Learning Planner (`planner.py`)

**In:** unit mastery and evidence, prerequisites, each topic's techniques in lesson order, each problem's technique, difficulty, solved and attempted state and whether it was solved fluently (first graded submission, no hint before it), current problem, attempts, hint level, goal, experience.
**Out:** `action`, `title`, `reason`, `reason_codes`, problem and unit, `keep_current_active`, `alternatives[]`, `route[]` (the current topic and up to 3 ahead, each with a status).

| Situation | Recommendation | Code |
|---|---|---|
| Not solved | Stay on this problem | `UNRESOLVED` |
| Stuck (4 or more attempts) with a weak prerequisite | Suggest the prerequisite. The current task stays saved. | `WEAK_PREREQUISITE` |
| Solved with L3 or L4, or mostly with hints | Same technique, same difficulty, on your own | `ASSISTANCE_DEPENDENCE` |
| Solved, technique needs a second problem at easy | One more of the same technique | `CONSOLIDATE_TECHNIQUE` |
| Solved, technique practised (2 solves, or 1 on the first try without hints) | The next technique in the lesson, same level | `NEXT_TECHNIQUE` |
| Every technique practised at this level | The first technique at the next difficulty | `STEP_UP_DIFFICULTY` |
| Secure: mastery ≥ 0.75, 2 or more independent solves, evidence ≥ 2.5 | Harder problem, or the next topic forward | `READY_HARDER`, `READY_NEXT_UNIT` |
| Reflection answer unsure after a solve, while the plan was moving on | One more of the same technique before moving on | `REFLECTION_UNSURE` |
| Home, with work in a topic | Continue that topic's sequence | `CONTINUE_TOPIC` |
| New learner | The first exercise, or a topic matching their goal | `FIRST_EXERCISE`, `NEXT_IN_PATH` |

The next topic is the next one forward from where the learner works. An earlier topic comes back only when it has work in it and is not yet secure, and a weak prerequisite holds a topic back only while it still has problems to practise. A held-back topic also holds back the topics that build on it, so the planner never jumps past it. The route is a preview in course order, so it always shows the topic after the current one, even while the current one is not secure. Home and the plan after a submission use the same rules. Every recommendation comes with its reason, and all topics stay open.

## Observability

The diagnostic step's trace also records the diagnosed cause, concept and confidence, even when the learner's first view holds the cause back, so the agent audit can check them.


Each stage writes an `agent_steps` row with status, reason, duration, summaries, retries, error, and model metadata. `GET /api/runs/{id}/trace` shows it for your own run outside production. Prompts, hidden tests and reference solutions are not stored there.
