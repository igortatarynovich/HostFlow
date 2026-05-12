"""Pure tests for recruitment-application-lifecycle.md §3–§4 and ``set_recruitment_application_status``."""

from types import SimpleNamespace

import pytest

from backend.app.services.recruitment_application_lifecycle import (
    INITIAL_APPLICATION_STATUS,
    InvalidRecruitmentApplicationStatus,
    InvalidRecruitmentApplicationTransition,
    normalize_application_status,
    set_recruitment_application_status,
    validate_application_status_transition,
)


def test_normalize_active_to_applied() -> None:
    assert normalize_application_status("active") == "applied"
    assert normalize_application_status("ACTIVE") == "applied"


def test_transition_applied_to_in_review() -> None:
    validate_application_status_transition("applied", "in_review")


def test_transition_rejected_to_hired_forbidden() -> None:
    with pytest.raises(InvalidRecruitmentApplicationTransition):
        validate_application_status_transition("rejected", "hired")


def test_transition_archived_to_applied_forbidden() -> None:
    with pytest.raises(InvalidRecruitmentApplicationTransition):
        validate_application_status_transition("archived", "applied")


def test_transition_reopened_to_applied() -> None:
    validate_application_status_transition("reopened", "applied")


def test_noop_transition() -> None:
    validate_application_status_transition("in_review", "in_review")


def test_hire_transition_allowed_from_open_states() -> None:
    """§4 allows hired from applied / in_review / shortlist; guards (c) are service-level later."""
    validate_application_status_transition("applied", "hired")
    validate_application_status_transition("shortlisted", "hired")


@pytest.mark.parametrize(
    "from_s,to_s",
    [
        ("hired", "applied"),
        ("hired", "in_review"),
        ("hired", "shortlisted"),
        ("archived", "applied"),
        ("archived", "in_review"),
        ("archived", "hired"),
        ("rejected", "hired"),
        ("rejected", "in_review"),
        ("rejected", "applied"),
        ("withdrawn", "hired"),
        ("withdrawn", "shortlisted"),
        ("withdrawn", "applied"),
        ("applied", "reopened"),
        ("in_review", "reopened"),
        ("shortlisted", "reopened"),
    ],
)
def test_forbidden_transitions(from_s: str, to_s: str) -> None:
    with pytest.raises(InvalidRecruitmentApplicationTransition):
        validate_application_status_transition(from_s, to_s)


def test_set_status_noop_after_normalize() -> None:
    row = SimpleNamespace(status="active")
    out = set_recruitment_application_status(row, "applied")
    assert out == "applied"
    assert row.status == "applied"


def test_set_status_applied_to_in_review() -> None:
    row = SimpleNamespace(status="applied")
    assert set_recruitment_application_status(row, "in_review") == "in_review"
    assert row.status == "in_review"


def test_set_status_rejects_invalid_target() -> None:
    row = SimpleNamespace(status="applied")
    with pytest.raises(InvalidRecruitmentApplicationStatus):
        set_recruitment_application_status(row, "not_a_status")


def test_set_status_rejects_bad_transition() -> None:
    row = SimpleNamespace(status="hired")
    with pytest.raises(InvalidRecruitmentApplicationTransition):
        set_recruitment_application_status(row, "in_review")


def test_set_status_idempotent_same_canonical() -> None:
    row = SimpleNamespace(status="in_review")
    assert set_recruitment_application_status(row, "in_review") == "in_review"
    assert row.status == "in_review"


def test_ready_for_handoff_to_handed_off() -> None:
    validate_application_status_transition("ready_for_handoff", "handed_off")


def test_handed_off_to_returned_for_revision() -> None:
    validate_application_status_transition("handed_off", "returned_for_revision")


def test_returned_for_revision_to_ready_for_handoff() -> None:
    validate_application_status_transition("returned_for_revision", "ready_for_handoff")
