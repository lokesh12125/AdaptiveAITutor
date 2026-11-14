# Data, provenance and import notes

This project keeps four kinds of data apart. They are stored, labelled and reported separately.

| Kind | Where it lives | Provenance label | May it be reported as evidence that tutoring works? |
|---|---|---|---|
| Curriculum and tests | `content/` | `curriculum`, `codenet_adapted` | No. It is course material. |
| Programming dataset statistics | `dataset_problem_stats` table | `dataset` column, with a note | No. It describes CodeNet submitters, not tutoring. |
| Real learner events and hint outcomes | `evaluations`, `hints`, `intervention_cases` with `provenance='live'` | `live` | Yes, for consenting real participants, with the limits in `docs/evaluation.md`. |
| Synthetic demonstration records | `intervention_cases` with `provenance='synthetic'`, users with `is_synthetic=true` | `synthetic` | **Never.** |

## IBM Project CodeNet

The report names CodeNet as the primary dataset. Its public repository (https://github.com/IBM/Project_CodeNet, checked on 8 November 2026) documents:

- 13,916,868 submissions, 4,053 problems and 55 languages, from AIZU Online Judge and AtCoder.
- Per-submission metadata: `submission_id, problem_id, user_id, date, language, original_language, filename_ext, status, cpu_time, memory, code_size, accuracy` (AIZU only).
- Per-problem metadata, including a difficulty rating. The tags column is marked "not used".
- Problem descriptions for most problems, and sample input and output where they could be extracted.

It does **not** document tutoring conversations, hints, hint outcomes, student confidence or cognitive-load labels. This system therefore never treats CodeNet as evidence about interventions. The repository page lists Apache-2.0 for the repository itself and does not state the dataset's licence on that page. **Confirm the dataset's terms on the official dataset page before redistributing any of it.** The report says "research and academic use".

### What is actually included here

- `content/problems/legacy.json` has 7 problems marked `codenet_adapted`. They came from this project's earlier version, where they were rewritten as function exercises. The original problem IDs are kept, but the wording's provenance has not been independently verified. They are labelled as such in the app.
- **No CodeNet submissions or source code are included in this repository.**
- `data/codenet/fixture/` is a tiny **made-up** file set in CodeNet's documented format, used only to test the importer. It contains no real CodeNet data.

### Import workflow

1. Download the metadata archive using the instructions in the CodeNet repository. It is large, so it is not fetched automatically. Keep it outside Git (`data/codenet/raw/` is ignored).
2. Preview, which writes nothing:

   ```bash
   cd backend
   .venv/bin/python -m app.imports.codenet --metadata-dir ../data/codenet/raw/metadata --language Python --dry-run
   ```
3. Import aggregates, optionally limited to some problems:

   ```bash
   .venv/bin/python -m app.imports.codenet --metadata-dir ../data/codenet/raw/metadata --language Python --problems p00000,p00001
   ```

**Preprocessing decisions**

| Decision | Reason |
|---|---|
| Keep only the chosen `language`. | The tutor supports Python only. |
| Drop `Judge Not Available`, `Waiting for Judging`, `Waiting for Re-judging`, `Internal Error`, `Judge System Error`. | These describe the judge, not the submitter. |
| Group by `user_id` and order by `date`, for first-attempt rate and attempts to accept. | Rebuilds attempt sequences from the documented fields. |
| Store aggregates only. User IDs and source code are not stored. | Nothing here needs individual records. |

**What the statistics are for:** comparing or calibrating problem difficulty. Because these submitters are competitive programmers, they may not reflect beginners, so treat any calibration as a starting point and review it by hand. They do not feed the similar-learner retrieval, because they contain no interventions.

## Synthetic records

`python -m app.seed` creates, when `DEMO_MODE=true`:

- 2,000 synthetic intervention cases from a fixed random seed and an invented rule (`app/seed.py`), so retrieval has something to demonstrate.
- One clearly named synthetic class of 8 learners, for the teacher demo.

To run a real study, set `DEMO_MODE=false` and `RETRIEVAL_ALLOW_SYNTHETIC=false`, and use a fresh database and vector store. Retrieval then uses only `live` cases, and reports "no reliable match" until enough exist.
