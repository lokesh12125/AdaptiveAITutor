# Evaluation

The report's Objective 5 tests effectiveness on programming datasets (§3, p.3), while its metrics need real learners (§5.2, p.4). So there are two parts. **No effectiveness result exists yet. The system has only been tested as software, and it has not been used with real learners.**

## Metrics

All of these are computed from stored records (`app/analytics.py`). Student and teacher views share the same code, and a test checks that they agree.

| Metric | Report | Formula here | Missing data | Limits |
|---|---|---|---|---|
| Completion rate | §5.2 | Problems solved ÷ problems with at least one graded attempt | No attempts: no value | Problems never tried are not counted |
| Hints per solved problem | §5.2 | Hints on solved problems ÷ problems solved | No solves: no value | Fewer is not automatically better |
| Hint efficiency | §5.2, without a separate definition | Hints followed by progress or a solve ÷ hints with a known outcome | Unresolved hints left out | **Shows association, not cause** |
| Time to completion | §5.2 | Median active seconds at first accepted submission | Solves with no time left out, with the count shown | Ignores unsolved problems. Read it with completion rate. |
| Topic mastery | §3 | BKT estimate, shown as a range | "Not enough evidence" | **Not a measure of learning gain** |
| Learning activity | §5 | Runs, submissions and hints per day | Zero | |
| Satisfaction | §5.2 | Median of 4 Likert items, with response count | No value | Self-report, and small samples |
| Learning gain | §5.2 | (post − pre) ÷ (max − pre), for learners with both checks | **Not shown** until both exist | The two forms are parallel by design, but not validated |

**The tutor's own mastery estimate is never used as learning gain.**

## Part A: offline, on datasets (Objective 5)

| Question | Method | Data |
|---|---|---|
| Are curriculum tests correct? | Reference solutions must pass, and starters must not. **Done: 90 of 90.** | `content/` |
| Does mastery estimation predict results? | Replay attempt sequences and measure AUC for the next result | CodeNet sequences (import needed) |
| Are difficulty values sensible? | Compare ratings and acceptance rates to the order used | `dataset_problem_stats` |
| Does the validator stop leaks? | Fixed attack prompts, and measure the leak rate | Scripted now. Needs a real model. |

## Part B: user study

| Item | Suggestion |
|---|---|
| Design | Random assignment, balanced on the starting check |
| Baseline | The same interface with a plain LLM assistant, or with fixed hints |
| Treatment | Full CSMASF |
| Procedure | Starting check, a tutoring session on a shared problem set, follow-up check, survey |
| Size | About 30 or more, understood as a pilot |
| Analysis | Normalised gain compared between groups, with an effect size. Treat a small study as preliminary. |
| Ablation | Compare without retrieval (`RETRIEVAL_ALLOW_SYNTHETIC=false` with no live data), with DSDA constrained via `policy.yaml`, and with a fixed problem order |
| Ethics | Institutional approval, informed consent, `DEMO_MODE=false` |

Before a study, also check that the estimates mean something by comparing confusion and load estimates with a short self-rating.
