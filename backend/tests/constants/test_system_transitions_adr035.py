"""Unit tests for ADR-035 system transition catalog gating."""

from backend.app.constants.system_transitions import (
    CLOSE_DECLINED,
    CLOSE_SUCCESS,
    FORBIDDEN_AS_OPERATIONAL_STAGE_CODES,
    HANDOFF_TO_CLIENT,
    HANDOFF_TO_FLEET,
    HANDOFF_TO_HR,
    available_transitions,
    is_forbidden_operational_stage,
)


def test_recruitment_without_hr_hides_handoff_to_hr():
    keys = {t.key for t in available_transitions(
        source_module="recruitment",
        source_object_type="candidate",
        enabled_modules=["recruitment"],
    )}
    assert HANDOFF_TO_CLIENT in keys
    assert CLOSE_SUCCESS in keys
    assert CLOSE_DECLINED in keys
    assert HANDOFF_TO_HR not in keys
    assert HANDOFF_TO_FLEET not in keys


def test_recruitment_with_hr_offers_handoff_to_hr():
    keys = {t.key for t in available_transitions(
        source_module="recruitment",
        source_object_type="candidate",
        enabled_modules=["recruitment", "hr"],
    )}
    assert HANDOFF_TO_HR in keys
    assert HANDOFF_TO_CLIENT in keys
    assert HANDOFF_TO_FLEET not in keys


def test_hr_with_fleet_offers_handoff_to_fleet():
    keys = {t.key for t in available_transitions(
        source_module="hr",
        source_object_type="employee",
        enabled_modules=["hr", "fleet"],
    )}
    assert HANDOFF_TO_FLEET in keys
    assert HANDOFF_TO_HR not in keys


def test_forbidden_operational_stage_codes():
    assert is_forbidden_operational_stage("ready_for_hr")
    assert is_forbidden_operational_stage("processing_by_hr")
    assert is_forbidden_operational_stage("ready_for_fleet")
    assert not is_forbidden_operational_stage("accepted")
    assert "ready_for_hr" in FORBIDDEN_AS_OPERATIONAL_STAGE_CODES
