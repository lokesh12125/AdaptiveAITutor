# Dynamic Scaffolding Decision Algorithm (DSDA)

**The report names DSDA and its purpose: choosing assistance from cognitive state, hint history and response time (§3, p.3; §6.3, p.8). It gives no formula, weights, thresholds or levels.** Everything below is this project's proposal. All values are experimental starting choices in `backend/app/tutoring/policy.yaml`, not validated findings. Current version: `dsda-2.0`.

The LLM does not run in this module. It may word a hint, but it cannot change the level, the strategy, the presentation limits, the solution protection, or the decision to wait for the learner.

DSDA answers two questions separately, in `tutoring/dsda.py`:

1. **How much support does this learner seem to need?** The support score, from the learner's state.
2. **What should that support be, given what they have already seen?** The strategy ladder. This is what stops help repeating.

## The decision

```json
{
  "support_need_score": 0.472,
  "selected_level": 2,
  "strategy": "targeted_hint",
  "reason_codes": ["SUPPORT_NEEDED", "ESCALATE_NO_PROGRESS"],
  "evidence": { "mastery": 0.25, "hints_on_issue": 1, "used_strategies": ["conceptual_question"], "...": "..." },
  "presentation": { "max_words": 70, "one_action_at_a_time": false, "format": "hint", "max_sentences": 3, "allow_code": "none" },
  "constraints": { "allow_complete_solution": false, "allow_analogous_example": false },
  "await_learner_action": true,
  "policy_version": "dsda-2.2"
}
```

`allow_complete_solution` and `await_learner_action` are literal types in `contracts.py`. No configuration, model reply or code path can change them. The decision also records `action`, `timing`, `focus_issue`, `theme`, `score_components`, `used_retrieval` and `reason_student`.

## The help ladder

| Level | Name | Format | Limits |
|---|---|---|---|
| L0 | Independent attempt | No unsolicited hint | |
| L1 | Conceptual question | Question | 2 sentences, 45 words |
| L2 | Targeted hint | Hint | 3 sentences, 70 words |
| L3 | Step-by-step outline | Numbered steps, no code | 110 words |
| L4 | Analogous worked example | Code on a different task | 150 words of prose |

## Strategies

Each issue climbs its own ladder, one unused step at a time. A strategy is how help is framed. The issue decides what it is about.

| Step | Most issues | Level | Syntax errors | Level |
|---|---|---|---|---|
| 1 | `conceptual_question` | 1 | `syntax_pinpoint` | 2 |
| 2 | `targeted_hint` | 2 | `syntax_read_tokens` | 2 |
| 3 | `trace_failing_case` | 2 | `syntax_checklist` | 3 |
| 4 | `print_debugging` | 2 | `syntax_analogous_line` | 4 |
| 5 | `step_outline` | 3 | `syntax_exact_fix` | 4 |
| 6 | `analogous_example` | 4 | | |
| 7 | `direct_pointer` | 4 | | |

A missing name has its own ladder: `conceptual_question` (1), `targeted_hint` (2), `name_options` (2), `step_outline` (3), `analogous_example` (4), `direct_pointer` (4). Tracing and printing are left out, because the line never runs. Issue keys carry the cause, such as `runtime:NameError:missing_import`, so a different cause starts its own ladder. Retrieval compares on the family, `runtime:NameError`.

`trace_failing_case` is skipped when no visible failing example exists, and for code that has not been written yet. `print_debugging` is skipped for timeouts, memory and output limits, where more printing would make things worse, and for code that has not been written yet. A missing function has no worked example. `direct_pointer` names the failing case and what to compare, the most direct help short of the solution.

