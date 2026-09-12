"""Intake Readiness Gate — Meta-like inbound → actionable Application (Fits)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend.app.acquisition.submission_routing import UnresolvedReason
from backend.app.modules.leads.conversion_mapping import apply_executable_intake_mapping
from backend.app.modules.leads.normalizer import normalize_meta_payload
from backend.app.reference.intake_readiness import (
    ARCH_REL,
    FITS_NEXT_ACTION,
    POLICY_ID,
    RSO_BRIEF_REL,
    WALK_API,
    intake_auto_convert_gated_is_actionable,
    recruitment_next_action_after_intake,
)
from backend.app.security.api_tenant_context import require_elevated_reason_or_raise
from backend.app.services.lead_rodo import lead_rodo_required_block_code
from backend.app.services.lead_rodo_obligation import notice_provided_at_source

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARCH = _REPO_ROOT / ARCH_REL
_RSO = _REPO_ROOT / RSO_BRIEF_REL
_CI = _REPO_ROOT / ".github" / "workflows" / "backend-ci.yml"
_MODULE = _REPO_ROOT / "backend" / "app" / "reference" / "intake_readiness.py"
_DEP = _REPO_ROOT / "backend" / "app" / "db" / "meta_leads_tenant_dep.py"
_ROUTE = _REPO_ROOT / "backend" / "app" / "modules" / "leads" / "intake_route.py"
_PROCESSING = (
    _REPO_ROOT / "backend" / "app" / "modules" / "leads" / "service" / "_processing.py"
)


def _meta_payload(*, citizenship: str = "PL", gdpr: str = "yes") -> dict:
    return {
        "entry": [
            {
                "id": "259905353877064",
                "changes": [
                    {
                        "field": "leadgen",
                        "value": {
                            "leadgen_id": "lg-intake-readiness",
                            "ad_id": "120250095717250547",
                            "form_id": "1987162785236755",
                            "page_id": "259905353877064",
                            "field_data": [
                                {"name": "full_name", "values": ["Jan Nowak"]},
                                {"name": "email", "values": ["jan.nowak@inbox.test"]},
                                {"name": "phone_number", "values": ["+48511000001"]},
                                {"name": "citizenship", "values": [citizenship]},
                                {"name": "gdpr_consent", "values": [gdpr]},
                                {
                                    "name": "какой у вас опыт работы водителем c+e в международных перевозках по ес?",
                                    "values": ["1–2_года"],
                                },
                                {"name": "jaka_masz_kategorie", "values": ["C+E"]},
                                {
                                    "name": "vacancy_id",
                                    "values": ["048408be-fcde-4890-af81-37bb44c523b5"],
                                },
                            ],
                        },
                    }
                ],
            }
        ]
    }


def test_intake_readiness_gate_filename() -> None:
    assert Path(__file__).name == "test_intake_readiness_gate.py"


def test_intake_readiness_policy_and_walk_api() -> None:
    assert POLICY_ID == "intake_readiness.v1"
    assert WALK_API == "recruitment_next_action_after_intake"
    assert "def recruitment_next_action_after_intake(" in _MODULE.read_text(encoding="utf-8")


def test_intake_readiness_sot_locks() -> None:
    text = _ARCH.read_text(encoding="utf-8")
    assert "Consent/RODO validity is not SMTP delivery" in text
    assert "campaign-flight STOP" in text
    assert "canonical facts" in text
    assert "require_elevated_reason_or_raise" in text
    assert "auto_convert_gated" in text
    assert "next_action` is `fits`" in text or "next_action = fits" in text


def test_consent_in_payload_is_notice_at_source_not_smtp() -> None:
    normalized = normalize_meta_payload(_meta_payload())
    assert notice_provided_at_source(normalized) is True
    assert normalized.get("rodo_notice_at_source") is True
    lead = SimpleNamespace(
        candidate_id=None,
        normalized={
            **normalized,
            "rodo": {"status": "failed", "compliance_state": "delivery_failed"},
        },
    )
    assert lead_rodo_required_block_code(lead, "process") is None


def test_citizenship_field_becomes_canonical_fact() -> None:
    normalized = normalize_meta_payload(_meta_payload(citizenship="PL"))
    assert str(normalized.get("citizenship") or "").upper() == "PL"
    writes = apply_executable_intake_mapping(normalized)
    # Canonical occupancy: personal_data.citizenship only (not extra).
    assert str(writes.personal.get("citizenship") or "").upper() == "PL"
    assert "citizenship" not in writes.extra


def test_experience_and_category_become_canonical_facts() -> None:
    normalized = normalize_meta_payload(_meta_payload())
    assert normalized.get("experience_eu_years") == 1
    assert str(normalized.get("driving_license_category") or "") == "C+E"
    writes = apply_executable_intake_mapping(normalized)
    # Canonical occupancy: extra.experience.years_ce (not flat experience_eu_years).
    assert writes.extra.get("experience", {}).get("years_ce") == 1
    assert "experience_eu_years" not in writes.extra
    assert writes.extra.get("driving_license_category") == "C+E"


def test_mapping_elevated_reason_is_keyword_only() -> None:
    dep = _DEP.read_text(encoding="utf-8")
    assert "require_elevated_reason_or_raise(" in dep
    assert "reason=elevated_reason" in dep
    require_elevated_reason_or_raise(reason="ops remap for mapping", detail="missing")


def test_missing_campaign_flight_does_not_force_intake_failed() -> None:
    route = _ROUTE.read_text(encoding="utf-8")
    assert "missing_campaign_flight" in route
    assert "force_failed=False" in route or "force_failed = False" in route
    assert UnresolvedReason.missing_campaign_flight.value == "missing_campaign_flight"


def test_sufficient_facts_next_action_is_fits() -> None:
    lead = SimpleNamespace(
        status="processed",
        vacancy_id="048408be-fcde-4890-af81-37bb44c523b5",
        normalized={"full_name": "Jan Nowak", "citizenship": "PL"},
        first_name="Jan",
        last_name="Nowak",
    )
    assert recruitment_next_action_after_intake(lead) == FITS_NEXT_ACTION
    blocked = SimpleNamespace(
        status="needs_routing",
        vacancy_id=lead.vacancy_id,
        normalized=lead.normalized,
        first_name="Jan",
        last_name="Nowak",
    )
    assert recruitment_next_action_after_intake(blocked) is None


def test_auto_convert_gated_is_not_routing_stop() -> None:
    assert intake_auto_convert_gated_is_actionable(
        disposition="needs_routing",
        blocking_reasons=["auto_convert_gated"],
        vacancy_resolved=True,
        triage_gate_bypass=True,
    )
    assert not intake_auto_convert_gated_is_actionable(
        disposition="needs_routing",
        blocking_reasons=["vacancy_not_resolved"],
        vacancy_resolved=False,
        triage_gate_bypass=False,
    )
    processing = _PROCESSING.read_text(encoding="utf-8")
    assert "intake_auto_convert_gated_is_actionable" in processing
    lead = SimpleNamespace(
        status="processed",
        vacancy_id="048408be-fcde-4890-af81-37bb44c523b5",
        normalized={"full_name": "Jan Nowak"},
        first_name="Jan",
        last_name="Nowak",
    )
    assert recruitment_next_action_after_intake(lead) == FITS_NEXT_ACTION


def test_intake_readiness_briefs_and_ci() -> None:
    rso = _RSO.read_text(encoding="utf-8")
    ci = _CI.read_text(encoding="utf-8")
    assert "Intake Readiness" in rso or "intake-readiness" in rso
    assert "test_intake_readiness_gate.py" in ci
    assert "intake-readiness-gate" in ci
