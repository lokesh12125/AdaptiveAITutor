# Assessment of the earlier code, and decisions

## What existed

Branch `lokesh` held a working React and FastAPI app, with 120 passing tests and a 49-concept curriculum. It remains untouched on that branch. These problems were checked in its code and behaviour, not assumed:

| Finding | Evidence | Consequence |
|---|---|---|
| **A learner could fake a pass.** | `print('__ALL_TESTS_PASSED__'); raise SystemExit(0)` returned `passed: True`. Expected answers ran in the same process as student code. | Grading could not be trusted. |
| **Hidden tests reached the browser.** | `GET /api/problems/{id}` returned `test_cases_json`. | Expected answers were exposed. |
| **The token signing secret is in Git.** | `backend/.auth_secret` was committed in the first commit, and `origin` is GitHub. | Anyone with repository access could forge tokens for that app. |
| Teacher invite code had a hard-coded default, and CORS was `*` with credentials. | `main.py` | Weak access control. |
| Code execution used a subprocess with a denylist. | `code_runner.py` | Not isolation. |
| SQLite, where the report says PostgreSQL. | `database.py` | Deviation from the report. |
| The "cyclic" graph ran once per call, and its only loop was the leak verifier. | `tutor_graph.py` | The learning cycle was not modelled. |
| Retrieval searched 4 hand-written archetypes. | `vector_store.py` | "Similar learners" had no outcomes behind it. |
| "Learning gain" came from the tutor's own mastery estimate. | Your earlier audits, and the metrics code | Not a real measure. |
| Infrastructure failures appeared as learner runtime errors. | `code_runner.py` | Service problems looked like learner mistakes. |
| 2 curriculum tests could not be passed by any correct code. | `count_frequencies` expected string keys for integer and boolean items. Found by running reference solutions. | Learners would have been failed wrongly. |

## Decision: rebuild, keeping the content

The issues above sit in the architecture, so patching would have left most of the code replaced anyway. **Kept and converted:** the curriculum, 58 problems, lessons, placement questions as a starting idea, and the BKT idea. **Replaced:** everything else. `scripts/convert_legacy_curriculum.py` records how content was converted.

## Reversible decisions

Each of these is a project choice, not a requirement of the report.

| Decision | Why | How to change it |
|---|---|---|
| Syntax help now climbs the ladder | The earlier cap at L2 was a cause of the repeated-hint bug. A precise pointer is still the first step. |
| Waiting rather than repeating | When every kind of help has been shown on unchanged code, the tutor says so. An unlimited supply of reworded hints would look responsive without helping. |
| Respecting `noai` and `ai-input=no` | Page text can reach a language model, so these signals are treated as refusals. This means AtCoder statements are pasted. |
| Sites with restrictive terms are not contacted | LeetCode, HackerRank, GeeksforGeeks, CodeChef and Take U Forward. Terms were read on 9 November 2026 and can change. |
| Product name "CodePath" | Replaced the earlier working name at the team's request. It says what the product is: a path through code. The report names only the framework. | Search and replace the UI text, logo and titles. |
| Vite, React and TypeScript | Fast to run, no server rendering needed, and close to the earlier stack. | Replace `frontend/`, keeping the API. |
| CodeMirror 6 | Bundled locally, works on phones, good keyboard handling. The earlier Monaco setup loaded from a CDN. | Replace `workspace/Editor.tsx`. |
| Radix primitives with hand-written CSS tokens | Accessible behaviour without a generic look. | Replace `components/ui.tsx`. |
| Self-hosted fonts | No third-party requests for learners. | `main.tsx` |
| Opaque session cookie stored in PostgreSQL | Sign-out and revocation work, and scripts in the page cannot read it. | `security.py` |
| Polling every 350 ms for progress | Simple and reliable. Streaming is not needed at these durations. | `useActions.ts` |
| In-process worker pool with a per-learner queue | Enough for a project-scale deployment. | Replace `tutoring/service.py` scheduling with a job queue. |
| 17 units | The brief's 16, plus an optional "Python toolkit" holding classes, exceptions and iterators from the earlier curriculum. | `scripts/convert_legacy_curriculum.py` |
| Two public tests per curriculum problem | Enough to compare, while leaving edge cases hidden. | `public:` in the content files |
| Every weight and threshold in `policy.yaml` | Experimental starting values. | Edit that file. |
| LLM off by default | The system must work without a key or spending money. | `LLM_PROVIDER` in `.env` |
| Codeforces as the one link source | It has an official public API. | `imports/sources.py` |
| Hint outcomes pooled anonymously unless the learner opts out; research use is opt-in | Pooling carries no identity or code. Research use is a stronger step. | `preferences`, `research_consent` |

## Interface direction

The learner chose this after rejecting a dark, neon design. Twelve coding and learning sites were reviewed at desktop width on 9 November 2026: Exercism, freeCodeCamp, LeetCode, NeetCode, USACO Guide, Codecademy, Brilliant, Boot.dev, Programiz, Khan Academy, HackerRank and W3Schools. Only layout and interaction ideas were taken, not branding or content.

| Decision | Why | Idea from |
|---|---|---|
| Light by default, dark as a choice | Long reading is the main task, and most of the friendlier sites are light | Exercism, Programiz, Khan Academy |
| Top navigation labelled Learn and Practice | Plain words, and the content gets the full width | Exercism |
| Lesson and Practice tabs on each topic | Reading comes first, and the problems are one click away | Exercism, Programiz |
| One numbered line through the topics | Quick to scan and works on a phone. A tree map is harder to read at small sizes. | USACO Guide |
| Rows with one clear action | It is always obvious what to do next | HackerRank |
| Two panes while coding, three only above 1640 pixels | Three columns were cramped on a laptop, and the tutor still sits beside the code | LeetCode |
| No promotions, leaderboards or game themes | They compete with the learning for attention | Avoiding LeetCode, W3Schools and Boot.dev patterns |

