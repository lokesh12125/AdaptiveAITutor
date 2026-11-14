"""What has already happened between this learner and this problem, read fresh from the database.

Every agent reads this rather than trusting the current request alone. Graph state only carries the
current cycle; anything earlier comes from here. History restarts after the problem is solved, so
reopening a solved problem does not inherit old hints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import CodeSnapshot, Draft, Evaluation, Hint, InteractionRecord, Reflection


@dataclass
class HintView:
    id: str
    text: str
    level: int
    strategy: str
    issue_key: str
    category: str
    snapshot_id: str
    outcome: str | None
    helpful: bool | None
    requested: bool
    source: str
    created_at: datetime


@dataclass
class RecordView:
    snapshot_id: str
    trigger: str
    evaluation_kind: str | None
    verdict: str | None
    category: str
    issue_key: str
    tests_passed: int
    tests_total: int
    code_changed: bool
    created_at: datetime


@dataclass
class InteractionHistory:
    hints: list[HintView] = field(default_factory=list)
    records: list[RecordView] = field(default_factory=list)
    reflection_prompts: list[str] = field(default_factory=list)
    reflection_answers: list[str] = field(default_factory=list)
    reflection_unsure_since_last_cycle: bool = False  # the learner's latest reflection answer said they were unsure
    last_solved_at: datetime | None = None
    last_action_at: datetime | None = None
    previous_code: str | None = None
    previous_snapshot_id: str | None = None

    def hints_on_issue(self, issue_key: str) -> list[HintView]:
        return [h for h in self.hints if h.issue_key == issue_key]

    def same_code_hints(self, issue_key: str, snapshot_id: str) -> list[HintView]:
        return [h for h in self.hints if h.issue_key == issue_key and h.snapshot_id == snapshot_id]

    def previous_record(self, snapshot_id: str) -> RecordView | None:
        """The most recent cycle on a different version of the code."""
        return next((r for r in reversed(self.records) if r.snapshot_id != snapshot_id), None)

    def previous_record_of_kind(self, snapshot_id: str, kind: str | None) -> RecordView | None:
        """As above, measured the same way. Visible examples and full tests are different scales."""
        return next((r for r in reversed(self.records) if r.snapshot_id != snapshot_id and r.evaluation_kind == kind), None)

    def seconds_since_last_hint(self, now: datetime | None = None) -> float | None:
        if not self.hints:
            return None
        return ((now or datetime.now(UTC)) - self.hints[-1].created_at).total_seconds()

    def seconds_since_last_action(self, now: datetime | None = None) -> float | None:
        if self.last_action_at is None:
            return None
        return max(0.0, ((now or datetime.now(UTC)) - self.last_action_at).total_seconds())

    def summary(self) -> dict[str, Any]:
        """A compact description for traces. Contains no code or hint text."""
        return {
            "hints": len(self.hints), "records": len(self.records), "reflection_answers": len(self.reflection_answers),
            "has_previous_code": self.previous_code is not None, "last_solved": self.last_solved_at is not None,
        }


def load_history(db: Session, user_id: str, problem_id: str, snapshot_id: str, evaluation_id: str | None = None) -> InteractionHistory:
    last_solved_at = db.scalar(
        select(func.max(Evaluation.created_at)).where(
            Evaluation.user_id == user_id, Evaluation.problem_id == problem_id, Evaluation.kind == "submit", Evaluation.verdict == "accepted",
            Evaluation.id != (evaluation_id or ""),
        )
    )

    hint_query = select(Hint).where(Hint.user_id == user_id, Hint.problem_id == problem_id, Hint.delivery == "shown").order_by(Hint.created_at)
    record_query = select(InteractionRecord).where(InteractionRecord.user_id == user_id, InteractionRecord.problem_id == problem_id).order_by(InteractionRecord.created_at)
    if last_solved_at is not None:
        hint_query = hint_query.where(Hint.created_at > last_solved_at)
        record_query = record_query.where(InteractionRecord.created_at > last_solved_at)
    hints = [
        HintView(h.id, h.text, h.level, h.strategy, h.issue_key, h.category, h.snapshot_id, h.outcome, h.helpful, h.requested, h.source, h.created_at)
        for h in db.scalars(hint_query).all()
    ]
    records = [
        RecordView(r.snapshot_id, r.trigger, r.evaluation_kind, r.verdict, r.category, r.issue_key, r.tests_passed, r.tests_total, r.code_changed, r.created_at)
        for r in db.scalars(record_query).all()
    ]

    reflections = db.scalars(select(Reflection).where(Reflection.user_id == user_id, Reflection.problem_id == problem_id).order_by(Reflection.created_at)).all()

    # The last time the learner did something that could change the picture: edited, ran or asked with new code.
    candidates: list[datetime] = []
    draft = db.get(Draft, (user_id, problem_id, "python"))
    if draft is not None:
        candidates.append(draft.updated_at)
    last_run = db.scalar(select(func.max(Evaluation.created_at)).where(Evaluation.user_id == user_id, Evaluation.problem_id == problem_id, Evaluation.kind == "run"))
    if last_run is not None:
        candidates.append(last_run)
    changed = [r.created_at for r in records if r.code_changed]
    if changed:
        candidates.append(changed[-1])

    previous = next((r for r in reversed(records) if r.snapshot_id != snapshot_id), None)
    previous_code = None
    if previous is not None:
        row = db.get(CodeSnapshot, previous.snapshot_id)
        previous_code = row.code if row else None

    return InteractionHistory(
        hints=hints, records=records, reflection_prompts=[r.prompt for r in reflections], reflection_answers=[r.answer for r in reflections if r.answer],
        reflection_unsure_since_last_cycle=_unsure_since(reflections, records),
        last_solved_at=last_solved_at, last_action_at=max(candidates) if candidates else None, previous_code=previous_code,
        previous_snapshot_id=previous.snapshot_id if previous else None,
    )


def _unsure_since(reflections: list[Reflection], records: list[RecordView]) -> bool:
    """An answer saying "I don't know", given after the last tutoring cycle, is one sign of confusion for the next."""
    answered = [r for r in reflections if r.answered_at is not None]
    if not answered or answered[-1].quality != "unsure":
        return False
    return not records or answered[-1].answered_at >= records[-1].created_at
