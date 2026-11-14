# Agent audit

Audit of the six agents and the request lifecycle around them, done on 10 November 2026, then extended the same day to cover reflection answers, the planner's sequencing, and help that was shown without being asked. Every claim below points at evidence: a test, or a row of [agent-audit-run.md](agent-audit-run.md), which `scripts/agent_audit.py` writes by driving real scenarios through a running stack and reading each agent's output back from the run and its agent trace.

No model was configured during the audit (`LLM_PROVIDER=none`), so hint wording was the built-in, evidence-based text. The model path was checked with a scripted model in the tests, not a real one.

## How it was audited

1. **Scenarios through the real stack.** `scripts/agent_audit.py` registers a fresh learner per scenario and submits code or asks for hints on `sum-to-n`. It covers repeated requests on unchanged wrong code, a syntax error repeated, a runtime error, a loop that never ends, a return inside a loop, progress after a hint, a new issue, a solve, a high-mastery learner asking for a nudge, an overloaded learner, a request with no history, wrong submissions made without asking for help, reflection answers (unsure while the plan was moving on, unsure when it already gave one more problem, and clear), and the plan after a first-try solve. It checks 37 rules taken from the brief and the follow-up requests, plus two checks over every hint shown.
2. **The agent trace.** Each run's `/api/runs/{id}/trace` (development only) shows each stage's input summary, output summary, status, retries and timing. This is where the audit read the cognitive estimates, retrieval result, DSDA decision and validation.
3. **Tests.** The backend suite drives the same pipeline with a real database and sandbox. The tests named below are the evidence for each rule.

The first round found 2 failing checks, and a later run found 1 more. The second round found the issues listed under agents 4, 5 and 6 below. All 37 checks and both checks over every hint pass on the final run.

## Request lifecycle

| Step | Where | Checked by |
|---|---|---|
| Student action: Run, Submit or Ask for a hint | `Workspace.tsx`, `useActions.ts`. Three separate buttons, and a hint is never graded. | Browser "Run, Submit and Hint are separate", `test_hint_request_is_not_a_graded_attempt` |
| API request and validation | `api/workspace.py` with `RunIn`, `SubmitIn`, `HintIn`. An idempotency key stops duplicates. | `test_repeated_submission_with_same_key_creates_one_record`, `test_concurrent_double_click_creates_one_attempt` |
| Database write of the code version | `CodeSnapshot`, then a `Run` for the graph | `test_results_are_persisted_with_their_snapshot` |
| Code execution | The separate execution service (Docker sandbox), through `service.py` | Execution service suite (39 tests, including sandbox attacks) |
| Six agents in order | `graph.py`, `nodes.py`: diagnostic, cognitive_state, retrieval, dsda, generate_hint, validate_hint, reflection, planner, finalize | `test_failed_submission_runs_every_agent_in_order`, `test_agents_receive_each_others_outputs` |
| Response generation | `compose.py` builds the one tutor view | `test_api`, browser tests |
| Response validation | `validate_hint` before anything is shown, with retry and a labelled fallback | `test_hint_quality.py`, `test_low_quality_model_text_is_rejected` |
| Persistence | `finalize`: `InteractionRecord`, `Hint`, `TopicState`, `StateSnapshot`, all written together | `test_interaction_state_is_persisted_for_every_cycle` |
| UI rendering | `TutorPane.tsx`, `ResultsPane.tsx`. A result names the code version it belongs to, and older results never overwrite newer ones. | `test_older_results_never_overwrite_newer_state`, browser "failure recovery" |
| Next learner action | The hint ends with one question or action, and the plan says what to do next | Every hint row in the audit run |

## Agents

### 1. Diagnostic (`diagnostic.py`, `error_analysis.py`)

- **Responsibility:** say what went wrong in this exact code version, with evidence.
- **Inputs required, and received:** the runner's test results, the code snapshot, the problem, the previous version and its result, and earlier issue keys. All of these are loaded from the database by `history.py`, not taken from the request.
- **Outputs:** error category, issue key, raw error (type, message, line, token), likely cause, concept, location, evidence, confidence, facts kept apart from inferences, a comparison with the previous version, and a safe summary for the learner.
- **Reads and writes:** reads history and the evaluation. Writes nothing itself; `finalize` stores its output in `InteractionRecord.diagnostic`.
- **Error handling:** a runner failure becomes `service_failure`, never a learner mistake (`test_service_failure_is_not_treated_as_learner_mistake`). Line numbers it cannot verify are never shown.
- **Used by the next agent:** yes. Cognitive State reads the verdict and issue, DSDA reads the issue key, comparison and repeat count, and hint generation reads the evidence.
- **Issues found:**
  1. The likely cause looked missing for UnboundLocalError. The cause was found correctly (`used_before_assignment`, confidence 0.95), but the learner's first view holds it back on purpose, and the trace did not record it, so it could not be audited.
  2. The diagnostic found the learner's main loop and the names it updates, but the evidence passed to hints did not include the loop's own line of code or the variable it builds up. So hints for logic mistakes could not point at the learner's code.
