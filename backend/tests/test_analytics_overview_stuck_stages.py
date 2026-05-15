"""Overview «stuck» counters must reference only canonical candidate stage codes."""

from backend.app.constants.stages import LABELS, OVERVIEW_STUCK_AGENCY_STAGE, OVERVIEW_STUCK_EMPLOYER_STAGE_CODES


def test_overview_stuck_agency_stage_is_canonical() -> None:
    assert OVERVIEW_STUCK_AGENCY_STAGE in LABELS


def test_overview_stuck_employer_stages_are_canonical() -> None:
    assert OVERVIEW_STUCK_EMPLOYER_STAGE_CODES
    for code in OVERVIEW_STUCK_EMPLOYER_STAGE_CODES:
        assert code in LABELS, f"missing label for {code!r}"
