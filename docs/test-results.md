# Test results

Run on 9 November 2026, on macOS (Apple Silicon, 8 GB RAM) with Docker Desktop 29.8, Python 3.12 and Node 26. Unless noted, these ran on a **clean copy**: only files Git would include, databases wiped, and set up with `./scripts/setup.sh`, then started with `./scripts/dev.sh`.

## Summary

| Suite | Result | What it uses |
|---|---|---|
| Execution service | **35 passed** | Real Docker sandbox containers |
| Execution service, non-Docker opt-in | **22 passed** | `local_dev_unsafe` backend, isolation tests excluded |
| Backend | **200 passed** | Real PostgreSQL, real execution service, real LangGraph and ChromaDB. **Model scripted.** |
| Frontend unit | **17 passed** | Vitest |
| Browser end-to-end | **34 passed** | Real Chrome against the full running stack |
| Accessibility (within the above) | **Passed, no violations** | axe-core, WCAG 2.0/2.1 A and AA rules, 11 screens or states, both themes |
| Curriculum verification | **90 of 90** | Each reference solution passes and each starter does not, in the real sandbox |
| TypeScript strict check, production build | **Passed** | `tsc`, `vite build` |
| Lint | **Passed** | Ruff on backend and runner. No ESLint for TypeScript. |
| Migrations | **Passed** | Up, down, up, and no model drift (`alembic check`), on a scratch database |
| Full stack in containers | **Smoke test passed** | `docker compose --profile full`: wrong and correct submissions, blocked network, no leftover containers |
| Codeforces API | **One live lookup passed** | The real public API |
| Clean setup | **Passed** | About 22 seconds with packages already cached |

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
| Import, generated tests, edit, delete | Browser "Add Question" (3 tests), plus API import tests |

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

## Inspected by eye in the browser

Welcome, onboarding, home, library, learning path, workspace with results and hints, Add Question, progress, settings and teacher dashboard. Light and dark themes on main screens, plus phone width for home and workspace, and tablet width by automated test only.

## Not verified

- **A real AI model.** The OpenAI key in `backend/.env` returned `429 insufficient_quota`. So real hint quality, real leak rates, latency and cost are unknown. Only adapters (mocked HTTP) and pipeline behaviour (scripted model) were tested.
- **Effectiveness with real learners.** No study has run.
- **Real CodeNet data.** The importer was only run on a made-up fixture in the documented format. The format was read from the repository page, not checked against a downloaded archive.
- **Linux hosts,** browsers other than Chrome, screen readers, and load.
- **A security audit** of the sandbox.
- **Anthropic and Ollama** with real endpoints.