| Situation | What happens | Code |
|---|---|---|
| First request on an issue | Starts at the score's level, at most L2 | `FIRST_CONTACT` |
| Asked again, same code, after a pause | Next unused step. High need may jump to more structure. A skipped step at L2 or above comes back before the tutor stops on unchanged code, since it is still help the learner has not seen. A conceptual question does not. | `ESCALATE_SAME_CODE` |
| Asked again within 12 seconds | Next unused step, never skipping ahead | `RAPID_REREQUEST` |
| Changed the code, same issue, no progress, and asked | Next unused step | `ESCALATE_NO_PROGRESS` |
| Submitted again without asking, same issue, after a hint | **The next step is offered, not shown.** The learner tries their own idea first, and asking shows it, at most one level above the last. Help never climbs the ladder unasked. | `OFFER_NEXT_STEP` |
| "I need more help" | The next unused step, in order. It never jumps over a kind of help. | `MORE_REQUEST` |
| A typed question, or lines pointed at | `answer_question`, built from what the code really did. It does not use up a ladder step, and it works when the ladder is used up and on solved code. | `QUESTION_ASKED` |
| "Just a small nudge" | Stays at L2 or below until those steps are used | `SMALL_REQUEST`, `NUDGE_LADDER_USED` |
| Progress after a hint | Lighter unused help, and progress is acknowledged | `FADE_PROGRESS` |
| A different issue appears | Its own ladder, from the start | `NEW_ISSUE` |
| Ladder used up, code changed | Looks at what the change did, using the comparison | `EVIDENCE_REVIEW` |
| Ladder used up, same code | **No new hint from a plain request.** Says so, suggests one action, and offers the question box. | `LADDER_EXHAUSTED` |
| Solved | No corrective hint. A reflection question consolidates. A typed question is still answered. | `SOLVED` |

### What the learning mode changes

The learner's mode changes what is presented, and one default. Practice mode turns off hints nobody asked for, so a failed submission gets an offer. Guided, Revision and Interview prep keep the normal behaviour. No mode changes explicit requests, the ladders, the limits or the validator.

### When the learner asks something

A question goes through the same graph as any other request: diagnostic, cognitive state, retrieval, DSDA, validation, reflection and planner. Three things differ.

1. `questions.py` reads the text as one of these intents: `why_fails`, `where_wrong`, `how_start`, `next_step`, `explain_code`, `error_meaning`, `concept`, `solution_request`, `overwhelmed` or `general`. The text selects a kind of answer. It can never change the policy, the limits or the solution constraint.
2. Selected lines become the focus, then any "line N" in the text. If neither is given and the code ran, the tutor looks at the line it has evidence about. Those lines are then run on a visible example with tracing, so the answer can state real values. Syntax errors are not traced, because nothing ran.
3. Each intent has an ordered list of angles, for example where the result differs, what the lines do one at a time, or how to begin. The validator still rejects a repeat or a leak. A rejected answer moves to the next angle, then to the next ladder step. Only when all of these are used does the tutor say that is everything it can work out from this version of the code.

Presentation for answers is set in `policy.yaml` under `presentation.question`: 8 sentences and 140 words, with no solution code.

## Support score

```text
S = weighted average of the known inputs − progress credit

  low mastery       0.22 × (1 − mastery)                      0.5 if there is no evidence
  low confidence    0.08 × (1 − confidence)                   left out if unknown
  confusion         0.18 × level value                        left out if unknown
  cognitive load    0.08 × level value                        left out if unknown
  repeated issue    0.16 × (repeats − 1) / 3
  unhelpful hints   0.12 × unhelpful hints / 2                includes a thumbs-down
  repeat requests   0.12 × hints on this exact code / 3
  stalled time      0.04 × time since last action / 10 min    left out if unknown
  progress credit  −0.15 when visibly improving, or when the code gets further than before
```

Level values are low 0.2, moderate 0.55, high 0.9. Weights are rescaled over the inputs that are known, so an unknown never counts as a value.

**S below 0.20 → L0, below 0.40 → L1, below 0.60 → L2, below 0.80 → L3, otherwise L4.**

Many hints alone do not raise S. Hints not followed by progress do, and so does asking again without changing anything.

## Limits

Applied so nothing can break them:

- Never more than one level above the last on this issue. A new issue starts at L2 or below.
- L3 needs an earlier attempt or hint on the issue. L4 needs 2 earlier hints on it.
- High load caps at L3, and allows one short action of up to 40 words.
- An explicit request gets at least L1.
- Retrieval needs support of at least 3 and effectiveness of at least 0.55. It may shift the level by at most 1, may pick among **unused** steps only, and is recorded and shown to the learner.

## Timing

