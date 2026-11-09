"""Import aggregate statistics from IBM Project CodeNet metadata files. See data/README.md.

Reads the documented CSV columns only. Stores per-problem aggregates, and never user IDs or code.
These statistics describe competitive programmers' submissions. They contain no tutoring data,
so they are not used as evidence about interventions.
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

JUDGE_ONLY_STATUSES = {"Judge Not Available", "Waiting for Judging", "Waiting for Re-judging", "Internal Error", "Judge System Error"}
ACCEPTED = "Accepted"
PROVENANCE = "Aggregated from IBM Project CodeNet metadata. Describes competitive programming submissions, not tutoring."
REQUIRED_COLUMNS = {"submission_id", "problem_id", "user_id", "date", "language", "status"}


@dataclass
class ProblemStats:
    problem_id: str
    language: str
    name: str | None = None
    rating: float | None = None
    submissions: int = 0
    learners: int = 0
    acceptance_rate: float = 0.0
    first_attempt_acceptance: float | None = None
    mean_attempts_to_accept: float | None = None
    status_counts: dict[str, int] = field(default_factory=dict)


def read_problem_list(metadata_dir: Path) -> dict[str, dict[str, str]]:
    path = metadata_dir / "problem_list.csv"
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["id"]: row for row in csv.DictReader(handle) if row.get("id")}


def _sort_key(row: dict[str, str]) -> tuple[float, str]:
    try:
        return (float(row.get("date") or 0), row.get("submission_id") or "")
    except ValueError:
        return (0.0, row.get("submission_id") or "")


def summarise(rows: Iterable[dict[str, str]], problem_id: str, language: str, info: dict[str, str] | None = None) -> ProblemStats | None:
    kept = [r for r in rows if r.get("language") == language and r.get("status") not in JUDGE_ONLY_STATUSES]
    if not kept:
        return None
    by_user: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in kept:
        by_user[row["user_id"]].append(row)
    first_accepts = 0
    attempts_to_accept: list[int] = []
    for attempts in by_user.values():
        attempts.sort(key=_sort_key)
        if attempts[0]["status"] == ACCEPTED:
            first_accepts += 1
        for index, attempt in enumerate(attempts, start=1):
            if attempt["status"] == ACCEPTED:
                attempts_to_accept.append(index)
                break
    counts = Counter(r["status"] for r in kept)
    rating = None
    if info and (info.get("rating") or "").strip():
        try:
            rating = float(info["rating"])
        except ValueError:
            rating = None
    return ProblemStats(
        problem_id=problem_id, language=language, name=(info or {}).get("name"), rating=rating, submissions=len(kept), learners=len(by_user),
        acceptance_rate=round(counts[ACCEPTED] / len(kept), 4), first_attempt_acceptance=round(first_accepts / len(by_user), 4),
        mean_attempts_to_accept=round(sum(attempts_to_accept) / len(attempts_to_accept), 3) if attempts_to_accept else None, status_counts=dict(counts),
    )


def collect(metadata_dir: Path, language: str, problems: set[str] | None = None) -> list[ProblemStats]:
    problem_list = read_problem_list(metadata_dir)
    results: list[ProblemStats] = []
    for path in sorted(metadata_dir.glob("p*.csv")):
        problem_id = path.stem
        if not re.fullmatch(r"p\d+", problem_id):
            continue  # problem_list.csv also starts with p
        if problems and problem_id not in problems:
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{path.name} is missing expected columns: {sorted(missing)}")
            stats = summarise(reader, problem_id, language, problem_list.get(problem_id))
        if stats:
            results.append(stats)
    return results


def store(stats: list[ProblemStats], dataset: str = "codenet") -> int:
    from ..db import session_scope
    from ..models import DatasetProblemStat

    with session_scope() as db:
        for item in stats:
            row = db.get(DatasetProblemStat, (dataset, item.problem_id, item.language)) or DatasetProblemStat(dataset=dataset, dataset_problem_id=item.problem_id, language=item.language)
            row.name, row.rating, row.submissions, row.learners, row.acceptance_rate = item.name, item.rating, item.submissions, item.learners, item.acceptance_rate
            row.first_attempt_acceptance, row.mean_attempts_to_accept, row.status_counts, row.provenance_note = item.first_attempt_acceptance, item.mean_attempts_to_accept, item.status_counts, PROVENANCE
            db.add(row)
    return len(stats)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-dir", required=True, type=Path)
    parser.add_argument("--language", default="Python")
    parser.add_argument("--problems", help="Comma-separated problem IDs. Default: all.")
    parser.add_argument("--dataset", default="codenet", help="Label stored with the results.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be stored, and write nothing.")
    args = parser.parse_args()
    wanted = set(args.problems.split(",")) if args.problems else None
    stats = collect(args.metadata_dir, args.language, wanted)
    for item in stats[:20]:
        print(f"{item.problem_id}: {item.submissions} submissions, {item.learners} submitters, acceptance {item.acceptance_rate:.0%}, first-attempt {item.first_attempt_acceptance:.0%}")
    if len(stats) > 20:
        print(f"... and {len(stats) - 20} more")
    if args.dry_run:
        print(f"Dry run: {len(stats)} problem(s) summarised, nothing stored.")
        return
    print(f"Stored statistics for {store(stats, args.dataset)} problem(s).")


if __name__ == "__main__":
    main()
