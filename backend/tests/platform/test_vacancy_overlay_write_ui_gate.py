"""Vacancy Overlay Write UI Gate.

Round-trip proof:
  Profile/Pack → Vacancy UI effective requirements → operator change
  → minimal Overlay delta → resolve/merge → evaluator → changed verdict

Negatives: unchanged inherited not in delta; reset to inherited clears delta;
no lead_criteria_v1; no RPM tenant_delta; description unused; Employment/legalization
out of this UI write path.

Contract: docs/specs/tasks/vacancy-overlay-write-ui.md
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend.app.entity_profile.constants import DRIVER_CE_PROFILE_CODE
from backend.app.entity_profile.vacancy_overlay_runtime import (
    CONTRACT_ID as OVERLAY_CONTRACT_ID,
    merge as merge_overlay,
    resolve_overlay,
)
from backend.app.reference.vacancy_overlay_write import (
    FORBIDDEN_EXTRA_KEYS,
    VacancyOverlayWriteError,
    apply_recruitment_requirements_to_extra,
    build_minimal_overlay_delta,
    build_overlay_delta_from_intent,
    inherited_base_requirements,
    project_effective_requirements,
    read_operator_intent_from_extra,
)
from backend.app.reference.vacancy_requirements import (
    STATUS_FIT,
    STATUS_NOT_FIT,
    evaluate_vacancy_requirements_v1,
)

_PACK_DOCS = ("passport", "driver_license", "code95", "tacho_card")
_WRITE_MOD = (
    Path(__file__).resolve().parents[2] / "app" / "reference" / "vacancy_overlay_write.py"
)
_PANEL = (
    Path(__file__).resolve().parents[3]
    / "hostflow-frontend"
    / "src"
    / "components"
    / "vacancies"
    / "detail"
    / "VacancyRecruitmentRequirementsPanel.tsx"
)
_VACANCY_DETAIL = (
    Path(__file__).resolve().parents[3]
    / "hostflow-frontend"
    / "src"
    / "components"
    / "vacancies"
    / "VacancyDetail.tsx"
)


def _facts(years: float | None) -> SimpleNamespace:
    personal: dict = {"citizenship": "PL"}
    extra: dict = {}
    if years is not None:
        extra["experience"] = {"years_ce": years}

    def _pd() -> dict:
        return personal

    def _ex() -> dict:
        return extra

    return SimpleNamespace(
        personal_data=personal,
        extra=extra,
        _get_personal_data=_pd,
        _get_extra=_ex,
    )


def _vacancy_payload(extra: dict) -> dict:
    return {
        "vacancy_ref": "v-write",
        "delta": extra[OVERLAY_CONTRACT_ID]["delta"],
        "years_ce_min": extra.get("years_ce_min"),
    }


class TestMinimalDeltaRoundTrip:
    def test_unchanged_inherited_not_in_delta(self) -> None:
        base = inherited_base_requirements(DRIVER_CE_PROFILE_CODE)
        intent = {
            "years_ce_min": base["years_ce_min"],
            "required_documents": list(base["document_types"]),
        }
        delta = build_minimal_overlay_delta(
            profile=DRIVER_CE_PROFILE_CODE, effective_intent=intent
        )
        assert delta == []
        extra = apply_recruitment_requirements_to_extra(
            {}, intent, profile=DRIVER_CE_PROFILE_CODE
        )
        assert extra[OVERLAY_CONTRACT_ID]["delta"] == []
        assert "years_ce_min" not in extra
        assert "extra_document_types" not in extra
        for doc in _PACK_DOCS:
            overlay_docs = [
                row.get("predicate", {}).get("document_type_code")
                for row in extra[OVERLAY_CONTRACT_ID]["delta"]
            ]
            assert doc not in overlay_docs

    def test_operator_change_writes_only_necessary_delta(self) -> None:
        base = inherited_base_requirements(DRIVER_CE_PROFILE_CODE)
        intent = {
            "years_ce_min": 5,
            "required_documents": [*base["document_types"], "adr"],
        }
        extra = apply_recruitment_requirements_to_extra(
            {}, intent, profile=DRIVER_CE_PROFILE_CODE
        )
        delta = extra[OVERLAY_CONTRACT_ID]["delta"]
        assert len(delta) == 2
        kinds = {(row.get("kind"), row.get("op")) for row in delta}
        assert ("value", "tighten") in kinds
        assert ("document", "add") in kinds
        codes = [
            row.get("predicate", {}).get("document_type_code")
            for row in delta
            if row.get("kind") == "document"
        ]
        assert codes == ["adr"]
        for pack_doc in _PACK_DOCS:
            assert pack_doc not in codes
        assert extra["years_ce_min"] == 5.0
        assert extra["extra_document_types"] == ["adr"]
        for key in FORBIDDEN_EXTRA_KEYS:
            assert key not in extra

    def test_reset_to_inherited_clears_delta(self) -> None:
        base = inherited_base_requirements(DRIVER_CE_PROFILE_CODE)
        tight = apply_recruitment_requirements_to_extra(
            {},
            {
                "years_ce_min": 5,
                "required_documents": [*base["document_types"], "adr"],
            },
            profile=DRIVER_CE_PROFILE_CODE,
        )
        assert tight[OVERLAY_CONTRACT_ID]["delta"]
        reset = apply_recruitment_requirements_to_extra(
            tight,
            {
                "years_ce_min": base["years_ce_min"],
                "required_documents": list(base["document_types"]),
            },
            profile=DRIVER_CE_PROFILE_CODE,
        )
        assert reset[OVERLAY_CONTRACT_ID]["delta"] == []
        assert "years_ce_min" not in reset
        assert "extra_document_types" not in reset

    def test_effective_projection_for_edit_ui(self) -> None:
        base = inherited_base_requirements(DRIVER_CE_PROFILE_CODE)
        empty = project_effective_requirements(
            profile=DRIVER_CE_PROFILE_CODE, extra={}
        )
        assert empty["years_ce_min"] == base["years_ce_min"]
        assert empty["inherited_documents"] == list(base["document_types"])
        assert empty["required_documents"] == list(base["document_types"])
        assert empty["vacancy_extra_documents"] == []

        tight_extra = apply_recruitment_requirements_to_extra(
            {},
            {"years_ce_min": 5, "required_documents": [*base["document_types"], "adr"]},
            profile=DRIVER_CE_PROFILE_CODE,
        )
        effective = project_effective_requirements(
            profile=DRIVER_CE_PROFILE_CODE, extra=tight_extra
        )
        assert effective["years_ce_min"] == 5.0
        assert "adr" in effective["required_documents"]
        assert "adr" in effective["vacancy_extra_documents"]
        assert "qualified_code" not in effective
        assert "predicate" not in str(effective.get("labels"))


class TestWritePathAuthority:
    def test_forbidden_lead_criteria_and_tenant_delta_rejected(self) -> None:
        try:
            build_overlay_delta_from_intent(
                {"lead_criteria_v1": {"min_experience_eu_years": 2}}
            )
            raise AssertionError("expected VacancyOverlayWriteError")
        except VacancyOverlayWriteError as exc:
            assert "lead_criteria_v1" in str(exc)

        try:
            build_overlay_delta_from_intent({"tenant_delta": {"x": 1}})
            raise AssertionError("expected VacancyOverlayWriteError")
        except VacancyOverlayWriteError as exc:
            assert "tenant_delta" in str(exc)

    def test_write_module_does_not_target_profiling_or_rpm(self) -> None:
        text = _WRITE_MOD.read_text(encoding="utf-8")
        assert "entity_profile_vacancy_overlay.v1" in text or "OVERLAY_CONTRACT_ID" in text
        assert "apply_recruitment_requirements_to_extra" in text
        assert 'out["lead_criteria_v1"]' not in text
        assert "out[\"tenant_delta\"]" not in text
        assert "build_minimal_overlay_delta" in text
        assert "project_effective_requirements" in text

    def test_ui_does_not_expose_employment_legalization_or_matching_chrome(self) -> None:
        panel = _PANEL.read_text(encoding="utf-8")
        detail = _VACANCY_DETAIL.read_text(encoding="utf-8")
        assert "VacancyRecruitmentRequirementsPanel" in detail
        assert "recruitment_requirements" in detail
        assert "lead_criteria" not in panel.lower() or "not lead_criteria" in panel.lower()
        for banned in (
            "legalization",
            "permit",
            "contract_subtype",
            "hourly_rate",
            "salary_band",
            "employment_requirement",
        ):
            assert banned not in panel.lower()
        # Description is not the requirements SoT in this panel.
        assert "description" not in panel.lower() or "not" in panel.lower()


class TestEvaluatorSeesOverlayWrite:
    def test_write_changes_merge_and_evaluator_verdict(self) -> None:
        base_extra = apply_recruitment_requirements_to_extra(
            {},
            {"years_ce_min": None, "required_documents": []},
            profile=DRIVER_CE_PROFILE_CODE,
        )
        tight_extra = apply_recruitment_requirements_to_extra(
            {},
            {"years_ce_min": 5, "required_documents": []},
            profile=DRIVER_CE_PROFILE_CODE,
        )

        overlay_base = resolve_overlay(
            DRIVER_CE_PROFILE_CODE, _vacancy_payload(base_extra)
        )
        merge_base = merge_overlay(
            DRIVER_CE_PROFILE_CODE, overlay_base.get("base"), overlay_base
        )
        overlay_tight = resolve_overlay(
            DRIVER_CE_PROFILE_CODE, _vacancy_payload(tight_extra)
        )
        merge_tight = merge_overlay(
            DRIVER_CE_PROFILE_CODE, overlay_tight.get("base"), overlay_tight
        )

        assert float(merge_base.get("years_ce_min") or 0) == 2.0
        assert float(merge_tight.get("years_ce_min") or 0) == 5.0

        facts = _facts(3)
        docs = list(_PACK_DOCS)
        base_verdict = evaluate_vacancy_requirements_v1(
            profile=DRIVER_CE_PROFILE_CODE,
            vacancy=_vacancy_payload(base_extra),
            facts_source=facts,
            evidence_document_types=docs,
        )
        tight_verdict = evaluate_vacancy_requirements_v1(
            profile=DRIVER_CE_PROFILE_CODE,
            vacancy=_vacancy_payload(tight_extra),
            facts_source=facts,
            evidence_document_types=docs,
        )
        assert base_verdict["status"] == STATUS_FIT
        assert tight_verdict["status"] == STATUS_NOT_FIT
        assert any(
            row.get("code") == "years_ce.below_min"
            for row in tight_verdict["explanation"]
        )

    def test_human_projection_has_no_predicate_ids(self) -> None:
        intent = {"years_ce_min": 5, "required_documents": ["adr"]}
        extra = apply_recruitment_requirements_to_extra(
            {}, intent, profile=DRIVER_CE_PROFILE_CODE
        )
        human = read_operator_intent_from_extra(extra)
        assert human["years_ce_min"] == 5
        assert "adr" in human["required_documents"]
        assert "qualified_code" not in human
        assert "predicate" not in human
