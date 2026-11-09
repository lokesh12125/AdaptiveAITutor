# Dynamic Scaffolding Decision Algorithm (DSDA)

**The report names DSDA and its purpose: choosing assistance from cognitive state, hint history and response time (§3, p.3; §6.3, p.8). It gives no formula, weights, thresholds or levels.** Everything below is this project's proposal. All values are experimental starting choices in `backend/app/tutoring/policy.yaml`, not validated findings. Current version: `dsda-1.0`.

The LLM does not run in this module and cannot change a decision.

## The help ladder

| Level | Name | Format | Limits |
|---|---|---|---|
| L0 | Independent attempt | No unsolicited hint | |
| L1 | Conceptual question | Question | 2 sentences, 45 words |
| L2 | Targeted hint | Hint | 3 sentences, 70 words |
| L3 | Step-by-step outline | Numbered steps, no code | 110 words |
| L4 | Analogous worked example | Code on a different task | 150 words of prose |

## Need-for-help score

```text
S = weighted average of the known inputs − progress credit

  low mastery       0.25 × (1 − mastery)        0.5 if there is no evidence
  low confidence    0.10 × (1 − confidence)     left out if unknown
  confusion         0.20 × level value          left out if unknown
  cognitive load    0.10 × level value          left out if unknown
  repeated issue    0.20 × (repeats − 1) / 3
  unhelpful hints   0.15 × unhelpful hints / 2
  progress credit  −0.15 when visibly improving
```

Level values are low 0.2, moderate 0.55, high 0.9. Weights are rescaled over the inputs that are known, so an unknown never counts as a value.

**S below 0.20 → L0, below 0.40 → L1, below 0.60 → L2, below 0.80 → L3, otherwise L4.**

**Hints alone never raise S.** Only hints not followed by progress do.

## Rules applied after the score

In order, with hard limits last so nothing can break them:

1. **Fade:** improving on the same issue → below the last level.
2. **Escalate:** no progress after a hint on this issue → the last level + 1.
3. **Repetition:** the same issue, with no hint yet → at least L2.
4. **More requested:** "I need more help" → the last level + 1.
5. **Retrieval:** reliable evidence (support ≥ 3, effectiveness ≥ 0.55) may shift the level by at most 1 and suggest a strategy. It is recorded and shown to the learner.
6. **Hard limits:**
   - At most L4, and never more than one step above the last level on this issue.
   - A new issue starts at L2 or below.
   - L3 needs an earlier attempt or hint on the issue. L4 needs 2 unhelpful hints.
   - Syntax issues stay at L2, as a precise pointer.
   - High load caps at L3, and allows one short action of up to 40 words.
   - An explicit request gets at least L1. "Just a nudge" stays at L2 or below.

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

A learner's second attempt with the same off-by-one bug. Known: mastery 0.25 with evidence, confusion moderate, repeats 2, one unhelpful hint. Unknown: confidence and load, which are left out.

```text
weights in use: 0.25 + 0.20 + 0.20 + 0.15 = 0.80
mastery   0.25 × 0.75 / 0.80 = 0.234
confusion 0.20 × 0.55 / 0.80 = 0.138
repeats   0.20 × 0.33 / 0.80 = 0.083
unhelpful 0.15 × 0.50 / 0.80 = 0.094
S = 0.549, which maps to L2
```

Suppose the last hint was L1. Rule 2 asks for at least L2, and the hard limit allows at most L2. **Result: L2.** The student sees: "This focuses on where your loop or range starts and stops, because answers differ by exactly one, and the same issue appeared in 2 attempts. The last hint on this issue did not lead to progress, so this one gives more support."

## Generation and validation

`hints.py` writes the text from the decision: built-in templates, or an LLM prompt carrying the task, the learner's code, public facts and the limits. The prompt never contains the reference solution or hidden tests. Learner text is delimited and treated as data.

The validator rejects a draft for:

- a code block below L4, or two or more code-like lines
- defining the target function
- 25% or more overlap with the reference solution's token sequences, even when reworded or unfenced
- rewriting the learner's own code
- containing hidden test values
- mentioning internal details such as a system prompt
- being too long, or not being a question at L1

A rejected AI draft is rewritten at the same level, up to 3 attempts in total. After that, a built-in hint is used and labelled.

## Reason codes

`SOLVED, NO_EVIDENCE, SERVICE_UNAVAILABLE, EXPLICIT_REQUEST, SMALL_REQUEST, MORE_REQUEST, FIRST_CONTACT, SYNTAX_PRECISE, ESCALATE_NO_PROGRESS, REPEATED_ISSUE, FADE_PROGRESS, PROGRESS_NO_HELP, HIGH_LOAD_CONCISE, OFFER_INDEPENDENT, AUTO_HINTS_OFF, RETRIEVAL_ADJUSTED, RETRIEVAL_ADJUSTED_DEMO, LOW_NEED, SUPPORT_NEEDED`

## Tuning it

Change `policy.yaml` and its `policy_version`, then restart. Each hint and run records the version that produced it, so policies can be compared. Weights have not been tuned on real data. Doing that requires a pilot, as described in [evaluation.md](evaluation.md).
