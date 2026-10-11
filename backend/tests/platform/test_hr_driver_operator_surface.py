"""The operator surface picks one next action and keeps every fact in view."""

from backend.app.models.hr_employment_requirement import (
    APPLICABILITY_APPLICABLE,
    APPLICABILITY_NOT_APPLICABLE,
    RESOLUTION_BLOCKING,
    RESOLUTION_SATISFIED,
    RESOLUTION_UNRESOLVED,
)
from backend.app.services.hr_driver_operator_surface import (
    SurfaceCase,
    SurfaceFact,
    choose_next_action,
    ordered_facts,
)


def _fact(key: str, resolution: str | None, applicability: str = APPLICABILITY_APPLICABLE) -> SurfaceFact:
    return SurfaceFact(
        key=key,
        label=key,
        applicability=applicability,
        resolution=resolution,
        blocking_reason="licence mismatch" if resolution == RESOLUTION_BLOCKING else None,
        evidence_linked=resolution == RESOLUTION_SATISFIED,
    )


def test_blocked_work_eligibility_does_not_drop_later_facts() -> None:
    facts = ordered_facts(
        (
            _fact("occupational_medicine", RESOLUTION_UNRESOLVED),
            _fact("passport", RESOLUTION_SATISFIED),
            _fact("code_95", None, APPLICABILITY_NOT_APPLICABLE),
        )
    )
    assert [fact.key for fact in facts] == ["passport", "code_95", "occupational_medicine"]
    action = choose_next_action(
        SurfaceCase(
            state="preparing",
            terms_complete=False,
            work_yes=False,
            legal_pass=False,
            zus_open=False,
            ready_pass=False,
            facts=facts,
        )
    )
    assert action is not None
    assert action["code"] == "confirm_terms"
    assert len(facts) == 3


def test_zus_is_the_action_when_the_permit_is_still_open() -> None:
    action = choose_next_action(
        SurfaceCase(
            state="preparing",
            terms_complete=True,
            work_yes=False,
            legal_pass=False,
            zus_open=True,
            ready_pass=False,
            facts=(_fact("code_95", RESOLUTION_UNRESOLVED),),
        )
    )
    assert action is not None
    assert action["code"] == "register_zus"
    assert action["title"] == "Register in ZUS"


def test_blocking_fact_outranks_a_later_start() -> None:
    action = choose_next_action(
        SurfaceCase(
            state="preparing",
            terms_complete=True,
            work_yes=True,
            legal_pass=True,
            zus_open=False,
            ready_pass=True,
            facts=(_fact("code_95", RESOLUTION_BLOCKING),),
        )
    )
    assert action is not None
    assert action["code"] == "resolve_requirement"
    assert action["fact_key"] == "code_95"


def test_current_ready_pass_is_start_employment() -> None:
    action = choose_next_action(
        SurfaceCase(
            state="preparing",
            terms_complete=True,
            work_yes=True,
            legal_pass=True,
            zus_open=False,
            ready_pass=True,
            facts=(_fact("passport", RESOLUTION_SATISFIED),),
        )
    )
    assert action is not None
    assert action["code"] == "start_employment"


def test_live_readings_without_a_current_pass_do_not_start() -> None:
    action = choose_next_action(
        SurfaceCase(
            state="preparing",
            terms_complete=True,
            work_yes=True,
            legal_pass=True,
            zus_open=False,
            ready_pass=False,
            facts=(_fact("passport", RESOLUTION_SATISFIED),),
            live_ready=True,
        )
    )
    assert action is not None
    assert action["code"] == "record_ready"
