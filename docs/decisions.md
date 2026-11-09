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
| Product name "Trellis" | A trellis supports growth, as scaffolding does. The report names only the framework. | Search and replace the UI text, logo and titles. |
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
