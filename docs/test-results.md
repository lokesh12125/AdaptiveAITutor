# Test results

Run on 10 November 2026 (the latest round in the evening), on macOS (Apple Silicon, 8 GB RAM) with Docker Desktop 29.8, Python 3.12 and Node 26. These ran on the development checkout, one suite at a time, after the last code change. The earlier clean-copy run of `setup.sh` was not repeated for this work. See "Not verified".

## Summary

| Suite | Result | What it uses |
|---|---|---|
| Execution service | **39 passed** (9 November) | Real Docker sandbox containers. Not re-run: the execution service did not change in this work. |
| Backend | **551 passed** | Real PostgreSQL, real execution service, real LangGraph and ChromaDB. **Model scripted.** Network simulated for link import. |
| Frontend unit | **21 passed** | Vitest |
| Browser end-to-end | **59 passed** | Real Chrome against the full running stack, in one full run after the last change. |
| Accessibility (within the above) | **Passed, no violations** | axe-core, WCAG 2.0/2.1 A and AA rules, 28 screens or states, each in both themes, including Add question with the previous questions open, the profile, the teacher's view of a student, the lesson, practice, tutor answer, Learn panel and search screens |
| Curriculum verification | **496 of 496** | Each reference solution passes all of its tests (15,717 in total) and each starter does not, in the real sandbox |
| Agent audit | **37 of 37 checks, and both checks over every hint** | `scripts/agent_audit.py` drove 9 scenarios through the running stack; every row is in [agent-audit-run.md](agent-audit-run.md) |
| TypeScript strict check, production build | **Passed** | `tsc`, `vite build` |
| Lint | **Passed** | Ruff on the backend, its tests and the content scripts. No ESLint for TypeScript. |
| Migrations | **Passed** (9 November); **0005 applied** | Up, down, up, and no model drift (`alembic check`), on a scratch database, on 9 November. This round added `0005_reflection_replies` (the reflection's kind, context, reply and quality), applied to the development database (`alembic current` shows 0005). Up, down, up for 0005 on a scratch database was not run. |
| Migration on existing data | **Passed** | Development database: 313 completed runs became 313 interaction records |
| Clean install of the backend | **Passed** | New virtual environment, installed from `pyproject.toml`, and the new modules import |
| API container image | **Built** | The image builds, and the new modules import inside it. The whole stack was not started. |
| Link import, live | **Checked by hand** | Project Euler, Rosetta Code and Wikipedia read; AtCoder refused on its `noai` marker; a LeetCode link never contacted the site; one real Codeforces API lookup |

One earlier full backend run reported 9 execution service failures and 1 backend failure, because two suites ran at the same time and overloaded Docker. They passed when run one at a time, so the README now says to run them that way.

**Latest round (agents as a tutor beside the learner, Learn links, theme in new tabs).** Learn links from a problem open the topic's lesson. Reflection questions name the learner's own code, the tutor replies to answers, and an unsure answer reaches the Cognitive State and the Planner. The Planner sequences each topic by technique and difficulty and moves forward, with a route. Help after a first hint is offered, not pushed. A lesson opened in a new tab keeps the theme. What failed on the way, and how it was fixed:
- After the agent changes, 7 backend tests failed. 5 of them encoded the old behaviour, in which help climbed the ladder on its own, and were changed on purpose. 2 found real problems: the planner labelled a same-level step as a step up, and the new offer rule hid the "progress, no help" decision. Both were fixed.
- The audit found Home and the post-submit plan suggesting different problems after a first-try solve. It was fixed by recording fluent solves.
- 2 browser tests failed because they expected the old behaviour (a new hint after every wrong submission, and "Your answer is saved"). They were rewritten for the new behaviour and pass.
- Testing the replies showed that a correct short answer changed the plan and repeated the plan card's suggestion, and that the reply after a first-try solve did not match its question. Both were fixed.
- An audit run showed the print hint for a return inside a loop never mentioning the `return`. It was fixed.
- The screen check found 4 more problems, all fixed: the offer card said the same thing twice, reflection text showed raw backticks, the route skipped Functions for a new learner in Loops, and Home called consolidation a "next technique".
- One full backend run had 1 failure: `test_hidden_tests_never_reach_the_client` found "5050" inside a random id, not in a hidden answer. The check now ignores ids and timestamps, and it still catches the value itself.

The final runs above are all on the finished code.

**Previous round (agent audit and test coverage).** It added the collapsible list of previously added questions, the agent audit and its fixes, 30 or more tests for 487 of the 496 problems, labelled test categories, and more suggested tests for imported questions. The audit's first run failed 2 of its checks: built-in hints for logic mistakes named nothing concrete in 8 of 16 cases, and the diagnosed cause could not be read from the trace. A later run caught a trace hint cut short by the sentence limit. All were fixed, and the final run passes. In the backend, 2 hint tests failed after the wording change: one level-1 wording ran past the sentence limit, and another dropped the words a pipeline test checks for. Both wordings were fixed. The full backend suite then passed in one run (522). The sandbox check passed for all 496 problems after the tests were regenerated with balanced answers. The execution service suite (39) was not re-run, because that code did not change.

**Earlier round.** This round added the profile page, the teacher's columns for each measure, the learner's own questions listed apart, 128 new problems and 3,223 generated tests. In the first full backend run, 2 of 499 tests failed. One was a test from earlier work that required the interaction record not to keep the situation vector; the record now keeps it on purpose, because the profile shows it, so the test was changed to check the vector is stored and within −1 to 1. The other was the hidden-answer check catching the new "What Kind of Number?" problem, whose answer `"text"` is also the name of its input type; the answer became `"not a number"`. Both passed on rerun, and the full backend suite was then run again (see the summary). Two browser tests counted 30 problems in one topic, which now has 37; they read the count from the API instead.

Not checked: real learners using the new interface, lessons, Learn panel or modes, or answering reflection questions; the AI-worded path with a real model (none is set up on this machine); browsers other than Chrome; and the exact window the Claude desktop app opens for a new-tab link. The built-in browser pane opens such links in the same tab, so the theme in a separate browser was tested with a fresh Playwright browser context instead.

## The repeated-hint bug

[bug-repeated-hint.md](bug-repeated-hint.md) has the reproduction and the fix. Before: 1 distinct hint in 5 clicks, in all 6 scenarios. After, in the real browser UI on the reported code: 4 different hints, then an honest wait with the button locked until the code changes.

## Scenarios required by the brief

| Scenario | Test |
|---|---|
| First syntax mistake | `test_first_syntax_mistake_gets_precise_help_now`, `test_syntax_error_flow` |
| Repeated logical error | `test_repeated_logic_error_escalates_one_level_at_a_time`, `test_repeated_errors_escalate_gradually_and_explainably` |
| Explicit small hint from a high-mastery learner | `test_explicit_small_hint_from_high_mastery_learner_is_honoured` |
| Progress after a hint | `test_progress_after_a_hint_fades_support_and_waits`, `test_progress_reduces_support` |
| High cognitive load | `test_high_load_gives_one_concise_action`, `test_high_load_hint_is_one_short_action` |
| Missing history | `test_missing_history_still_produces_a_decision` |
| Unknown confidence | `test_unknown_confidence_is_left_out_not_assumed` |
| No retrieval match | `test_no_retrieval_match_changes_nothing`, `test_retrieval_reports_no_match_when_appropriate` |
| Solved task | `test_solved_task_needs_no_help`, `test_correct_submission_skips_help_and_does_not_advance` |
| Full-solution leakage attempts | `test_full_solution_is_rejected`, `test_leaked_solution_from_the_model_is_blocked_then_retried`, `test_model_that_keeps_leaking_ends_in_built_in_hint`, `test_never_returns_the_solution_through_the_ladder`, `test_prompt_injection_in_code_cannot_change_the_policy` |
| Model failure | `test_model_failure_uses_labelled_fallback`, `test_provider_http_errors_become_a_fallback_signal` |
| Reflection deferred | `test_reflection_deferred_when_overloaded` |
| Planner keeps an unresolved task active | `test_planner_keeps_unresolved_task_active` |
| Correct code, wrong answer, runtime exception | `test_correct_code_returns_value`, `test_wrong_answer_is_just_a_value`, `test_runtime_exception_reports_student_line_only` |
| Infinite loop, excessive output, resource limits | `test_infinite_loop_times_out_and_later_tests_still_run`, `test_excessive_output_is_stopped`, `test_memory_bomb_is_contained`, `test_fork_bomb_is_contained_and_service_survives` |
| Runner failure | `test_runner_failure_is_reported_as_infrastructure`, `test_service_failure_is_not_treated_as_learner_mistake` |
| Submission persists through the workflow | `test_failed_submission_runs_every_agent_in_order`, `test_results_are_persisted_with_their_snapshot` |
| Agents receive prior outputs | `test_agents_receive_each_others_outputs` |
| Run, Submit and Hint semantics | `test_run_is_not_graded_and_starts_no_agents`, `test_hint_request_is_not_a_graded_attempt`, browser test "Run, Submit and Hint are separate" |
| No duplicates, even with concurrent clicks | `test_repeated_submission_with_same_key_creates_one_record`, `test_concurrent_double_click_creates_one_attempt` |
| Old results do not overwrite new ones | `test_older_results_never_overwrite_newer_state` |
| Sign-in and role restrictions | Browser "sign-in and roles", `test_teacher_sees_only_joined_students`, `test_teacher_cannot_see_another_teachers_class`, `test_students_cannot_read_each_others_work` |
| Problem selection, draft restoration, theme, editor | Browser "library and path", "editor", "appearance" |
| Submission, hint, reflection, dashboard consistency | Browser "beginner path", "class flow", `test_student_and_teacher_metrics_agree` |
| Keyboard navigation | Browser "keyboard: skip link, shortcuts, leaving the editor" |
| Responsive layouts | Browser "responsive": phone and tablet |
| Failure recovery | Browser "failure recovery", "copy controls and lost connections" |
| Import, generated tests, edit, delete | Browser "Add Question" (6 tests), plus API import tests |
| Second hint differs from the first, with history updated | `test_second_hint_on_unchanged_code_is_not_the_same_hint` |
| Repeated requests across syntax, logic, runtime, timeout | `test_repeated_requests_never_show_the_same_hint` (6 kinds), browser "asking repeatedly gives different help each time" |
| New error after a hint, and progress acknowledged | `test_new_error_after_a_hint_is_diagnosed_rather_than_repeating_the_old_one`, `test_progress_is_acknowledged_and_new_issue_starts_again`, browser "fixing an error is acknowledged" |
| Persisted state read by agents | `test_interaction_state_is_persisted_for_every_cycle`, `test_cognitive_state_updates_from_repeated_requests`, `test_diagnostic_compares_with_previous_version`, `test_previous_hint_outcome_reaches_the_next_decision` |
| Retrieval responds to state and history | `test_query_changes_when_the_learner_state_changes_materially`, `test_retrieval_does_not_suggest_what_this_learner_already_saw`, `test_reliable_retrieval_changes_the_real_decision_and_is_labelled` |
| Low-quality model text rejected | `test_low_quality_model_text_is_rejected` (6 kinds), `test_model_that_repeats_itself_is_rejected_then_labelled_fallback_is_used` |
| Link import safety | `test_addresses_that_are_not_public_websites_are_refused` (20), `test_names_resolving_to_private_addresses_are_refused` (13), redirect tests |
| robots.txt and terms respected | `test_robots_matching` (15), `test_sites_whose_terms_restrict_automation_are_never_contacted` (5) |
| Imported question through the whole workflow | `test_imported_link_question_works_with_the_whole_tutoring_workflow` |
| Rebrand, with saved data kept | Browser "the old product name is gone", unit "moving saved data to the new product name" |
| Profile: totals, improvement, calendar, learning state per topic, situation vector | `test_profile_counts_work_and_shows_the_learning_state`, `test_new_learner_profile_is_empty_not_an_error`, browser "the profile shows what was done" |
| Similar learners shown only as counts | `test_profile_shows_similar_learners_only_as_counts` |
| Teacher table with a column per measure, and each student's profile | `test_teacher_table_has_state_columns_and_student_profile`, browser "the teacher's table has a column for each measure" |
| The learner's own questions listed apart, with the date added | `test_your_questions_list_shows_when_each_was_added`, browser "Add Question: paste, review, generated tests, practise, edit, delete" |
| Every problem has a working reference and enough tests | `test_there_are_450_to_600_problems_and_at_least_15_in_every_topic`, `test_most_problems_have_many_tests_and_generated_ones_stay_hidden`, `scripts/verify_content.py` |

## Sandbox attacks tried from inside the sandbox

All were contained: network access, DNS, writing to the root filesystem and sandbox files, running from the temp folder, escalated privileges, reading secrets from the environment, reading host files or the supervisor's memory and file descriptors, killing the supervisor, memory exhaustion, a fork bomb, background processes outliving a test, forging harness output, and printing a fake pass marker.

## Bugs these tests found and I fixed

| Bug | Found by |
|---|---|
| DSDA could reach level 5 under sustained failure | Policy test |
| A hint on already-submitted code counted as a second graded attempt | Integration test |
| A concurrent double click raised a database error for some clicks | Warning from the integration test |
| Renaming a function during import left the starter code with the old name, so tests could not find it | Browser test |
| A blank, switched-off test blocked saving an imported question | Browser test |
| The CodeNet importer treated `problem_list.csv` as a problem file | Fixture test |
| 2 earlier curriculum tests could never be passed by correct code | Curriculum verification |
| Chart bars and scrollable tables failed accessibility rules | axe-core |
| The containerised runner image had no Docker CLI | Full-stack smoke test |
| The non-Docker sandbox profile stopped Python from starting | Running that suite |
| Hints repeated, in four separate layers | Reproduction against the real stack |
| Python's `robotparser` ignores `*`, and wrongly allowed pages robots.txt forbids | Comparing its answers with the real robots files |
| A long section on a real web page crashed the parser, which could also have affected paste | Live link import |
| Retrieval was reliable for only 0.15% of learner states | Measuring it across 10,800 states |
| A hint could reuse results from before an imported question's tests were edited | Writing the persistence tests |
| A skipped step could come back as a question straight after a worked example | Full test run |
| A false "may not be a problem statement" warning on Project Euler | Inspecting the real page by eye |
| The profile lost the situation vector and last match as soon as a problem was solved, because a correct submission runs no similarity search | Backend test for the profile |
| The "Your questions" group on Practice started closed, so the page could open with every group closed | Writing the browser test |
| The teacher's student page showed recent submissions, activity and totals twice after the profile was added | Inspecting the page by eye |
| A generated hidden answer matched a type label, which the hidden-answer check reported | Content test |
| Built-in hints for logic mistakes named neither the learner's loop, its line, nor the failing example | Agent audit |
| "Use a loop.", "Think carefully" and "Read the problem again" passed hint validation | Agent audit |
| The trace hint's question was cut off by the level's sentence limit | Agent audit |
| A full stop inside quoted code counted as the end of a sentence | Writing the hint-quality tests |
| Binary search had 7 hidden tests on an empty list, all answering -1 | Reading the Hidden tab's new category summary |
| Yes-or-no tasks had nearly all one answer, for example 2 true and 30 false | Measuring answer balance |
| The "Previously added questions" heading read "(1)0 solved" to screen readers | Inspecting the accessible name |

## Inspected by eye in the browser

Latest round: Add question with the collapsed and opened list of previous questions (light at desktop, dark at phone width, open state kept across navigation), the Hidden tab's category summary, and the hint card with its concept line. Previous round: the profile in the dark theme at desktop and phone width (no sideways page scroll; the topic table scrolls inside its card), the teacher's class table, and the teacher's view of a student in both themes. Earlier: welcome, onboarding, home, learning path, problem library, the workspace through the whole hint ladder and the waiting state, and Add Question through the link result and review. Real keystrokes confirmed auto-indent after a colon, undo, and the find and replace panel.

## Not verified

- **A real AI model.** No model was used in this work: `LLM_PROVIDER` is `none`, and the OpenAI key in `backend/.env` earlier returned `429 insufficient_quota`. Real hint wording, how often real text is rejected as a repeat, leak rates, latency and cost are unknown. Only adapters (mocked HTTP) and pipeline behaviour (scripted model) were tested.
- **Effectiveness with real learners.** No study has run, so there is no evidence the new hint ladder teaches better. No teacher has reviewed the hint text.
- **The 128 new problems with learners.** Their wording, difficulty labels and generated tests were checked by the build, the sandbox and a sample read by hand, not by learners or teachers.
- **`scripts/setup.sh` on a clean copy, and the whole stack in containers,** were not repeated after these changes. Only the backend install and the API image build were.
- **The non-Docker execution opt-in** was not re-run. Its code did not change.
- **Legal review.** Terms of service were read by hand on one date, and LeetCode's page could not be opened directly, so that entry comes from a search summary of its official terms.
- **Security review** of link import or the sandbox. SSRF protections were tested with simulated network responses only.
- **Real CodeNet data.** The importer was only run on a made-up fixture.
- **Linux hosts,** browsers other than Chrome, screen readers, and load.
- **Anthropic and Ollama** with real endpoints.
