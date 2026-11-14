# Known limitations

**Evidence**

- **No evidence yet that this improves learning.** It has not been used by real learners. Every weight and threshold is an unvalidated starting value.
- Confusion and load are behavioural estimates, not validated against any external measure.
- The pre and post checks are short and written to be parallel. They have not been statistically validated.
- Retrieval has only synthetic demonstration cases until real learners generate outcomes. With those it is reliable for about 12% of learner states, so it often has no effect.
- The rule that a hint repeats at 0.8 similarity, and the 12-second rule for asking again quickly, are starting values. Neither has been tested with learners.

**Models**

- **A real model has not been tested end to end.** The available OpenAI key has no credit, so adapters were tested with mocked HTTP and the pipeline with a scripted model. Real hint quality, leak rates and how often model text is rejected as a repeat are unknown. Everything observed in this work used built-in hints.
- The relevance check on model text is keyword based. It catches clearly unrelated text, not subtly wrong advice.
- The validator detects copied and lightly reworded solutions. A determined reworded explanation can still pass, and imported problems have no reference solution to compare with.

**Data**

- CodeNet: only the importer exists, tested on a made-up fixture. No real CodeNet data has been imported, because the archive is large. It is not used for retrieval, since it has no interventions.
- The 7 CodeNet-adapted problems have unverified wording provenance.
- 496 problems across 17 topics. All of them pass verification in the sandbox, but 406 were written for this project, 128 of them in the latest pass, and none has been used by real learners yet. Difficulty labels and lesson wording are the author's judgement.

**Features**

- Python only. Roadmap: JavaScript, then Java or C++, only after Python is stable.
- **Link import cannot read the statement from any of the named coding sites.** Five forbid automated access in their terms, AtCoder marks its pages `noai`, and the Codeforces API has no statements. For these, the link gives attribution and the learner pastes. Full reading works on other public pages that allow it, such as educational sites and blogs. See [data-imports.md](data-imports.md).
- Terms of service cannot be read by a machine. Only the sites listed in `imports/sources.py` are known to restrict access. For any other site, the checks are robots.txt and machine-readable signals.
- Reading a page is heuristic. Layouts vary, so fields can be incomplete or wrong until reviewed. Pages that need a browser to render, or a sign-in, cannot be read.
- Pasted-text parsing is rule-based, so unusual formats need correcting at the review step.
- Built-in hints have 4 to 7 kinds of help per issue, depending on the error. After those, plain requests on unchanged code stop by design, and questions stay open until their answers are used up too.
- Generated tests propose inputs only. The learner must supply answers, apart from the "finishes in time" check.
- Classes and iterators work through expression tests in the curriculum, but imported questions support functions and standard input only.
- Finding the cause of an error is rule-based. The analyser covers common causes, and an unusual error falls back to general help. A likely cause is what the code suggests, not a claim about what the learner meant, and it carries a confidence.
- The Learn tab combines theory written per technique (74 techniques, with steps for each approach) with facts worked out from each problem's task and visible examples. It is not hand-written for each of the 496 problems, so two problems that practise the same technique share most of their theory. Complexity is typical for the technique, so a specific problem can differ. The steps of the main approach are one click away rather than shown at once, so a learner can try the idea first.
- 13,052 hidden tests were generated for 493 of the 496 problems, so there are 15,717 in all. 487 problems have 30 or more (median 32, at most 34). Answers always come from the reference solution. Inputs come from what a problem's examples share, from a generator written for that problem (valid trees, loop-free course rules, a single planted answer, valid operation lists), or, for classes and generators, from scripts of valid calls. Tests are chosen from a larger pool to cover different kinds of case (empty, single item, all the same, sorted, reverse sorted, repeated values, negative numbers, zero, one, large numbers), not to reach a number with near-copies. Selection also balances answers and penalises repeating both the kind of case and the answer: binary search, for example, went from 7 hidden tests on an empty list (all answering -1) to at most 5 tests sharing any one answer. Yes-or-no tasks get both answers where the task allows; perfect-number-check stays mostly false because only 4 perfect numbers exist in its range. 53 tests use large inputs, and the 6 problems whose task asks for an efficient approach also get 20,000 values, where a quadratic solution runs out of time. Large tests exist only where the answer is short, because the sandbox caps output at 64 KB. A correct solution relying on a rule a generator misses could still fail a generated test, so inputs were sampled and read by hand, and every test passes against the reference solution in the sandbox. 9 problems stay under 30 because they have few possible inputs: two take none, rock-paper-scissors has 9 pairs, a month has 12 values, some take n up to 9, and a recursive Fibonacci becomes too slow past n = 22.
- When a learner edits a test case or adds one, its expected answer comes from running the reference solution on that input. An input the task does not allow can still get an answer this way, and the tutor marks a case "may not be a valid input" only when the reference solution fails on it. Imported questions have no reference solution, so their edited cases show output only.
- The profile's improvement comparison needs at least four solved problems, and uses submissions, hints and time per solve, which also depend on which problems were chosen. Only the knowledge checks measure learning gain. Mastery, confidence, confusion, workload and progress are the tutor's estimates from coding activity, not grades, and they are shown with how much evidence they rest on.
- The profile shows the situation vector and the last similar-situation match as numbers and counts only. It never shows another learner's identity, code or answers, and a match is not evidence that a kind of help will work for this learner.
- Imported questions get up to about 14 suggested tests (typical, smallest, boundary, negative, zero, all the same, duplicates, sorted, reverse sorted, different order, large), not 30, because an imported question has no reference solution: each suggested answer must come from the learner, and stays off until they enter it.
- Built-in hints quote the learner's own loop, line, variables and failing example for 10 common logic and timeout issues. Other issues use general wording that names the failing example when there is one.
- The development database also holds pooled outcomes from automated test and audit runs, which retrieval counts as live there. Use a fresh database for any study.
- Topic notes use text diagrams, not interactive visualisations. Time complexity, operators, dictionaries, sets and sorting are covered inside other topics rather than as topics of their own.
- Learning modes change presentation and one default, as described in [dsda.md](dsda.md). They have not been evaluated with learners.
- Asking the tutor is not a free conversation. With no model configured, a question is matched to a kind of answer by keywords, so an unusual question gets a general answer built from the evidence, and it may not address the exact wording. A configured model rewords answers, but only from the same evidence and inside the same limits. Each question stands alone, apart from the record of earlier help.
- Reflection replies spot the key idea of an answer by keywords. A correct answer in unusual words can be read as partial, and then gets one more thing to check. No study has checked that the replies improve how learners explain their reasoning.
- The planner's sequence (each technique at easy, 2 solves or 1 on the first try without hints, then medium, then hard, then the next topic forward) is a teaching judgement. It has not been compared with teachers' choices or tuned on real learners.
- After a first hint on an issue, more help on that issue is offered rather than shown until the learner asks. A learner who never asks gets no further hints on that issue, by design.
- Tracing covers visible examples only, and shows at most 40 events, 12 variables and 80 characters per value. Code that needs a very long run before reaching the selected lines may not show them.

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
