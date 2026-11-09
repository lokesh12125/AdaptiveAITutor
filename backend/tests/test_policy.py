"""DSDA as pure logic. These are the policy scenarios required by the project brief."""
import pytest

from app.tutoring.dsda import POLICY, DSDAInput, decide, need_score


def situation(**overrides) -> DSDAInput:
    base = dict(
        trigger="submission", request_size=None, category="wrong_answer", issue_key="logic:general", repeat_count=1, mastery=0.3, mastery_evidence=2.0,
        confidence=None, confusion=None, load=None, progress="unknown", attempts_on_problem=1,
    )
    base.update(overrides)
    return DSDAInput(**base)


def test_first_syntax_mistake_gets_precise_help_now():
    decision = decide(situation(category="syntax", issue_key="syntax:missing_colon"))
    assert decision.action == "give_help" and decision.timing == "show_now"
    assert decision.level == 2 and decision.strategy == "syntax_pinpoint"
    assert "SYNTAX_PRECISE" in decision.reason_codes


def test_syntax_help_never_climbs_above_its_cap():
    decision = decide(situation(category="syntax", issue_key="syntax:other", repeat_count=6, last_level_on_issue=2, hints_on_issue=4, hints_without_progress_on_issue=4, confusion="high", mastery=0.1))
    assert decision.level == POLICY["syntax_max_level"]


def test_repeated_logic_error_escalates_one_level_at_a_time():
    levels = []
    last = 0
    for attempt in range(1, 7):
        decision = decide(situation(
            issue_key="logic:off_by_one", repeat_count=attempt, attempts_on_problem=attempt, last_level_on_issue=last, hints_on_issue=attempt - 1,
            hints_without_progress_on_issue=attempt - 1, progress="stalled" if attempt > 1 else "unknown", confusion="moderate" if attempt > 1 else None, mastery=0.25,
        ))
        assert decision.action == "give_help"
        assert decision.level <= last + 1, f"jumped from {last} to {decision.level}"
        assert decision.level >= last, "support dropped while nothing improved"
        levels.append(decision.level)
        last = decision.level
    assert levels[0] <= POLICY["first_contact_max_level"]
    assert levels[-1] == 4
    assert levels == sorted(levels)


def test_new_issue_starts_small_even_with_high_need():
    decision = decide(situation(mastery=0.05, confusion="high", load="moderate", repeat_count=1))
    assert decision.level <= POLICY["first_contact_max_level"]
    assert "FIRST_CONTACT" in decision.reason_codes


def test_explicit_small_hint_from_high_mastery_learner_is_honoured():
    decision = decide(situation(trigger="hint_request", request_size="nudge", mastery=0.95, mastery_evidence=8, progress="steady"))
    assert decision.action == "give_help" and decision.timing == "show_now"
    assert 1 <= decision.level <= POLICY["small_request_max_level"]
    assert "SMALL_REQUEST" in decision.reason_codes


def test_explicit_request_always_gets_at_least_l1():
    decision = decide(situation(trigger="hint_request", mastery=1.0, mastery_evidence=20))
    assert decision.level >= 1 and decision.action == "give_help"


def test_asking_for_more_moves_up_one_rung():
    decision = decide(situation(trigger="hint_request", request_size="more", last_level_on_issue=1, hints_on_issue=1, mastery=0.9, mastery_evidence=5))
    assert decision.level == 2 and "MORE_REQUEST" in decision.reason_codes


def test_progress_after_a_hint_fades_support_and_waits():
    decision = decide(situation(progress="improving", last_level_on_issue=3, hints_on_issue=1, repeat_count=1, attempts_on_problem=3, mastery=0.5))
    assert decision.action == "offer_help"
    assert decision.timing == "offer"
    assert "PROGRESS_NO_HELP" in decision.reason_codes
    assert "FADE_PROGRESS" in decision.reason_codes


def test_requested_help_after_progress_is_lighter_than_before():
    decision = decide(situation(trigger="hint_request", progress="improving", last_level_on_issue=3, hints_on_issue=1, attempts_on_problem=3, mastery=0.5))
    assert decision.level < 3


def test_many_hints_alone_do_not_raise_assistance():
    many = situation(trigger="hint_request", hints_on_issue=6, hints_without_progress_on_issue=0, last_level_on_issue=1, progress="steady", mastery=0.8, mastery_evidence=4)
    few = situation(trigger="hint_request", hints_on_issue=1, hints_without_progress_on_issue=0, last_level_on_issue=1, progress="steady", mastery=0.8, mastery_evidence=4)
    assert need_score(many, POLICY)[0] == need_score(few, POLICY)[0]
    assert decide(many).level == decide(few).level


def test_unhelpful_hints_do_raise_assistance():
    helped = situation(hints_on_issue=2, hints_without_progress_on_issue=0, last_level_on_issue=1, mastery=0.6)
    unhelped = situation(hints_on_issue=2, hints_without_progress_on_issue=2, last_level_on_issue=1, mastery=0.6)
    assert need_score(unhelped, POLICY)[0] > need_score(helped, POLICY)[0]


