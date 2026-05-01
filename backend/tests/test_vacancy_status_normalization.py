"""Tests for `VacancyStatus` enum and `normalize_vacancy_status`.

Phase 2.6.D Stage A — see `docs/specs/vacancy-statuses.md`. Every entry
point that writes `Vacancy.status` (VacancyIn / VacancyPatch) and every
read path (VacancyOut) must funnel through `normalize_vacancy_status`,
so the canonical set `{open, on_hold, closed, filled, cancelled}` is the
only thing downstream code (NBA, list filters, analytics) needs to know
about.

Acceptance focus:

1. Canonical 5 values are returned unchanged.
2. `paused` (legacy alias) is normalized to `on_hold`.
3. `archived` is preserved (legacy passthrough — the service layer
   converts it to `is_archived=True`; alembic Stage B will rewrite
   stored rows).
4. Unknown values are clamped to `open` (with a logged warning).
5. None / empty / whitespace defaults to `open`.
6. The Pydantic schemas (VacancyIn / VacancyOut / VacancyPatch) apply
   the normalizer to the relevant fields.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from backend.app.api.v1.vacancies.schemas import VacancyIn, VacancyOut, VacancyPatch
from backend.app.models.vacancy import (
    VacancyStatus,
    normalize_vacancy_status,
)


# ---------------------------------------------------------------------------
# `normalize_vacancy_status` — direct unit coverage.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [member.value for member in VacancyStatus],
)
def test_canonical_values_are_returned_unchanged(value: str) -> None:
    assert normalize_vacancy_status(value) == value


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("OPEN", "open"),
        ("On_Hold", "on_hold"),
        (" closed ", "closed"),
        ("FILLED", "filled"),
        ("Cancelled", "cancelled"),
    ],
)
def test_canonical_values_are_lowercased_and_stripped(
    raw: str, expected: str
) -> None:
    assert normalize_vacancy_status(raw) == expected


def test_paused_is_aliased_to_on_hold() -> None:
    assert normalize_vacancy_status("paused") == VacancyStatus.on_hold.value


def test_paused_alias_handles_casing_and_whitespace() -> None:
    assert normalize_vacancy_status("  PAUSED ") == VacancyStatus.on_hold.value


def test_archived_is_legacy_passthrough_for_service_translation() -> None:
    """`archived` is intentionally NOT clamped — the existing
    `VacancyService.patch` logic translates `status="archived"` into
    `is_archived=True`. The Stage B alembic migration will rewrite
    stored rows so this passthrough disappears in steady state.
    """
    assert normalize_vacancy_status("archived") == "archived"


def test_unknown_value_is_clamped_to_open() -> None:
    """Unknown statuses are clamped to canonical `open`.

    We don't assert the warning log here — the project's `conftest.py`
    intercepts logging propagation in ways that make `caplog` brittle
    for nested module loggers. The clamp behaviour itself is what
    callers rely on; the warning is a diagnostic side-effect verified
    by manual log inspection.
    """
    assert normalize_vacancy_status("totally-bogus") == VacancyStatus.open.value
    assert normalize_vacancy_status("retired") == VacancyStatus.open.value
    assert normalize_vacancy_status("ARCHIVE") == VacancyStatus.open.value  # no alias defined


@pytest.mark.parametrize("raw", [None, "", "   "])
def test_empty_inputs_default_to_open(raw: str | None) -> None:
    assert normalize_vacancy_status(raw) == VacancyStatus.open.value


def test_non_string_input_is_coerced_via_str() -> None:
    """The normalizer accepts any object — defensive against legacy
    callers that pass ints or enum members directly. Output is still a
    canonical string.
    """
    assert normalize_vacancy_status(VacancyStatus.on_hold) == "on_hold"


# ---------------------------------------------------------------------------
# Pydantic integration: VacancyIn / VacancyOut / VacancyPatch normalize on
# entry. Without this layer, downstream readers would see legacy strings.
# ---------------------------------------------------------------------------


def _vacancy_in_kwargs(**overrides: object) -> dict[str, object]:
    """Minimal payload to satisfy `VacancyIn` non-status fields."""
    base: dict[str, object] = {
        "company_id": uuid4(),
        "title": "Driver",
    }
    base.update(overrides)
    return base


def test_vacancy_in_default_status_is_open() -> None:
    payload = VacancyIn(**_vacancy_in_kwargs())  # type: ignore[arg-type]
    assert payload.status == "open"


def test_vacancy_in_normalizes_paused_alias() -> None:
    payload = VacancyIn(**_vacancy_in_kwargs(status="paused"))  # type: ignore[arg-type]
    assert payload.status == "on_hold"


def test_vacancy_in_clamps_unknown_status_to_open() -> None:
    payload = VacancyIn(**_vacancy_in_kwargs(status="bogus"))  # type: ignore[arg-type]
    assert payload.status == "open"


@pytest.mark.parametrize("canonical", [m.value for m in VacancyStatus])
def test_vacancy_in_accepts_every_canonical_value(canonical: str) -> None:
    payload = VacancyIn(**_vacancy_in_kwargs(status=canonical))  # type: ignore[arg-type]
    assert payload.status == canonical


def test_vacancy_patch_normalizes_status_alt_aliases() -> None:
    """`state=paused` and `stage=paused` are documented aliases used by
    legacy clients. Both must funnel into the same canonical value the
    primary `status` field would.
    """
    via_state = VacancyPatch(state="paused")  # type: ignore[call-arg]
    via_stage = VacancyPatch(stage="paused")  # type: ignore[call-arg]
    via_status = VacancyPatch(status="paused")
    assert via_state.status_alt1 == "on_hold"
    assert via_stage.status_alt2 == "on_hold"
    assert via_status.status == "on_hold"


def test_vacancy_patch_preserves_archived_for_service_layer() -> None:
    patch = VacancyPatch(status="archived")
    assert patch.status == "archived"


def test_vacancy_out_normalizes_legacy_paused_for_clients() -> None:
    """During the rollout window (before the Stage B alembic migration
    rewrites stored rows) the database may still hold `status="paused"`.
    The output schema must mask that and emit canonical `on_hold` so
    clients never see the legacy alias.
    """
    out = VacancyOut(
        id=str(uuid4()),
        tenant_id=str(uuid4()),
        company_id=str(uuid4()),
        title="Driver",
        description=None,
        location=None,
        salary_from=None,
        salary_to=None,
        currency=None,
        status="paused",
        extra={},
        employment_type="full_time",
    )
    assert out.status == "on_hold"


def test_vacancy_out_clamps_unknown_status_for_clients() -> None:
    out = VacancyOut(
        id=str(uuid4()),
        tenant_id=str(uuid4()),
        company_id=str(uuid4()),
        title="Driver",
        description=None,
        location=None,
        salary_from=None,
        salary_to=None,
        currency=None,
        status="something-weird",
        extra={},
        employment_type="full_time",
    )
    assert out.status == "open"