- **Fixes:** the trace now records `cause`, `concept` and `cause_confidence`. The evidence now carries `loop_line`, `loop_source`, `loop_variable` and `result_name` (`_loop_facts` in `diagnostic.py`).
- **Tests:** `test_diagnostic_finds_the_loop_and_what_it_builds`, `test_diagnosed_cause_is_in_the_trace_even_when_held_back_from_the_learner`, `test_diagnosis.py` (NameError causes), `test_diagnostic_compares_with_previous_version`, and audit checks "The runtime cause is told apart from a generic NameError" and "A new issue after a hint is diagnosed afresh".
- **Status:** working, with evidence. Covered causes are rule-based, so an unusual error falls back to general help with lower confidence.

### 2. Cognitive State (`cognitive.py`, method `cs-1.2`)

- **Responsibility:** estimate mastery, confidence, confusion, cognitive load and progress, keeping uncertainty.
- **Inputs:** prior topic state, graded attempts, hints and their outcomes, requests on the same code, the comparison with the last version, active time, and the learner's own rating. All are read from the database.
- **Outputs:** each estimate with its evidence, mastery with a range and band, and unknown where there is not enough evidence.
- **Reads and writes:** reads `TopicState`, hints, records and snapshots. `finalize` writes `TopicState` and a `StateSnapshot`.
- **Evidence from the audit run:** after one failure, confusion and load are unknown, not assumed. After a second request on unchanged code, both are moderate. After moving from no answer to a close answer, progress is improving. One solve gives a band of "just starting", not mastery. An overloaded learner's load is high.
- **Issues found:** none in this audit.
- **Tests:** `test_unknown_confidence_is_left_out_not_assumed`, `test_cognitive_state_updates_from_repeated_requests`, `test_self_rating_carries_forward_until_replaced`, `test_thumbs_down_counts_as_evidence`, audit checks "Unknown confidence stays unknown" and "Moving from no answer to a close answer counts as progress".
- **Status:** working. These are behavioural estimates, not validated against an outside measure.

### 3. Similar Learner Retrieval (`retrieval.py`, vectors `sv-1`)

- **Responsibility:** find similar past situations and what helped, or say there is no reliable match.
- **Inputs:** the 14-number situation vector from the current state and diagnosis, plus approaches this learner already saw on the issue.
- **Outputs:** reliable or not, a reason, suggested level and strategy, effectiveness, support, provenance (live, synthetic or mixed), and approaches left out.
- **Reads and writes:** queries ChromaDB by cosine similarity, then PostgreSQL for outcomes. The query vector is now stored in `InteractionRecord.retrieval`, so the learner's profile can show it.
- **Evidence from the audit run:** approaches already shown are left out, one more on each request (`conceptual_question`, then `targeted_hint`, then `trace_failing_case`). Most states give "no reliable match" with a reason. A demonstration-data match is labelled `RETRIEVAL_ADJUSTED_DEMO`.
- **Issues found:** none. The development database also holds pooled outcomes from automated runs, which count as live there; see limitations.
- **Tests:** `test_query_changes_when_the_learner_state_changes_materially`, `test_retrieval_does_not_suggest_what_this_learner_already_saw`, `test_retrieval_output_exposes_no_identities_or_code`, `test_reliable_retrieval_changes_the_real_decision_and_is_labelled`, `test_profile_shows_similar_learners_only_as_counts`.
- **Status:** working. Similarity is never treated as proof that an intervention works, and synthetic cases are labelled.

### 4. Adaptive Scaffolding / DSDA (`dsda.py`, `hints.py`, policy `dsda-2.2`)