def test_high_load_gives_one_concise_action():
    decision = decide(situation(load="high", trigger="hint_request", last_level_on_issue=3, hints_on_issue=3, hints_without_progress_on_issue=3, repeat_count=4, mastery=0.1))
    assert decision.presentation.one_action
    assert decision.presentation.max_sentences <= 2 and decision.presentation.max_words <= 40
    assert decision.level <= POLICY["high_load_max_level"]
    assert "HIGH_LOAD_CONCISE" in decision.reason_codes


def test_missing_history_still_produces_a_decision():
    decision = decide(situation(mastery=0.2, mastery_evidence=0, attempts_on_problem=0))
    assert decision.action in ("give_help", "offer_help")
    assert decision.level <= POLICY["first_contact_max_level"]


def test_unknown_confidence_is_left_out_not_assumed():
    _, components = need_score(situation(confidence=None), POLICY)
    assert "low_confidence" not in components
    _, known = need_score(situation(confidence=0.2), POLICY)
    assert known["low_confidence"] > 0


def test_no_retrieval_match_changes_nothing():
    without = decide(situation(retrieval=None))
    unreliable = decide(situation(retrieval={"reliable": False, "reason": "none"}))
    assert without.level == unreliable.level and not unreliable.used_retrieval


def test_reliable_retrieval_nudges_within_limits_only():
    evidence = {"reliable": True, "suggested_level": 4, "suggested_strategy": "step_outline", "support": 9, "effectiveness": 0.8, "provenance": "live"}
    decision = decide(situation(retrieval=evidence, mastery=0.5, confusion="moderate", repeat_count=1))
    assert decision.used_retrieval
    assert decision.level <= POLICY["first_contact_max_level"], "evidence cannot break the first-contact cap"
    assert "RETRIEVAL_ADJUSTED" in decision.reason_codes


def test_weak_retrieval_is_ignored():
    evidence = {"reliable": True, "suggested_level": 3, "suggested_strategy": "step_outline", "support": 1, "effectiveness": 0.9, "provenance": "live"}
    assert not decide(situation(retrieval=evidence)).used_retrieval


def test_synthetic_evidence_is_labelled():
    evidence = {"reliable": True, "suggested_level": 2, "suggested_strategy": "trace_example", "support": 9, "effectiveness": 0.8, "provenance": "synthetic"}
    decision = decide(situation(retrieval=evidence, mastery=0.4, confusion="moderate"))
    assert "RETRIEVAL_ADJUSTED_DEMO" in decision.reason_codes and "Demo records" in decision.reason_student


def test_solved_task_needs_no_help():
    decision = decide(situation(category="accepted", issue_key="accepted"))
    assert decision.action == "none" and decision.level == 0 and decision.timing == "not_needed"


def test_service_failure_never_produces_help():
    decision = decide(situation(category="service_failure", issue_key="service_failure", trigger="hint_request"))
    assert decision.action == "wait" and decision.level == 0


def test_experienced_learner_first_failure_is_offered_not_pushed():
    decision = decide(situation(mastery=0.85, mastery_evidence=4, attempts_on_problem=1))
    assert decision.action == "offer_help" and decision.timing == "offer"
    assert "OFFER_INDEPENDENT" in decision.reason_codes or "LOW_NEED" in decision.reason_codes


def test_auto_hints_preference_is_respected():
    decision = decide(situation(auto_hints=False, mastery=0.1, repeat_count=2))
    assert decision.action == "offer_help" and "AUTO_HINTS_OFF" in decision.reason_codes


def test_reason_is_simple_language_tied_to_the_issue():
    decision = decide(situation(issue_key="logic:early_return_in_loop", mastery=0.2))
    assert "before processing every value" in decision.reason_student
    assert "score" not in decision.reason_student.lower()


def test_policy_is_configurable():
    custom = {**POLICY, "policy_version": "experiment-b", "first_contact_max_level": 1}
    decision = decide(situation(mastery=0.05, confusion="high", policy=custom))
    assert decision.level == 1 and decision.policy_version == "experiment-b"


@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_presentation_limits_exist_for_every_level(level):
    assert POLICY["presentation"][str(level)]["max_words"] > 0


def test_worked_example_in_the_documentation_is_accurate():
    """docs/dsda.md shows this exact case. If the policy changes, this fails until the document is updated."""
    decision = decide(situation(
        issue_key="logic:off_by_one", repeat_count=2, attempts_on_problem=2, mastery=0.25, mastery_evidence=2.0, confusion="moderate", progress="stalled",
        last_level_on_issue=1, hints_on_issue=1, hints_without_progress_on_issue=1,
    ))
    assert decision.score == pytest.approx(0.549, abs=0.002)
    assert decision.level == 2 and decision.action == "give_help"
    assert decision.reason_student == (
        "This focuses on where your loop or range starts and stops, because answers differ by exactly one, and the same issue appeared in 2 attempts. "
        "The last hint on this issue did not lead to progress, so this one gives more support."
    )
