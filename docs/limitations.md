# Known limitations

**Evidence**

- **No evidence yet that this improves learning.** It has not been used by real learners. Every weight and threshold is an unvalidated starting value.
- Confusion and load are behavioural estimates, not validated against any external measure.
- The pre and post checks are short and written to be parallel. They have not been statistically validated.
- Retrieval has only synthetic demonstration cases until real learners generate outcomes.

**Models**

- **A real model has not been tested end to end.** The available OpenAI key has no credit, so adapters were tested with mocked HTTP and the pipeline with a scripted model. Real hint quality and leak rates are unknown.
- The validator detects copied and lightly reworded solutions. A determined reworded explanation can still pass, and imported problems have no reference solution to compare with.

**Data**

- CodeNet: only the importer exists, tested on a made-up fixture. No real CodeNet data has been imported, because the archive is large. It is not used for retrieval, since it has no interventions.
- The 7 CodeNet-adapted problems have unverified wording provenance.
- Curriculum depth is modest: 90 problems across 17 units.

**Features**

- Python only. Roadmap: JavaScript, then Java or C++, only after Python is stable.
- Link import supports Codeforces only, and gives metadata without the statement.
- Pasted-text parsing is rule-based, so unusual formats need correcting at the review step.
- Generated tests propose inputs only. The learner must supply answers, apart from the "finishes in time" check.
- Classes and iterators work through expression tests in the curriculum, but imported questions support functions and standard input only.
- Hints are not a chat. Follow-up is through "I need more help" or a short question.

**Scale and operations**

- Single API process: the worker pool, per-learner queue and rate limits are in memory. Running several API processes would need a shared queue.
- Each job starts a container, so a Run takes about a second. There is no warm pool.
- No email verification, password reset, or multi-factor sign-in.
- Data retention is not automated.

**Security** See [security.md](security.md). In short: isolation is tested here but not audited, the Compose stack mounts the Docker socket, and the earlier signing secret stays in Git history.

**Testing gaps**

- Automated accessibility checks cover a portion of WCAG. No screen reader or keyboard-only user testing was done with real users.
- Browser tests ran on Chrome only, on macOS.
- The sandbox was tested on Docker Desktop for macOS, not on a Linux server.
- No load testing was done.