| Situation | Timing |
|---|---|
| Learner asked | Show now |
| Syntax error | Show now |
| Score maps to L0 | Offer a button, and wait |
| Improving | Offer, and wait |
| Experienced on this topic and first failure | Offer, and wait |
| Automatic hints turned off | Offer, and wait |
| Solved | Not needed |
| Service failure | Wait. No help without evidence. |

After any intervention the graph pauses until the learner acts.

## Worked example

A learner's second attempt with the same off-by-one bug. Known: mastery 0.25 with evidence, confusion moderate, repeats 2, one unhelpful hint, no repeat requests. Unknown: confidence, load and time, which are left out.

```text
weights in use: 0.22 + 0.18 + 0.16 + 0.12 + 0.12 = 0.80
mastery   0.22 × 0.75 / 0.80 = 0.206
confusion 0.18 × 0.55 / 0.80 = 0.124
repeats   0.16 × 0.33 / 0.80 = 0.067
unhelpful 0.12 × 0.50 / 0.80 = 0.075
repeat requests 0            = 0
S = 0.472, which maps to L2
```

Suppose the last hint was L1. The next step at or above L2 is `targeted_hint`. **Result: L2, offered; shown when the learner asks.** This was a submission, not a request, and the learner already had one hint on this issue, so the hint waits behind "I need more help". The offer card says one thing, once: "You have already had a hint on this, so try your own next idea first. The next hint is here whenever you want it. It will focus on where your loop or range starts and stops, because answers differ by exactly one." The reasons for the level (`ESCALATE_NO_PROGRESS` and the repeated issue) stay in the decision record. If they ask, the same L2 `targeted_hint` is shown, with the full reason under "Why this hint?" (`test_worked_example_in_the_documentation_is_accurate`).

## Generation and validation

`hints.py` writes the text from the decision: built-in text chosen by strategy and filled with observed evidence, or an LLM prompt carrying the task, the learner's code, public facts, exact evidence, the limits and every hint already shown. The prompt never contains the reference solution or hidden tests. Learner text is delimited and treated as data.

The validator rejects a draft for:

- a code block below L4, or two or more code-like lines
- defining the target function
- 25% or more overlap with the reference solution's token sequences, even when reworded or unfenced
- rewriting the learner's own code
- containing hidden test values
- mentioning internal details such as a system prompt
- being too long, or not being a question at L1
- **repeating an earlier hint:** similarity of 0.8 or more with any hint on this problem, ignoring case and punctuation
- **vague advice** such as "try again" with nothing specific
- **invented line numbers:** naming a line the code does not have
- **invented test results:** counts that match neither this result nor the previous one
- **contradicting the diagnosis,** such as "your code is correct" on a failure, or "syntax error" on a logic error
- **going off topic,** for model text: not addressing the diagnosed issue

A rejected AI draft is rewritten at the same level and strategy, up to 3 attempts in total, and each retry says what was wrong. After that, a built-in hint is used and labelled. If the built-in text is also rejected, the next unused step is tried. If nothing can pass, no hint is shown and the tutor waits. Every rejection is logged and recorded on the `validate_hint` step.

## Reason codes

`SOLVED, NO_EVIDENCE, SERVICE_UNAVAILABLE, EXPLICIT_REQUEST, SMALL_REQUEST, MORE_REQUEST, NUDGE_LADDER_USED, FIRST_CONTACT, NEW_ISSUE, SYNTAX_PRECISE, ESCALATE_NO_PROGRESS, ESCALATE_SAME_CODE, RAPID_REREQUEST, EVIDENCE_REVIEW, LADDER_EXHAUSTED, REPEATED_ISSUE, FADE_PROGRESS, PROGRESS_NO_HELP, OFFER_NEXT_STEP, HIGH_LOAD_CONCISE, OFFER_INDEPENDENT, AUTO_HINTS_OFF, RETRIEVAL_ADJUSTED, RETRIEVAL_ADJUSTED_DEMO, LOW_NEED, SUPPORT_NEEDED`

## Tuning it

Change `policy.yaml` and its `policy_version`, then restart. Weights, thresholds, ladders and the repeat threshold are all there. Each hint and run records the version that produced it, so policies can be compared. Weights have not been tuned on real data. Doing that requires a pilot, as described in [evaluation.md](evaluation.md).
