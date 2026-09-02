"""Recruitment inbox filter helpers — call result is activity, tabs use intake lifecycle."""

from backend.app.modules.applications.listing import (
    normalize_recruitment_call_result,
    normalize_recruitment_inbox_tab,
    normalize_recruitment_search,
)


def test_normalize_call_result_accepts_known() -> None:
    assert normalize_recruitment_call_result("no_answer") == "no_answer"
    assert normalize_recruitment_call_result("  INTERESTED ") == "interested"
    assert normalize_recruitment_call_result("") is None
    assert normalize_recruitment_call_result(None) is None


def test_normalize_call_result_rejects_unknown() -> None:
    try:
        normalize_recruitment_call_result("maybe_later")
    except ValueError as exc:
        assert "Unsupported call result" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_normalize_search_collapses_whitespace() -> None:
    assert normalize_recruitment_search("  Ada   Kowalska ") == "Ada Kowalska"
    assert normalize_recruitment_search("   ") is None


def test_normalize_tab_falls_back_to_all() -> None:
    assert normalize_recruitment_inbox_tab("new") == "new"
    assert normalize_recruitment_inbox_tab("nope") == "all"