- **Responsibility:** decide whether and how much to help (policy), word the help (generation), and check it before showing it (validation).
- **Inputs:** diagnosis, cognitive estimates, retrieval, hint history and outcomes, strategies used, hints on this exact code, time since the last hint, the trigger and the request size.
- **Outputs:** support-need score, level (L0 to L4), strategy, reason codes, presentation limits, constraints (never a complete solution), whether to wait for the learner, then validated text and its source.
- **Reads and writes:** reads history. `finalize` writes the `Hint`, the decision, the validation result and, later, the outcome.
- **Evidence from the audit run:** four requests on unchanged wrong code gave four different hints (highest similarity 0.38 in the final run) at levels 2, 2, 2, 3, never going down, with strategies changing each time. The first level varies between runs: the development database now holds outcomes from earlier audit runs, so retrieval finds a reliable match and can start one level higher (`RETRIEVAL_ADJUSTED`). Each repeat recorded that the learner asked again on the same code. A nudge request from a strong learner was honoured at level 1. An overloaded learner got one short action and no reflection question. After progress, help was offered rather than pushed (`PROGRESS_NO_HELP`). After a first hint, two more wrong submissions without asking only offered help (`OFFER_NEXT_STEP`); asking then gave the next step, one level up.
- **Issues found:**
  1. **Built-in hints for logic mistakes were on topic but generic.** For example: "Your answers are very close to the expected ones. Does your loop include both its first and last values?" It named neither the learner's loop, its line, nor the failing example, although the diagnostic had all three. 8 of the 16 hints in the first audit run named nothing concrete.
  2. **The validator let some generic advice through.** "Use a loop.", "Think carefully about your logic." and "Read the problem again." all passed. "Use a loop" escaped because "loop" counted as a specific word.
  3. **The trace hint was cut short.** It ran to four sentences, and level 2 allows three, so its closing question was dropped.
  4. Full stops inside quoted code, such as `'a. b'`, counted as sentence ends, so a hint could be cut in the middle of a value.
  5. **Help climbed the ladder without being asked.** After the first hint on an issue, each further failed submission on that issue could show the next, more revealing hint automatically. A beginner who just wanted to try again was given more help than they asked for.
  6. When retrieval moved the print-debugging hint earlier for a return inside a loop, that hint asked whether the values were right on each pass but never mentioned the `return`, which is the point of the print here: it shows the loop running only once.
- **Fixes:**
  1. `_anchored_issue_hint` writes hints for 10 common logic and timeout issues around the learner's real failing call, its actual and expected values, the loop's line and source, the loop variable and the result variable. When any of those were not observed, it falls back to the earlier wording, so no placeholder is ever shown. Now a first hint reads: "For `sum_to_n(3)` your function returned `3`, but `6` was expected. Does your loop, `for i in range(1, n):` on line 3, visit both the first and the last value it should?"
  2. `VAGUE` now covers these phrases. A vague phrase is excused only by something specific elsewhere in the text, and model-written text must name a line, a value or a name from the learner's code (`names_nothing_concrete`).
  3. The trace hint fits in three sentences and says what to watch for: for a return inside a loop, on which pass of the loop the `return` runs.
  4. Sentence counting skips quoted code.
  5. After a first hint on an issue, help on the same issue that the learner did not ask for is offered, not shown (`OFFER_NEXT_STEP`): "You have already had a hint on this, so try your own next idea first. The next hint is here whenever you want it." Asking shows it, at most one level above the last. The first failed submission still gets a hint, and progress still gets no help (`PROGRESS_NO_HELP`).
  The offer card states the offer once, with what the next hint will look at, and drops its generic first line, which repeated the same invitation (found in the screen check).
  6. For a return inside a loop, the print hint asks the learner to count the lines the print shows, then: "How many passes should the loop make, and what does your `return` do to that?"
- **Tests:** `test_hint_quality.py` (22 tests), `test_every_ladder_step_is_distinct_and_passes_validation`, `test_repeated_requests_never_show_the_same_hint`, `test_never_returns_the_solution_through_the_ladder`, `test_leaked_solution_from_the_model_is_blocked_then_retried`, `test_model_failure_uses_labelled_fallback`, `test_prompt_injection_in_code_cannot_change_the_policy`, `test_help_never_climbs_the_ladder_without_a_request`, `test_print_hint_for_an_early_return_asks_how_many_passes_run`, the audit checks in "Wrong submissions without asking: help is offered, not pushed", and audit checks "Every hint names something concrete" (all hints) and "No hint uses generic advice" (all hints).
- **Status:** working, with evidence on the built-in path. Model-written wording was tested with a scripted model only.

### 5. Reflection (`reflection.py`)

