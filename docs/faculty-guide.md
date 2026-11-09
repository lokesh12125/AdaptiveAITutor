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
| Diagnostic | Code, test results, earlier issues | Facts, possible misconceptions with confidence, a stable issue label | Visible: a summary and details on request |
| Cognitive State | Diagnosis, attempt and hint history, time, self-report | Topic mastery range, and confusion, load, progress, or "unknown" | Mostly internal. Estimates are shown with explanations and can be hidden. |
| Similar Learner Retrieval | A situation vector | What helped in similar situations, or "no reliable match" | Internal. One line if it changed the help. |
| Adaptive Scaffolding | All of the above and hint history | Level, strategy, limits, timing, reason, then a validated hint | Visible: the hint, and why |
| Reflection | Situation and hint | One question, or nothing | Visible, sometimes |
| Learning Planner | Mastery, prerequisites, dependence on hints | Next step and why | Visible |

The student sees one tutor, not six messages.

## How does DSDA select help?

It is deterministic. A score combines mastery, confidence, confusion, load, repeated issues and hints that did not help, leaving out anything unknown. The score suggests a level on a ladder from an independent attempt (L0) to an analogous worked example (L4).

Rules then apply: an explicit request gets at least a small hint; support rises one step at a time when the same issue repeats without progress; support fades when the student improves; high load produces one short action; syntax errors get a precise pointer. A model can only choose the wording, and its text must pass a validator.

Many hints alone do not raise support. Only hints not followed by progress do.

## How does retrieval influence the decision?

The situation becomes a vector. ChromaDB finds similar past situations by cosine similarity, and PostgreSQL supplies which help was given and what happened next. If there is enough support, this can shift the level by one step and suggest a strategy, within DSDA's limits. Otherwise it reports no reliable match, and DSDA continues without it.

**Important limits:** similar does not mean effective. At launch there are no real outcomes, so the demo uses 400 clearly labelled synthetic records, which are excluded for real studies. CodeNet is not used here, because it contains no interventions.

## How does the system respond to failure?

| Failure | Response |
|---|---|
| Code runner down | Told it is not their code. Nothing counted. Retry offered. |
| Model down, or no key | Same help decision, with a built-in hint, labelled |
| Model leaks a solution | Rejected and rewritten, then a built-in hint |
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

**What is synthetic?** The 400 retrieval cases and the demo class. Both are labelled everywhere and can be switched off.

**How do you know the tests are right?** Each of the 90 problems has a reference solution that must pass, and a starter that must not. This found 2 wrong tests in the earlier curriculum.
