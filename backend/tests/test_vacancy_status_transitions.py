"""Tests for ``validate_vacancy_status_transition``.

Phase 2.6.D Stage D — see ``docs/specs/vacancy-statuses.md`` §5.3.

Coverage focus:

1. Same-status patches are no-ops (idempotent).
2. Each ``open`` → {on_hold, closed, filled, cancelled} move is allowed.
3. Each ``on_hold`` → {open, closed, cancelled} move is allowed.
4. Terminal statuses (closed, filled, cancelled) accept reopen-to-``open``
   only.
5. Disallowed moves raise ``ValueError`` (router maps to HTTP 409).
6. Legacy aliases on the input side (``paused``, casing, whitespace) are
   normalised before the matrix is consulted, so e.g. ``Paused`` →
   ``open`` behaves like ``on_hold`` → ``open`` (allowed).
7. The legacy ``archived`` alias is *not* canonicalised inside the
   validator — the service layer rewrites it to ``closed`` before this
   check runs (covered in service-level tests).
"""

from __future__ import annotations

import pytest

from backend.app.api.v1.vacancies.rules import (
    VACANCY_ALLOWED_TRANSITIONS,
    validate_vacancy_status_transition,
)
from backend.app.models.vacancy import VacancyStatus


# ---------------------------------------------------------------------------
# Same-status no-op (idempotency)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status", [s.value for s in VacancyStatus])
def test_same_status_is_idempotent_noop(status: str) -> None:
    """``X → X`` must never raise — patches that don't change the value
    must be silently absorbed so generic editors that always re-send
    every field don't trip the matrix on unrelated edits.
    """
    validate_vacancy_status_transition(status, status)


# ---------------------------------------------------------------------------
# `open` is the active hub — all moves out of it are allowed.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    [
        VacancyStatus.on_hold.value,
        VacancyStatus.closed.value,
        VacancyStatus.filled.value,
        VacancyStatus.cancelled.value,
    ],
)
def test_open_can_move_to_any_other_status(target: str) -> None:
    validate_vacancy_status_transition("open", target)


# ---------------------------------------------------------------------------
# `on_hold` — same set as open MINUS `filled` (you must reopen first to
# explicitly say "I'm hiring again" before declaring success).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "target",
    [
        VacancyStatus.open.value,
        VacancyStatus.closed.value,
        VacancyStatus.cancelled.value,
    ],
)
def test_on_hold_allowed_targets(target: str) -> None:
    validate_vacancy_status_transition("on_hold", target)


def test_on_hold_to_filled_is_blocked() -> None:
    """``on_hold → filled`` requires explicit reopen first. Hiring while
    paused is a contradiction; forcing the reopen keeps the audit trail
    truthful.
    """
    with pytest.raises(ValueError, match=r"on_hold -> filled"):
        validate_vacancy_status_transition("on_hold", "filled")


# ---------------------------------------------------------------------------
# Terminal statuses — only reopen-to-`open` is allowed.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "terminal",
    [
        VacancyStatus.closed.value,
        VacancyStatus.filled.value,
        VacancyStatus.cancelled.value,
    ],
)
def test_terminal_allows_reopen_to_open(terminal: str) -> None:
    validate_vacancy_status_transition(terminal, "open")


@pytest.mark.parametrize(
    "terminal,target",
    [
        ("closed", "on_hold"),
        ("closed", "filled"),
        ("closed", "cancelled"),
        ("filled", "on_hold"),
        ("filled", "closed"),
        ("filled", "cancelled"),
        ("cancelled", "on_hold"),
        ("cancelled", "closed"),
        ("cancelled", "filled"),
    ],
)
def test_terminal_to_non_open_is_blocked(terminal: str, target: str) -> None:
    """The matrix forces a reopen-then-target dance. Going closed → filled
    directly would lose the "we restarted hiring" event from the audit
    trail; the explicit reopen is the journal entry.
    """
    with pytest.raises(ValueError, match=rf"{terminal} -> {target}"):
        validate_vacancy_status_transition(terminal, target)


# ---------------------------------------------------------------------------
# Legacy alias normalization on the input side.
# ---------------------------------------------------------------------------


def test_legacy_paused_alias_is_normalised_before_matrix() -> None:
    """A patch coming from an old client with ``paused`` as current state
    must behave identically to ``on_hold``: ``paused → open`` is allowed.
    """
    validate_vacancy_status_transition("paused", "open")


def test_legacy_paused_alias_to_filled_is_still_blocked() -> None:
    """``paused`` normalises to ``on_hold``; the on_hold → filled block
    therefore applies through the alias too.
    """
    with pytest.raises(ValueError, match=r"on_hold -> filled"):
        validate_vacancy_status_transition("paused", "filled")


@pytest.mark.parametrize(
    "raw_cur,raw_new",
    [
        ("OPEN", "ON_HOLD"),
        ("  open  ", "Closed"),
        ("On_Hold", "  CANCELLED  "),
    ],
)
def test_casing_and_whitespace_are_normalised(raw_cur: str, raw_new: str) -> None:
    validate_vacancy_status_transition(raw_cur, raw_new)


def test_unknown_current_status_is_clamped_to_open() -> None:
    """``normalize_vacancy_status`` clamps unknown values to ``open`` (with
    a warning). The validator inherits that clamp, so ``"weird" → "closed"``
    is treated as ``open → closed`` (allowed). This is intentional: the
    validator is a *transition* gate, not a *value* gate (the value gate
    lives in the pydantic schema).
    """
    validate_vacancy_status_transition("weird-legacy-value", "closed")


def test_unknown_target_status_is_clamped_to_open() -> None:
    """Symmetric: if the writer hands us garbage, it's clamped to
    ``open``. ``closed → open`` is the canonical reopen, so allowed.
    """
    validate_vacancy_status_transition("closed", "totally-bogus")


# ---------------------------------------------------------------------------
# Matrix self-consistency
# ---------------------------------------------------------------------------


def test_matrix_covers_every_canonical_status() -> None:
    """Every canonical ``VacancyStatus`` must have an explicit row in the
    matrix. If a new status is added to the enum, this test fails until
    the matrix is updated — a built-in reminder against silent drift.
    """
    canonical = {s.value for s in VacancyStatus}
    matrix_keys = set(VACANCY_ALLOWED_TRANSITIONS.keys())
    assert canonical == matrix_keys, (
        f"VACANCY_ALLOWED_TRANSITIONS is out of sync with VacancyStatus. "
        f"Missing: {canonical - matrix_keys}, extra: {matrix_keys - canonical}"
    )


def test_matrix_targets_are_all_canonical() -> None:
    """Every transition target must itself be a canonical status. Catches
    typos / stale enum members that would silently let invalid moves
    through.
    """
    canonical = {s.value for s in VacancyStatus}
    for source, targets in VACANCY_ALLOWED_TRANSITIONS.items():
        bogus = targets - canonical
        assert not bogus, (
            f"Transition matrix contains non-canonical targets from {source}: {bogus}"
        )