- **Responsibility:** ask one short question that makes the learner explain their own reasoning, at a moment when it helps, then reply to the answer the way a tutor sitting beside them would: no grading, no code, no fix.
- **Inputs:** category, issue, whether solved, load, pending prompts, questions already asked, attempts, the hint text, and what this cycle observed: the failing call with its actual and expected values, the loop's line and variable, the result variable, the line, and the problem's technique.
- **Outputs:** ask, defer or skip, with the prompt, its kind (the issue, or `solved:assisted`, `solved:first_try` and `solved:default`) and the context it names. For an answer: a quality (specific, partial, unsure or brief), a short reply, and the key ideas the answer named.
- **Reads and writes:** reads earlier reflections. `Reflection` stores the kind and context with the question, then the answer, reply and quality when the learner answers (`POST /reflections/{id}/answer`, migration 0005). The answer is also logged as a learner event.
- **What the answer changes:** an unsure answer counts as one sign of confusion in the next cycle's Cognitive State ("you said you were not sure"). After a solve, an unsure answer holds back a plan that was moving on: the Planner suggests one more problem of the same technique first (`REFLECTION_UNSURE`). When the plan shown with the question already gives one more problem of that technique, it stands, so the learner is not told the same thing twice. A clear, partial or short answer leaves the plan as it was.
- **Evidence from the audit run:** after a solve with help, the question named the technique ("This problem used running totals..."). After a first-try solve the plan was Count the Digits, the next technique; "not sure, I just changed it until it passed" got a kind reply with one small thing to try, and the plan became Sum Odds Only, one more running-totals problem. After a solve with help the plan already was Sum Odds Only, so the same answer left it alone. A clear answer was confirmed by naming what it got right, and the plan stood. No reply graded the learner or contained code.
- **Issues found:**
  1. Questions were fixed sentences, the same for every learner, for example "Which kind of input have you not yet considered?" They named nothing from the learner's code or the problem's technique.
  2. An answer was stored and nothing else happened: no reply, and no other agent read it. "I don't know" was treated the same as an answer that explained the bug.
  3. Found while testing the replies: a correct but short answer ("It builds the text from the name.") made the plan say the idea was "not fully settled", and repeated the problem the plan card already suggested. After a first-try solve, the reply's suggestion did not match the question, which asked about an input that could break the code.
- **Fixes:**
  1. Questions are built from this cycle's evidence for six issue kinds (off by one, return inside a loop, missing return, runtime error, timeout, other) and three solved kinds (with help, first try, other). For the off-by-one example: "Trace `sum_to_n(3)` by hand: which values does `i` take in `for i in range(1, n):`, and which values does the answer need?" Anything not observed is left out, never shown as a placeholder.
  2. `respond_to_answer` listens for the key idea of the issue or technique (for example "where `range` stops", or "keeping a running total"), for reasoning words (because, so, since), and for honest uncertainty, then replies in one of four ways:
     - **Specific:** names what the learner got right and pushes one step further. "Good thinking: you named where `range` stops. ... Now test that on the example before changing anything, so you know whether you were right."
     - **Partial:** gives one concrete thing to check, in the learner's own example and variable. "You're on the right track. To make it sharper, write down the first and last value `i` takes for `sum_to_n(3)`, then the values the answer needs."
     - **Unsure:** says that is fine and gives one small thing to try. "That's honest, and a fine place to start. Try just one small thing: ..."
     - **Brief:** asks for a little more, in a sentence.
     It never says right or wrong, never shows code and never names the fix.
  3. Questions and replies show code spans as code, not as raw backticks (found in the screen check).
  4. Only an unsure answer changes the plan, and only when the plan was moving on. The first-try question has its own reply: an unsure learner is asked to pick the smallest or emptiest input and work out by hand what the code gives, and an answer that names one is credited for it.
- **Tests:** the reflection tests in `test_reflection_and_planner.py` (question, replies, effects on the next cycle and the plan, stored rows), `test_reflection_deferred_when_overloaded`, browser "a reflection answer gets a reply, and the plan shows the route ahead", and the audit checks in "Reflection: the question, the reply, and what happens next".
- **Status:** working, with evidence. Spotting the key idea is keyword-based, so a correct answer in unusual words can be read as partial. The reply then asks for one more step, which is mild.

### 6. Learning Planner (`planner.py`)

