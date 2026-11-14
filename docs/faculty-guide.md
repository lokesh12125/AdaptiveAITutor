# Faculty guide: how the system works

This explains the implemented system. The report sets the goals, the six agents and their order, LangGraph, PostgreSQL, ChromaDB, cosine similarity and the metrics. The report does not specify the DSDA formula, the levels, the schema or the model, so those are this project's design choices, documented in [dsda.md](dsda.md) and [decisions.md](decisions.md).

## What happens after a student submits code?

1. The code is saved as an exact snapshot, with a key that stops duplicates.
2. A separate service runs it in a locked-down container, one process per test. The container has **inputs only**, and no answers.
3. The backend compares results to expected answers, and decides the verdict.
4. The six agents run in order on LangGraph.
5. Everything is saved in one transaction, and the student gets one coordinated response.
6. The graph **pauses** until the student's next action, which continues the same learning cycle.

## What does each agent receive and produce?

| Agent | Receives | Produces | Acts internally or visibly? |
|---|---|---|---|
| Diagnostic | Code, test results, earlier issues, the previous version of the code | Facts, possible misconceptions with confidence, a stable issue label, what changed since last time | Visible: a summary and details on request |
| Cognitive State | Diagnosis, attempt and hint history with outcomes, repeated requests, time, self-report | Topic mastery range, and confusion, load, progress, or "unknown", each with its evidence | Mostly internal. Estimates are shown with explanations and can be hidden. |
| Similar Learner Retrieval | A situation vector, and the approaches this learner already saw | What helped in similar situations, or "no reliable match" | Internal. One line if it changed the help. |
| Adaptive Scaffolding | All of the above and hint history | Level, strategy, limits, timing, reason, then a validated hint | Visible: the hint, and why |
| Reflection | Situation, hint, questions already asked, and the learner's own failing example, loop and technique | One question about the learner's own code, or nothing. Then a short reply to the answer that confirms, sharpens, or gives one small thing to try, without grading or giving the fix | Visible, sometimes. An unsure answer counts as confusion next time, and after a solve it earns one more problem of the same technique. |
| Learning Planner | Mastery, prerequisites, dependence on hints, each topic's techniques in lesson order, first-try solves, reflection answers | Next step and why, and a route: this topic and the next ones forward. Easy problems technique by technique, then medium, then hard, then the next topic | Visible |

The student sees one tutor, not six messages. Each agent reads the learner's stored history from the database before it acts. See the table in [agents.md](agents.md).

## How does DSDA select help?

It is deterministic. A score combines mastery, confidence, confusion, load, repeated issues and hints that did not help, leaving out anything unknown. The score suggests a level on a ladder from an independent attempt (L0) to an analogous worked example (L4).

Each issue then has its own ladder of different kinds of help, from a question up to a worked example on a different task. An explicit request gets at least a small hint. Support rises one step at a time when the issue persists, fades when the student improves, and starts again on a new issue. High load produces one short action, and syntax errors start with a precise pointer. A model can only choose the wording, and its text must pass a validator.

Many hints alone do not raise support. Hints not followed by progress do, and so does asking again without changing anything.

## How does the system prevent repeated hints?

Four layers, each of which was missing when the bug was found. See [bug-repeated-hint.md](bug-repeated-hint.md).

1. **Policy.** A kind of help used on an issue is not used again on it.
2. **Evidence.** Text uses the real line, token and failing example, so hints differ in substance.
3. **Validation.** Any hint too similar to an earlier one on the problem is rejected, whether written by a model or built in.
4. **An honest end.** When everything for this version of the code has been shown, the tutor says so, suggests one action and waits. Any code change reopens help, because new code is new evidence.

## What if the hints do not address what the student is stuck on?

The student types what confuses them in the tutor panel, and can select the lines they mean. That request runs the same six agents. The diagnostic also runs those lines on a visible example and records the real values, so the answer can say, for example, "`i` was 0, then 1, then 2, and `j` stayed 3". Different questions get different kinds of answer. An answer does not use up a step on the help ladder, and the request is open even after every hint has been shown.

With no language model configured, these answers are built by rules from that evidence. A model can reword them, but it receives the same evidence and limits, and it cannot override the decision or reveal the solution.

## How does the tutor find the real cause of an error?

Python's message says what failed, not why. For `name 'count' is not defined`, the Diagnostic Agent reads the learner's code to tell apart a missing import, a misspelling, a method called as a function, a variable from another function, and several other causes. It also reads the task text, function name, arguments and visible examples to work out what the learner was probably trying to do. Each result records its class, likely cause, concept, location, evidence and confidence.

The hint then starts with a question, and becomes more specific with each request. Before it is shown, the validator rejects text that only repeats the error, ignores the diagnosis, invents evidence, repeats an earlier hint, or gives away the solution.

## What does a student see while solving a problem?

