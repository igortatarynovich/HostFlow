"""Tests for platform Next Action publisher (PI-1A)."""

from __future__ import annotations

from backend.app.platform.next_action.contracts import NextActionCandidate, ReachabilityContext
from backend.app.platform.next_action.publisher import NextActionPublisher
from backend.app.platform.next_action.reachability import ReachabilityEvaluator
from backend.app.platform.next_action.setup_activation_policy import (
    is_handler_allowed_during_setup_activation_lock,
    is_handler_blocked_for_guided_trial,
)
from backend.app.services.recruitment_setup_readiness import (
    SPA_CLIENTS,
    SPA_SETTINGS_FUNNELS,
    SPA_VACANCY_NEW,
    SetupReadinessContext,
    _ActiveVacancyRow,
    evaluate_setup_readiness_from_context,
)


def test_setup_activation_lock_allows_settings_funnels_path() -> None:
    assert is_handler_allowed_during_setup_activation_lock(SPA_SETTINGS_FUNNELS) is True


def test_setup_activation_lock_allows_clients_and_vacancies() -> None:
    assert is_handler_allowed_during_setup_activation_lock(SPA_CLIENTS) is True
    assert is_handler_allowed_during_setup_activation_lock(SPA_VACANCY_NEW) is True


def test_setup_activation_lock_denies_overview() -> None:
    assert is_handler_allowed_during_setup_activation_lock("/app/overview") is False


def test_guided_trial_blocks_settings_funnels() -> None:
    assert is_handler_blocked_for_guided_trial(SPA_SETTINGS_FUNNELS, tenant_status="trial") is True


def test_guided_trial_allows_billing_settings() -> None:
    assert is_handler_blocked_for_guided_trial("/app/settings/billing", tenant_status="trial") is False


def test_reachability_evaluator_blocks_trial_settings_during_setup() -> None:
    ev = ReachabilityEvaluator()
    candidate = NextActionCandidate("G4", "setup.gate.g4.funnel", SPA_SETTINGS_FUNNELS)
    ctx = ReachabilityContext(setup_ready=False, tenant_status="trial")
    result = ev.evaluate(candidate, ctx)
    assert result.reachable is False
    assert result.reason_code == "guided_trial_settings"


def test_publisher_suppresses_unreachable_g4_on_trial_tenant() -> None:
    ctx = SetupReadinessContext(
        tenant_active=True,
        admin_user_count=1,
        operating_company_count=1,
        business_type="agency",
        clients_count=1,
        manual_intake_declared=False,
        active_vacancies=[
            _ActiveVacancyRow(
                id="vac-1",
                funnel_id=None,
                funnel_stage_count=0,
                entity_profile_code=None,
                entity_profile_active=False,
            )
        ],
        intake_sources=[],
        meta_credentials_active=0,
        published_lead_forms=0,
        dual_routing_conflicts=[],
        legacy_meta_routes_without_binding=0,
        meta_ads_map_count=0,
        tenant_status="trial",
    )
    snapshot = evaluate_setup_readiness_from_context(ctx)
    assert snapshot.ready is False
    g4 = next(g for g in snapshot.gates if g.id == "G4")
    assert g4.status == "fail"
    assert snapshot.next_action is None


def test_publisher_publishes_g4_funnels_for_non_trial_tenant() -> None:
    ctx = SetupReadinessContext(
        tenant_active=True,
        admin_user_count=1,
        operating_company_count=1,
        business_type="agency",
        clients_count=1,
        manual_intake_declared=False,
        active_vacancies=[
            _ActiveVacancyRow(
                id="vac-1",
                funnel_id=None,
                funnel_stage_count=0,
                entity_profile_code=None,
                entity_profile_active=False,
            )
        ],
        intake_sources=[],
        meta_credentials_active=0,
        published_lead_forms=0,
        dual_routing_conflicts=[],
        legacy_meta_routes_without_binding=0,
        meta_ads_map_count=0,
        tenant_status="active",
    )
    snapshot = evaluate_setup_readiness_from_context(ctx)
    assert snapshot.next_action is not None
    assert snapshot.next_action.gate_id == "G4"
    assert snapshot.next_action.handler_ref == SPA_SETTINGS_FUNNELS


def test_publisher_allows_superadmin_bypass() -> None:
    pub = NextActionPublisher()
    candidate = NextActionCandidate("G4", "setup.gate.g4.funnel", SPA_SETTINGS_FUNNELS)
    ctx = ReachabilityContext(setup_ready=False, tenant_status="trial", is_superadmin=True)
    assert pub.can_publish(candidate, ctx) is True
