"""ADR-043 Step 9A.3a — deliberately-live Process Profile containment."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from backend.app.entity_profile.recruitment_profile_authoring import create_recruitment_profile
from backend.app.models.audit import ActivityLog
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.company import Company
from backend.app.models.entity_profile import EpEntityProfile
from backend.app.models.process_engine import PeProcessProfile, PeTransitionRule
from backend.app.models.vacancy import Vacancy
from backend.app.process_engine.manifests.recruitment import (
    recruitment_module_manifest,
)
from backend.app.process_engine.policy_safety import (
    ProcessPolicyRegistryDriftError,
    ProcessPolicyRevisionConflictError,
    ProcessProfileNotFoundError,
    classify_process_profile_references,
    correct_hiring_pipeline_gates_policy,
    update_process_profile_metadata,
)
from backend.app.process_engine.registry import ProcessEngineRegistry
from backend.app.process_engine.transition_rules_adapter import (
    default_hiring_pipeline_gates_rule_config,
    sync_tenant_hiring_gates_to_default_profile_rule,
)
from backend.app.services.hiring_pipeline_gates import merge_hiring_pipeline_gates, patch_settings_dict


async def _profile_and_rule(db, tenant_id: str) -> tuple[PeProcessProfile, PeTransitionRule]:
    profile = PeProcessProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        module="recruitment",
        code=f"policy_{uuid.uuid4().hex[:8]}",
        name="Live policy",
        config={"handoff_mode": "both"},
        is_default=False,
        is_system=False,
    )
    rule = PeTransitionRule(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        module="recruitment",
        code=f"hiring_gates_{uuid.uuid4().hex[:8]}",
        name="Hiring gates",
        process_profile_id=profile.id,
        priority=100,
        config=default_hiring_pipeline_gates_rule_config(),
    )
    db.add_all([profile, rule])
    await db.flush()
    return profile, rule


@pytest.mark.anyio
async def test_policy_revision_default_and_metadata_update(db, tenant_id: str) -> None:
    profile, _ = await _profile_and_rule(db, tenant_id)
    assert profile.policy_revision == 1

    await update_process_profile_metadata(
        db,
        tenant_id=tenant_id,
        process_profile_id=profile.id,
        changes={"name": "Corrected label", "description": "Display-only"},
    )
    assert profile.name == "Corrected label"
    assert profile.policy_revision == 1


@pytest.mark.anyio
async def test_controlled_correction_increments_and_audits(
    db, tenant_id: str, bootstrap: dict[str, str]
) -> None:
    profile, rule = await _profile_and_rule(db, tenant_id)
    gates = merge_hiring_pipeline_gates({"stages_doc_block_soft_only": ["docs_got"]})

    await correct_hiring_pipeline_gates_policy(
        db,
        tenant_id=tenant_id,
        process_profile_id=profile.id,
        expected_policy_revision=1,
        gates=gates,
        reason="Emergency correction",
        actor_id=bootstrap["admin_id"],
        source="test",
        rule_code=rule.code,
    )

    assert profile.policy_revision == 2
    assert rule.config["gates"]["stages_doc_block_soft_only"] == ["docs_got"]
    audit = await db.scalar(
        select(ActivityLog)
        .where(
            ActivityLog.tenant_id == tenant_id,
            ActivityLog.target_id == profile.id,
            ActivityLog.action == "process_profile.policy_corrected",
        )
        .order_by(ActivityLog.created_at.desc())
    )
    assert audit is not None
    assert audit.actor_id == bootstrap["admin_id"]
    assert audit.payload["reason"] == "Emergency correction"
    assert audit.payload["source"] == "test"
    assert audit.payload["previous_policy_revision"] == 1
    assert audit.payload["new_policy_revision"] == 2
    assert audit.payload["transition_rules_before"][0]["config"] != audit.payload[
        "transition_rules_after"
    ][0]["config"]


@pytest.mark.anyio
async def test_stale_and_cross_tenant_corrections_do_not_mutate(
    db, tenant_id: str, bootstrap: dict[str, str]
) -> None:
    profile, rule = await _profile_and_rule(db, tenant_id)
    original = dict(rule.config)
    gates = merge_hiring_pipeline_gates({"stages_doc_block_soft_only": ["docs_got"]})

    with pytest.raises(ProcessPolicyRevisionConflictError):
        await correct_hiring_pipeline_gates_policy(
            db,
            tenant_id=tenant_id,
            process_profile_id=profile.id,
            expected_policy_revision=99,
            gates=gates,
            reason="Stale",
            actor_id=bootstrap["admin_id"],
            source="test",
            rule_code=rule.code,
        )
    with pytest.raises(ProcessProfileNotFoundError):
        await correct_hiring_pipeline_gates_policy(
            db,
            tenant_id=str(uuid.uuid4()),
            process_profile_id=profile.id,
            expected_policy_revision=1,
            gates=gates,
            reason="Cross tenant",
            actor_id=bootstrap["admin_id"],
            source="test",
            rule_code=rule.code,
        )
    assert profile.policy_revision == 1
    assert dict(rule.config) == original


@pytest.mark.anyio
async def test_reference_classification_separates_head_from_published_version(
    db, tenant_id: str
) -> None:
    profile, _ = await _profile_and_rule(db, tenant_id)
    head = EpEntityProfile(
        tenant_id=tenant_id,
        profile_code=f"head_{uuid.uuid4().hex[:8]}",
        name="Mutable head",
        entity_type="candidate",
        module_owner="recruitment",
        process_profile_id=profile.id,
        process_profile_code=profile.code,
        config={},
    )
    db.add(head)
    await db.flush()

    usage = await classify_process_profile_references(
        db, tenant_id=tenant_id, process_profile_id=profile.id
    )
    assert usage.mutable_profile_heads == 1
    assert usage.immutable_profile_versions == 0
    assert usage.operationally_protected is False

    await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        name="Published profile",
        process_profile_id=profile.id,
    )
    usage = await classify_process_profile_references(
        db, tenant_id=tenant_id, process_profile_id=profile.id
    )
    assert usage.immutable_profile_versions == 1
    assert usage.operationally_protected is True


@pytest.mark.anyio
async def test_registry_blocks_semantic_drift_for_referenced_profile(db, tenant_id: str) -> None:
    manifest = recruitment_module_manifest()
    await ProcessEngineRegistry.register_module(db, manifest, tenant_id=tenant_id)
    profile = await db.scalar(
        select(PeProcessProfile).where(
            PeProcessProfile.tenant_id == tenant_id,
            PeProcessProfile.code == "recruitment_default",
        )
    )
    assert profile is not None
    await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        name="Protected profile",
        process_profile_id=profile.id,
    )

    changed = recruitment_module_manifest()
    changed["process_profiles"][0]["config"] = {"handoff_mode": "none"}
    with pytest.raises(ProcessPolicyRegistryDriftError, match="config"):
        await ProcessEngineRegistry.register_module(db, changed, tenant_id=tenant_id)

    await db.refresh(profile)
    assert profile.config == manifest["process_profiles"][0]["config"]


@pytest.mark.anyio
async def test_registry_blocks_rule_rewrite_for_referenced_profile(db, tenant_id: str) -> None:
    manifest = recruitment_module_manifest()
    await ProcessEngineRegistry.register_module(db, manifest, tenant_id=tenant_id)
    profile = await db.scalar(
        select(PeProcessProfile).where(
            PeProcessProfile.tenant_id == tenant_id,
            PeProcessProfile.code == "recruitment_default",
        )
    )
    assert profile is not None
    await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        name="Protected profile",
        process_profile_id=profile.id,
    )

    changed = recruitment_module_manifest()
    changed["transition_rules"][0]["priority"] = 999
    with pytest.raises(ProcessPolicyRegistryDriftError, match="priority"):
        await ProcessEngineRegistry.register_module(db, changed, tenant_id=tenant_id)


@pytest.mark.anyio
async def test_legacy_reference_is_conservatively_operational(db, tenant_id: str) -> None:
    profile, _ = await _profile_and_rule(db, tenant_id)
    legacy = CandidateProfile(
        tenant_id=tenant_id,
        code=f"legacy_{uuid.uuid4().hex[:8]}",
        name="Legacy bridge",
        config={},
        pe_process_profile_id=profile.id,
    )
    db.add(legacy)
    await db.flush()

    usage = await classify_process_profile_references(
        db, tenant_id=tenant_id, process_profile_id=profile.id
    )
    assert usage.legacy_candidate_profiles == 1
    assert usage.operationally_protected is True


@pytest.mark.anyio
async def test_vacancy_binding_is_operationally_protected(db, tenant_id: str) -> None:
    profile, _ = await _profile_and_rule(db, tenant_id)
    company = await db.scalar(select(Company).where(Company.tenant_id == tenant_id).limit(1))
    assert company is not None
    vacancy = Vacancy(
        tenant_id=tenant_id,
        company_id=company.id,
        title="Protected process binding",
        pe_process_profile_id=profile.id,
    )
    db.add(vacancy)
    await db.flush()

    usage = await classify_process_profile_references(
        db, tenant_id=tenant_id, process_profile_id=profile.id
    )
    assert usage.vacancy_runtime_bindings == 1
    assert usage.operationally_protected is True


@pytest.mark.anyio
async def test_startup_settings_sync_rejects_referenced_policy_drift(
    db, tenant_id: str
) -> None:
    manifest = recruitment_module_manifest()
    await ProcessEngineRegistry.register_module(db, manifest, tenant_id=tenant_id)
    profile = await db.scalar(
        select(PeProcessProfile).where(
            PeProcessProfile.tenant_id == tenant_id,
            PeProcessProfile.code == "recruitment_default",
        )
    )
    assert profile is not None
    await create_recruitment_profile(
        db,
        tenant_id=tenant_id,
        name="Referenced default",
        process_profile_id=profile.id,
    )

    from backend.app.models.tenant import Tenant

    tenant = await db.get(Tenant, tenant_id)
    assert tenant is not None
    tenant.settings = patch_settings_dict(
        dict(tenant.settings or {}),
        {"stages_doc_block_soft_only": ["docs_got"]},
    )
    await db.flush()

    with pytest.raises(ProcessPolicyRegistryDriftError, match="Settings"):
        await sync_tenant_hiring_gates_to_default_profile_rule(db, tenant_id=tenant_id)