- **Test cases before running.** Each problem shows its examples as Case 1, Case 2, with a box for each parameter. Students can edit a case or add their own. Pressing Run checks all of them, and an edited or new case gets its expected answer from the reference solution. A Hidden tab says how many more tests run on Submit.
- **Submission history.** Every submission is listed by day, with its time, result, tests passed and the code sent, which can be loaded back into the editor.
- **Theory beside the problem.** The Learn tab reads top to bottom: the problem in brief, then a tab per approach (for example Brute force, then the technique it practises) with intuition, steps and cost, followed by observations, common mistakes and edge cases.

## How is the learning material organised?

There are 17 topics and 496 problems, at least 19 per topic, with 15,717 tests: 487 problems have 30 or more. In the workspace, the Hidden tab says what kinds of case the hidden tests cover (for example empty input, repeated values or a large input) and what each kind checks, without showing inputs or answers. Each topic has notes covering why it matters, core definitions, how it works step by step, a diagram, syntax and runnable examples, techniques, common mistakes, edge cases, time and space cost, when to use it, related topics, knowledge checks, a revision summary and a glossary.

Beside every problem, a Learn panel explains what it is really asking, what goes in and out, what the constraints imply, the process to try on the first example, typical approaches with their complexity, common mistakes and edge cases, with links to the notes, prerequisites and related problems. Learners choose Guided, Practice, Revision or Interview prep, which changes what comes first. No mode overrides an explicit request for help or a safety rule. It never shows the solution to the current problem.

## What can students and teachers see about progress?

Every learner has a **profile** page. It shows problems solved and started, acceptance rate, first-try solves, solves without hints, streaks, an activity calendar, solves by difficulty and milestones. Under "How you have improved" it compares the first and latest solved problems (submissions, hints and minutes per solve) and shows solves week by week. Knowledge checks remain the only measure of learning gain.

The **learning state** table has one row per topic and one column per measure the tutor uses: mastery with its likely range and band, the starting estimate, how much evidence it rests on, solves alone and with help, confidence, confusion, workload and progress. The profile also shows the latest **situation vector** (the 14 numbers retrieval compares, each with its meaning) and the last similar-situation match as counts and an outcome rate.

Teachers see the same profile for any student in their class, and the class table has a column for each measure: solved, completion, mastery, topics, confidence, confusion, workload, progress, first try, submissions per solve, hints per solve, streak, last active and flags. Similar learners appear only as counts, never as names or code.

## How do we know each agent works?

`scripts/agent_audit.py` drives real scenarios through a running stack and checks each agent's output from the agent trace: repeated requests on unchanged code, syntax, runtime and timeout errors, progress, a new issue, a solve, a strong learner asking for a nudge, an overloaded learner, and no history. [agent-audit.md](agent-audit.md) reports each agent's inputs, outputs, issues found, fixes, tests and status, and [agent-audit-run.md](agent-audit-run.md) shows every row of the last run, including the exact hints shown. The audit found that built-in hints for logic mistakes were generic; they now quote the learner's own loop, line and failing example.

## How does retrieval influence the decision?

The situation becomes a vector. ChromaDB finds similar past situations by cosine similarity, and PostgreSQL supplies which help was given and what happened next. If there is enough support, this can shift the level by one step and suggest a strategy, within DSDA's limits. Otherwise it reports no reliable match, and DSDA continues without it.

It also leaves out what this learner has already seen, so the suggestion changes as their history does. In the demonstration data it finds a reliable match for about 12% of learner states, and says "no reliable match" for the rest.

**Important limits:** similar does not mean effective. At launch there are no real outcomes, so the demo uses 2,000 clearly labelled synthetic records, which are excluded for real studies. CodeNet is not used here, because it contains no interventions.

## How does the system respond to failure?

| Failure | Response |
|---|---|
| Code runner down | Told it is not their code. Nothing counted. Retry offered. |
| Model down, or no key | Same help decision, with a built-in hint, labelled |
| Model leaks a solution, repeats itself or invents evidence | Rejected and rewritten, then a labelled built-in hint |
| Every kind of help used on this code | Says so and waits for a change, rather than repeating |
| An agent crashes | Safe default, the cycle completes, and the failure is logged |
| Duplicate click | The same attempt |
| Editing during a check | The result is labelled as belonging to the earlier version |

## How will effectiveness be evaluated?

See [evaluation.md](evaluation.md). In short: learning gain comes from separate pre and post checks, never the tutor's own estimate, compared against a baseline, along with hints per problem, completion, time and satisfaction.

**Current status: this has been tested as software. It has not been evaluated with real learners, so there is no evidence yet that it improves learning.**

## Likely questions

**Why not one big prompt?** A prompt cannot guarantee a policy. Here the decision is inspectable code, testable without a model, and the model cannot override it.

**Where is the novelty?** Combining continuous state, retrieval of what helped, and an explicit help policy in one cycle. That claim needs checking against multi-agent tutoring literature, which the report's survey lacks.

**Is cognitive load really measured?** No. It is estimated from behaviour, needs more than one signal, and is reported as an estimate.

**What is synthetic?** The 2,000 retrieval cases and the demo class. Both are labelled everywhere and can be switched off.

**How do you know the tests are right?** Each of the 496 problems has a reference solution that must pass, and a starter that must not. This found 2 wrong tests in the earlier curriculum.