- **Responsibility:** recommend what to do next, with a reason, moving the learner from where they are towards harder work one step at a time.
- **Inputs:** unit mastery and evidence, prerequisites, each topic's techniques in lesson order, each problem's technique and difficulty, which problems are solved, attempted, or solved on the first try without hints, the current problem, attempts, hint level, goal, experience, and after a reflection, the answer's quality.
- **Outputs:** an action, a title, a reason, reason codes, a problem and topic, whether the current task stays active, alternatives, and a **route**: the current topic and up to three topics ahead, each with its status.
- **How it sequences:**
  1. An unsolved problem stays the current task.
  2. Inside a topic: every technique at easy, in the lesson's order, then medium, then hard. A technique counts as practised at easy after 2 solves, or 1 solved on the first try without hints; above easy, after 1.
  3. After a solve with heavy help (level 3 or more) or a pattern of solving with hints: one more problem of the same technique at the same difficulty, on your own.
  4. When the topic is secure (mastery 0.75 or more, 2 or more independent solves, evidence 2.5 or more): a harder problem, then the next topic.
  5. The next topic is the next one forward. An earlier topic comes back only when it has work in it and is not yet secure. A weak prerequisite holds a topic back only while it still has problems to practise.
  6. Home uses the same rules as the plan after a submission, so they suggest the same next step.
- **Evidence from the audit run:** a first-try solve of Sum to N (running totals) moved on to Count the Digits (digit loops, easy), the next technique in the lesson, not a harder problem. Home suggested the same problem. The route read Loops, Functions, Strings, Lists and dictionaries. After a solve with hints, the next problem was another running-totals problem at the same level.
- **Issues found:**
  1. Inside a topic, the next problem was chosen by difficulty only. Techniques were ignored, so a learner could get several problems of one technique in a row and never meet the next, or step up to medium with techniques still unpractised.
  2. The next topic was the first topic in the course that was not yet secure. A learner working in Functions could be sent back to Loops with no work there.
  3. While testing the new sequencing: when a topic had no problems left but was not yet secure, and the next topic's prerequisite looked weak, Home had no recommendation.
  4. After a first-try solve, the plan moved to the next technique, but Home sent the learner to another problem of the same technique, because Home did not know the solve was fluent.
  5. The plan named only the next problem, with no sense of where it leads.
  6. Found in the screen check: for a new learner in Loops, the route skipped Functions and showed Strings, Lists and Recursion, which all build on Functions. Functions was "blocked" because its prerequisite, Loops, was the topic being worked on and was not secure yet, and the next-topic walk then jumped past it.
  7. On the home screen, a second problem of a technique already solved once was titled "Next technique" with the reason "Next in the lesson is running totals", because Home has no current problem to compare with.
- **Fixes:**
  1. `_sequence_next` follows the lesson's techniques and the difficulty steps, with reason codes `CONSOLIDATE_TECHNIQUE`, `NEXT_TECHNIQUE` and `STEP_UP_DIFFICULTY`. A new technique at the same level is labelled practice, not a step up.
  2. `_next_unit` looks forward from the current topic first.
  3. `_blocked` counts a weak prerequisite only while it still has open problems.
  4. `load_planner_views` records fluent solves (the first graded submission accepted, with no hint shown before it), and both paths use the same rule.
  5. Every plan carries a `route`, shown on the tutor's plan card and on the home screen.
  6. The route is a preview in course order, so the topic after the current one is always shown. The next-topic walk treats a held-back topic as holding back every topic that builds on it, so it never jumps past it.
  7. Home uses the consolidation wording ("One more running totals problem") when the technique already has a solve.
- **Tests:** the planner tests in `test_reflection_and_planner.py` (technique order, step up, forward topics, Home agreeing with the plan, unsure reflection), `test_planner_keeps_unresolved_task_active`, the audit checks in "Learning Planner: from where the learner is, onward", and "One solve does not jump to a harder problem or topic".
- **Status:** working, with evidence. The thresholds (2 solves, or 1 if fluent) are a teaching judgement, not tuned on real learners.

## Hints now include

| Part | Where |
|---|---|
| What is happening, in plain words | The first sentence of an anchored hint, for example "For `sum_to_n(3)` your function returned `3`, but `6` was expected." |
| One focused question or action | The hint's last sentence |
| The relevant concept | "Concept: Loops and boundaries" on the hint card (new in this audit), with a link to the lesson |
| Why this hint | A collapsed "Why this hint?" section with the reason and its evidence |
| The next step | "I need more help", the plan, and the waiting state when every kind of help has been used |

## Not verified

- A real model's wording, rejection rates and latency.
- Whether the anchored hints help real learners more than the earlier wording. No study has run.
- Issues outside the 10 anchored ones still use the general wording, which names the failing example where one exists but not always the learner's own line.
- Reflection replies spot key ideas by keywords, not by understanding. No study has checked that the replies help learners explain their reasoning better.
- The planner's sequence has not been compared with a teacher's choices for real learners.
