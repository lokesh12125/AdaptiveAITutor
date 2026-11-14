# Architecture

The report specifies the six agents and their order, LangGraph, PostgreSQL, ChromaDB, cosine similarity, a web platform and dashboards. Everything else in these diagrams is an implementation choice recorded in [decisions.md](decisions.md).

## Components

```mermaid
flowchart TD
    Browser["Browser: React and TypeScript"] -->|"JSON and session cookie"| API["FastAPI backend"]
    API --> Graph["LangGraph: learning cycle"]
    Graph --> Agents["Six agents"]
    Agents --> PG[("PostgreSQL: records and checkpoints")]
    Agents --> Chroma[("ChromaDB: situation vectors")]
    Agents -.->|"optional wording"| LLM["Model provider"]
    Graph -->|"internal token"| Runner["Execution service"]
    Runner -->|"one container per job"| Sandbox["Sandbox: no network, read-only, unprivileged"]
    Seed["Content and seed scripts"] --> PG
    Seed --> Chroma
    Import["CodeNet importer"] --> PG
    API -->|"one public page, on request"| Fetcher["Link import: address checks, robots.txt, limits"]
    Fetcher -->|"only if the site allows"| Web["External sites"]
```

**Why grading is safe:** the sandbox receives test inputs and returns what the code produced. Expected answers stay in the backend, and comparison happens there. Student code therefore cannot read answers or claim a pass.

## The LangGraph state graph

```mermaid
stateDiagram-v2
    [*] --> intake
    intake --> evaluate
    evaluate --> diagnostic: evaluated
    evaluate --> finalize: service failure or cancelled
    diagnostic --> cognitive_state
    cognitive_state --> retrieval: not solved
    cognitive_state --> dsda: solved
    retrieval --> dsda
    dsda --> generate_hint: give help
    dsda --> reflection: offer, wait or none
    generate_hint --> validate_hint
    validate_hint --> generate_hint: rejected, attempts left
    validate_hint --> reflection: accepted, built-in used, or nothing new to say
    reflection --> planner
    planner --> finalize
    finalize --> await_learner
    await_learner --> intake: the learner's next action
```

There are two real cycles:

- **The learning cycle.** `await_learner` calls LangGraph's `interrupt`. The state is checkpointed in PostgreSQL per learner and problem, and nothing runs until the learner acts. The next action resumes the same thread. No loop can generate more detailed hints by itself.
- **The validation cycle.** A rejected draft is rewritten at the same level and strategy, at most 3 attempts, and then a built-in hint is used. If that would repeat an earlier hint, the next unused step is tried, or the tutor waits. A rewrite cannot raise the level of help.

The report calls processing "sequential" (§5.1, p.4) and also "cyclic" (§6.3, p.8). This design satisfies both: agents run in sequence within a cycle, and the cycle repeats with each learner action.

## One submission

```mermaid
sequenceDiagram
    actor L as Learner
    participant W as Web app
    participant A as API
    participant G as LangGraph
    participant R as Execution service
    participant P as PostgreSQL
    participant C as ChromaDB
    L->>W: Submit
    W->>A: POST submit with an idempotency key
    A->>P: Save snapshot, evaluation and run
    A-->>W: 202 with the run ID
    A->>G: Resume the learner's thread
    G->>R: Inputs only, with no answers
    R-->>G: Values, output and errors
    G->>G: Grade on the trusted side
    Note over G: Diagnostic, then Cognitive State
    G->>C: Cosine query for similar situations
    C-->>G: Case IDs
    G->>P: Interventions and outcomes for those IDs
    Note over G: DSDA decides, text is generated, then validated
    Note over G: Reflection, then Learning Planner
    G->>P: Save everything in one transaction
    W->>A: Poll the run
    A-->>W: Real stage status, then one coordinated response
    W-->>L: What happened, next action, tests, hint
    Note over G: Paused until the learner acts
```

## One repeated hint request

