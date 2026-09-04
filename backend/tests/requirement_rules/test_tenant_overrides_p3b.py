"""P3B — Tenant override layer tests."""

from __future__ import annotations

import pytest

from backend.app.entity_profile.manifests.recruitment import recruitment_candidate_driver_ce_profile
from backend.app.process_engine.manifests.recruitment import DEFAULT_PROFILE_CODE
from backend.app.requirement_rules.constants import (
    LEVEL_WARNING,
    OVERRIDE_KIND_ADD,
    OVERRIDE_KIND_RELAX,
    OVERRIDE_KIND_SEVERITY,
    RULE_TYPE_DOCUMENT_REQUIRED,
    RULE_TYPE_FIELD_REQUIRED,
    SOURCE_DOCUMENT_PACK,
    SOURCE_ENTITY_PROFILE,
    SOURCE_PROCESS_PROFILE,
    SOURCE_TENANT_OVERRIDE,
)
from backend.app.requirement_rules.evaluator import evaluate_requirement_rules
from backend.app.requirement_rules.registry import build_requirement_rule_set
from backend.app.requirement_rules.tenant_override_source import (
    TenantOverridePolicyError,
    apply_tenant_overrides,
    validate_tenant_override_policy,
)


def _profile_view_from_manifest() -> dict:
    manifest = recruitment_candidate_driver_ce_profile()
    return {
        "entity_profile_code": manifest["profile_code"],
        "profile_code": manifest["profile_code"],
        "profile": {
            "profile_code": manifest["profile_code"],
            "entity_type": manifest["entity_type"],
            "document_pack_code": manifest["document_pack_code"],
            "process_profile_code": manifest["process_profile_code"],
        },
        "fields": manifest["fields"],
    }


def test_p3b_document_required_relax_is_inert() -> None:
    baseline = build_requirement_rule_set(_profile_view_from_manifest(), context="readiness")
    rule_set = build_requirement_rule_set(
        _profile_view_from_manifest(),
        context="readiness",
        tenant_overrides=[
            {
                "override_kind": OVERRIDE_KIND_RELAX,
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "target_code": "code95",
                "status": "active",
            }
        ],
    )
    base_docs = {row["document_type_code"] for row in baseline["rules"] if row["rule_type"] == RULE_TYPE_DOCUMENT_REQUIRED}
    docs = {row["document_type_code"] for row in rule_set["rules"] if row["rule_type"] == RULE_TYPE_DOCUMENT_REQUIRED}
    assert docs == base_docs
    assert not any(row["source"] == SOURCE_TENANT_OVERRIDE for row in rule_set["rule_sources_applied"])


def test_p3b_document_required_add_is_inert() -> None:
    rule_set = build_requirement_rule_set(
        _profile_view_from_manifest(),
        context="readiness",
        tenant_overrides=[
            {
                "id": "ov-add-1",
                "override_kind": OVERRIDE_KIND_ADD,
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "target_code": "client_specific_doc",
                "level": "warning",
                "status": "active",
            }
        ],
    )
    doc_codes = {row["document_type_code"] for row in rule_set["rules"] if row["rule_type"] == RULE_TYPE_DOCUMENT_REQUIRED}
    assert "client_specific_doc" not in doc_codes


def test_p3b_document_required_severity_is_inert() -> None:
    baseline = build_requirement_rule_set(
        _profile_view_from_manifest(),
        context="transition",
        stage_code="ready_for_handoff",
    )
    rule_set = build_requirement_rule_set(
        _profile_view_from_manifest(),
        context="transition",
        stage_code="ready_for_handoff",
        tenant_overrides=[
            {
                "id": "ov-sev-1",
                "override_kind": OVERRIDE_KIND_SEVERITY,
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "target_code": "medical_certificate",
                "level": LEVEL_WARNING,
                "status": "active",
            }
        ],
    )
    base_codes = {row.get("document_type_code") for row in baseline["rules"]}
    over_codes = {row.get("document_type_code") for row in rule_set["rules"]}
    assert "medical_certificate" not in base_codes
    assert "medical_certificate" not in over_codes


