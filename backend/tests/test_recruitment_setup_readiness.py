"""Unit tests for recruitment setup readiness gates (G0–G8)."""

from __future__ import annotations

from backend.app.services.recruitment_setup_readiness import (
    SETUP_READINESS_SCOPE,
    SetupReadinessContext,
    _ActiveVacancyRow,
    _IntakeSourceRow,
    evaluate_setup_readiness_from_context,
    recruitment_activation_lock_applies,
)


def _empty_ctx(**overrides: object) -> SetupReadinessContext:
    base = SetupReadinessContext(
        tenant_active=True,
        admin_user_count=1,
        operating_company_count=1,
        business_type="agency",
        clients_count=0,
        manual_intake_declared=False,
        active_vacancies=[],
        intake_sources=[],
        meta_credentials_active=0,
        published_lead_forms=0,
        dual_routing_conflicts=[],
        legacy_meta_routes_without_binding=0,
        meta_ads_map_count=0,
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _ready_vacancy(**kwargs: object) -> _ActiveVacancyRow:
    defaults = {
        "id": "vac-1",
        "funnel_id": "fun-1",
        "funnel_stage_count": 2,
        "entity_profile_code": "recruitment.candidate.driver_ce",
        "entity_profile_active": True,
    }
    defaults.update(kwargs)
    return _ActiveVacancyRow(**defaults)  # type: ignore[arg-type]


def _ready_source(**kwargs: object) -> _IntakeSourceRow:
    defaults = {
        "profile_id": "src-1",
        "provider": "meta",
        "route_intent": "candidate_application",
        "default_assignee_id": "user-1",
        "entity_profile_code": "recruitment.candidate.driver_ce",
        "entity_profile_active": True,
        "pipeline_preset": "lead_pipeline",
        "is_active": True,
    }
    defaults.update(kwargs)
    return _IntakeSourceRow(**defaults)  # type: ignore[arg-type]


def test_empty_agency_tenant_not_ready_first_blocker_is_client() -> None:
    snapshot = evaluate_setup_readiness_from_context(_empty_ctx())
    assert snapshot.scope == SETUP_READINESS_SCOPE
    assert snapshot.ready is False
    assert snapshot.next_action is not None
    assert snapshot.next_action.gate_id == "G2"
    assert snapshot.next_action.handler_ref == "/app/setup/client"
    failed = {g.id: g.status for g in snapshot.gates if g.status == "fail"}
    assert "G2" in failed


def test_employer_skips_client_gate() -> None:
    snapshot = evaluate_setup_readiness_from_context(
        _empty_ctx(business_type="employer"),
    )
    g2 = next(g for g in snapshot.gates if g.id == "G2")
    assert g2.status == "not_applicable"
    assert snapshot.next_action is not None
    assert snapshot.next_action.gate_id == "G3"


def test_all_gates_pass_when_fully_configured() -> None:
    snapshot = evaluate_setup_readiness_from_context(
        _empty_ctx(
            clients_count=1,
            active_vacancies=[_ready_vacancy()],
            intake_sources=[_ready_source()],
            meta_credentials_active=1,
        )
    )
    assert snapshot.ready is True
    assert snapshot.blockers == []
    assert snapshot.next_action is None


def test_g0_fails_without_admin() -> None:
    snapshot = evaluate_setup_readiness_from_context(
        _empty_ctx(admin_user_count=0),
    )
    assert snapshot.ready is False
    assert snapshot.next_action is not None
    assert snapshot.next_action.gate_id == "G0"


def test_g8_fails_on_dual_routing_conflict() -> None:
    snapshot = evaluate_setup_readiness_from_context(
        _empty_ctx(
            clients_count=1,
            active_vacancies=[_ready_vacancy()],
            intake_sources=[_ready_source()],
            legacy_meta_routes_without_binding=1,
            dual_routing_conflicts=["meta_form:123:missing_intake_binding"],
        )
    )
    g8 = next(g for g in snapshot.gates if g.id == "G8")
    assert g8.status == "fail"
    assert snapshot.ready is False
    assert snapshot.next_action is not None
    assert snapshot.next_action.gate_id == "G8"
    assert snapshot.next_action.handler_ref == "/app/setup/intake"


def test_manual_intake_passes_g6_without_external_source() -> None:
    snapshot = evaluate_setup_readiness_from_context(
        _empty_ctx(
            clients_count=1,
            active_vacancies=[_ready_vacancy()],
            manual_intake_declared=True,
        )
    )
    g6 = next(g for g in snapshot.gates if g.id == "G6")
    g7 = next(g for g in snapshot.gates if g.id == "G7")
    assert g6.status == "pass"
    assert g7.status == "pass"
    assert snapshot.ready is True


def test_employer_ready_without_client_gate() -> None:
    snapshot = evaluate_setup_readiness_from_context(
        _empty_ctx(
            business_type="employer",
            active_vacancies=[_ready_vacancy()],
            manual_intake_declared=True,
        )
    )
    g2 = next(g for g in snapshot.gates if g.id == "G2")
    assert g2.status == "not_applicable"
    assert g2.applicable is False
    assert snapshot.ready is True
    assert snapshot.next_action is None


def test_employer_next_action_skips_client_to_vacancy() -> None:
    snapshot = evaluate_setup_readiness_from_context(
        _empty_ctx(business_type="employer"),
    )
    assert snapshot.next_action is not None
    assert snapshot.next_action.gate_id == "G3"
    assert snapshot.next_action.handler_ref == "/app/setup/vacancy"


def test_recruitment_activation_lock_applies_only_when_flag_set() -> None:
    assert recruitment_activation_lock_applies(None) is False
    assert recruitment_activation_lock_applies({}) is False
    assert recruitment_activation_lock_applies({"signup": {"source": "self_service"}}) is False
    assert recruitment_activation_lock_applies({"setup": {"recruitment_activation_lock": True}}) is True


def test_g6_next_action_points_to_setup_intake() -> None:
    snapshot = evaluate_setup_readiness_from_context(
        _empty_ctx(
            clients_count=1,
            active_vacancies=[_ready_vacancy()],
            manual_intake_declared=False,
        )
    )
    g6 = next(g for g in snapshot.gates if g.id == "G6")
    assert g6.status == "fail"
    assert snapshot.next_action is not None
    assert snapshot.next_action.gate_id == "G6"
    assert snapshot.next_action.handler_ref == "/app/setup/intake"