```mermaid
sequenceDiagram
    actor L as Learner
    participant A as API
    participant G as LangGraph
    participant P as PostgreSQL
    L->>A: Ask for a hint, with unchanged code
    A->>P: New run, reuse the result for this exact code
    A->>G: Resume the learner's thread
    G->>P: Each agent reads hints, outcomes, decisions and earlier versions
    Note over G: Diagnostic states the code has not changed
    Note over G: Cognitive counts the repeated request as evidence
    Note over G: Retrieval leaves out approaches already seen
    Note over G: DSDA picks the next unused step on this issue's ladder
    Note over G: Validator compares the draft with every earlier hint
    G->>P: Save the hint and an interaction record
    A-->>L: A different kind of help, or "change your code and I will look again"
```

## One question about the code

The learner types what is confusing and can select lines in the editor. The request is `POST /problems/{id}/hint` with `question`, `focus_start` and `focus_end`, and it starts the same graph as any other hint.

```mermaid
sequenceDiagram
    actor L as Learner
    participant A as API
    participant G as LangGraph
    participant R as Execution service
    L->>A: "Why does it stop early?", lines 3 to 4
    A->>G: Start the cycle with the question and the lines
    Note over G: Diagnostic reads the question and looks at those lines
    G->>R: Run a visible example, recording values on those lines
    R-->>G: The values each variable held
    Note over G: Cognitive, retrieval and DSDA run as usual
    Note over G: DSDA chooses answer_question, which uses no ladder step
    Note over G: Validator rejects repeats and leaks, then tries another angle
    G-->>L: An answer using the real values, shown beside the code
```

Lesson examples use a separate route, `POST /playground/run`. It runs code in the same sandbox against a hidden scratch problem. It is never graded, starts no learning cycle, and does not count as work in progress.

## Event semantics

| Action | Runs | Graded? | Agents? | Changes mastery? |
|---|---|---|---|---|
| **Run** | Public examples, or the learner's own input | No | No | No |
| **Submit** | All enabled tests | Yes | All six | Yes |
| **Hint** | Public examples, or reuses the result for this exact code | No | All six | No |
| **Reflection answer** | Nothing | No | No | No. Stored as its own event. |
| Typing | Nothing. Autosave and a local parser only. | No | No | No |

## Ordering, duplicates and stale results

- Each result belongs to a code snapshot, and the response returns that code. If the editor has changed, the UI says the results are for an earlier version.
- An idempotency key makes a double click or retry the same attempt, enforced by a unique constraint.
- A per-learner queue applies actions in order, so an older result cannot overwrite newer state. The UI also follows only the newest request.

## Failure handling

| Failure | What the learner sees | What is recorded |
|---|---|---|
| Execution service down | "A problem on our side, not with your code", with Try again. Nothing is counted. | `evaluate` failed, later stages skipped with a reason. |
| Model provider down | A standard hint, labelled. | `generate_hint` status `fallback`, with provider metadata. |
| An agent crashes | The cycle completes with a safe default. | That stage `failed`, with error type. |
| Retrieval down or no match | Normal help, chosen without it. | Reason recorded. |
| Server restarts mid-run | Work marked failed, with a retry offered. | Recovered on startup. A fresh thread starts if a checkpoint is mid-cycle. |
| Connection lost when submitting | "Your code is safe", with Try again using the same key. | No duplicate. |
| A hint fails validation | A labelled standard hint, the next kind of help, or an honest wait. | `validate_hint` status `fallback`, with the violations, and a warning in the log. |
| A link cannot be read | What happened in plain words, and a route to paste with the link kept as the source. | Reason code in the response. |

## Repository layout

```text
backend/   FastAPI API, LangGraph, agents, policy.yaml, migrations, tests
runner/    Execution service, sandbox image and harness, tests
frontend/  React app, unit tests, Playwright end-to-end tests
content/   Units, problems, tests, reference solutions, topic lessons, knowledge checks
data/      Provenance notes and the importer's made-up test fixture
scripts/   Setup, development start, content verification, curriculum conversion, problem bank
docs/      This documentation
```