def test_p3b_merge_order_excludes_document_required_tenant_override() -> None:
    rule_set = build_requirement_rule_set(
        _profile_view_from_manifest(),
        context="transition",
        stage_code="ready_for_handoff",
        tenant_overrides=[
            {
                "override_kind": OVERRIDE_KIND_ADD,
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "target_code": "tenant_extra_doc",
                "status": "active",
            }
        ],
    )
    sources = [row["source"] for row in rule_set["rule_sources_applied"]]
    assert sources[0] == SOURCE_ENTITY_PROFILE
    assert SOURCE_DOCUMENT_PACK in sources
    assert SOURCE_PROCESS_PROFILE in sources
    assert SOURCE_TENANT_OVERRIDE not in sources


def test_p3b_policy_rejects_canonical_field_relax() -> None:
    with pytest.raises(TenantOverridePolicyError):
        validate_tenant_override_policy(
            {
                "override_kind": OVERRIDE_KIND_RELAX,
                "rule_type": RULE_TYPE_FIELD_REQUIRED,
                "target_code": "recruitment.candidate.first_name",
            },
            canonical_field_targets={"recruitment.candidate.first_name"},
        )


def test_p3b_policy_rejects_passport_relax() -> None:
    with pytest.raises(TenantOverridePolicyError):
        validate_tenant_override_policy(
            {
                "override_kind": OVERRIDE_KIND_RELAX,
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "target_code": "passport",
            },
            canonical_field_targets=set(),
        )


def test_p3b_readiness_without_overrides_unchanged() -> None:
    baseline = build_requirement_rule_set(_profile_view_from_manifest(), context="readiness")
    assert baseline["p1_sources_only"] is True
    assert "tenant_override" in baseline["excluded_sources"]


def test_p3b_evaluator_document_required_relax_is_inert() -> None:
    baseline = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=[],
    )
    relaxed = evaluate_requirement_rules(
        _profile_view_from_manifest(),
        context="readiness",
        normalized_payload={},
        documents=[],
        tenant_overrides=[
            {
                "override_kind": OVERRIDE_KIND_RELAX,
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "target_code": "code95",
                "status": "active",
            }
        ],
    )
    baseline_missing = {row.get("document_type_code") for row in baseline["blockers"] if row.get("document_type_code")}
    relaxed_missing = {row.get("document_type_code") for row in relaxed["blockers"] if row.get("document_type_code")}
    assert relaxed_missing == baseline_missing


def test_p3b_field_required_add_still_applies() -> None:
    final, sources = apply_tenant_overrides(
        [],
        [
            {
                "override_kind": OVERRIDE_KIND_ADD,
                "rule_type": RULE_TYPE_FIELD_REQUIRED,
                "target_code": "recruitment.candidate.license_number",
                "status": "active",
            }
        ],
        canonical_field_targets=set(),
        context="readiness",
    )
    assert len(final) == 1
    assert final[0]["rule_type"] == RULE_TYPE_FIELD_REQUIRED
    assert sources


def test_p3b_stage_scoped_override_not_applied_without_stage() -> None:
    rule_set = build_requirement_rule_set(
        _profile_view_from_manifest(),
        context="readiness",
        tenant_overrides=[
            {
                "override_kind": OVERRIDE_KIND_RELAX,
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "target_code": "medical_certificate",
                "stage_code": "ready_for_handoff",
                "status": "active",
            }
        ],
    )
    # medical_certificate only exists from process profile at handoff stage
    doc_codes = {row.get("document_type_code") for row in rule_set["rules"]}
    assert "medical_certificate" not in doc_codes


def test_p3b_apply_tenant_overrides_dedup_add() -> None:
    base = [
        {
            "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
            "source": SOURCE_DOCUMENT_PACK,
            "document_type_code": "passport",
            "target": "passport",
            "level": "blocking",
        }
    ]
    final, sources = apply_tenant_overrides(
        base,
        [
            {
                "override_kind": OVERRIDE_KIND_ADD,
                "rule_type": RULE_TYPE_DOCUMENT_REQUIRED,
                "target_code": "passport",
                "status": "active",
            }
        ],
        canonical_field_targets=set(),
        context="readiness",
    )
    assert len(final) == 1
    assert final[0]["source"] == SOURCE_DOCUMENT_PACK
    assert sources == []
