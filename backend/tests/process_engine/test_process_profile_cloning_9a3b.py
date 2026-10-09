"""ADR-043 Step 9A.3b — future-only Process Profile cloning."""

from __future__ import annotations

import uuid
from copy import deepcopy

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.app.entity_profile.recruitment_profile_authoring import create_recruitment_profile
from backend.app.models.audit import ActivityLog
from backend.app.models.entity_profile import EpEntityProfileVersion
from backend.app.models.process_engine import (
    PePipelineTemplate,
    PeProcessProfile,
    PeTransitionRule,
)
from backend.app.models.funnel import Funnel, FunnelStage
from backend.app.process_engine.manifests.recruitment import recruitment_module_manifest
from backend.app.process_engine.policy_safety import classify_process_profile_references
from backend.app.process_engine.profile_cloning import (
    ProcessProfileCloneCodeConflictError,
    ProcessProfileCloneSourceNotFoundError,
    clone_process_profile,
)
from backend.app.process_engine.registry import ProcessEngineRegistry


async def _source(db, tenant_id: str) -> tuple[PeProcessProfile, list[PeTransitionRule]]:
    profile = PeProcessProfile(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        module="recruitment",
        code=f"source_{uuid.uuid4().hex[:8]}",
        registry_version="source-v1",
        name="Source policy",
        description="semantic source",
        config={"nested": {"enabled": True}},
        is_system=True,
        is_default=True,
        policy_revision=7,
        owner_company_id=str(uuid.uuid4()),
    )
    rules = [
        PeTransitionRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            module="recruitment",
            code=code,
            registry_version="source-v1",
            status="active",
            name=code,
            description="copied rule",
            config={"nested": {"value": priority}},
            is_system=True,
            process_profile_id=profile.id,
            priority=priority,
        )
        for code, priority in (("same_code_one", 10), ("same_code_two", 20))
    ]
    db.add_all([profile, *rules])
    await db.flush()
    return profile, rules


@pytest.mark.anyio
async def test_clone_creates_independent_policy_and_audit(
    db, tenant_id: str, bootstrap: dict[str, str]
) -> None:
    source, source_rules = await _source(db, tenant_id)
    source_snapshot = {
        "id": source.id,
        "revision": source.policy_revision,
        "config": deepcopy(source.config),
        "updated_at": source.updated_at,
        "rules": [(r.id, r.code, deepcopy(r.config), r.updated_at) for r in source_rules],
    }
    object_counts = {
        model: int(await db.scalar(select(func.count()).select_from(model)) or 0)
        for model in (Funnel, FunnelStage, PePipelineTemplate)
    }

    clone = await clone_process_profile(
        db,
        tenant_id=tenant_id,
        source_process_profile_id=source.id,
        new_code="future_policy",
        actor_id=bootstrap["admin_id"],
        reason="Future semantics",
        source="test",
    )

    cloned_rules = list(
        (
            await db.execute(
                select(PeTransitionRule)
                .where(PeTransitionRule.process_profile_id == clone.id)
                .order_by(PeTransitionRule.code)
            )
        ).scalars()
    )
    assert clone.id != source.id
    assert clone.code == "future_policy"
    assert clone.policy_revision == 1
    assert clone.status == "active"
    assert clone.is_default is False
    assert clone.is_system is False
    assert clone.legacy_candidate_profile_id is None
    assert clone.pipeline_template_id == source.pipeline_template_id
    assert clone.owner_company_id == source.owner_company_id
    assert clone.registry_version == source.registry_version
    assert clone.config == source.config
    assert clone.config is not source.config
    assert [r.code for r in cloned_rules] == [r.code for r in source_rules]
    assert {r.id for r in cloned_rules}.isdisjoint({r.id for r in source_rules})
    assert all(r.is_system is False for r in cloned_rules)
    assert all(r.process_profile_id == clone.id for r in cloned_rules)
    assert cloned_rules[0].config is not source_rules[0].config

    cloned_rules[0].config["nested"]["value"] = 999
    clone.config["nested"]["enabled"] = False
    assert source_rules[0].config == source_snapshot["rules"][0][2]
    assert source.config == source_snapshot["config"]
    assert source.policy_revision == source_snapshot["revision"]
    assert source.updated_at == source_snapshot["updated_at"]
    assert [(r.id, r.code, r.updated_at) for r in source_rules] == [
        (row[0], row[1], row[3]) for row in source_snapshot["rules"]
    ]
    for model, count in object_counts.items():
        assert int(await db.scalar(select(func.count()).select_from(model)) or 0) == count

    audit = await db.scalar(
        select(ActivityLog).where(
            ActivityLog.action == "process_profile.cloned",
            ActivityLog.target_id == clone.id,
        )
    )
    assert audit is not None
    assert audit.actor_id == bootstrap["admin_id"]
    assert audit.payload["reason"] == "Future semantics"
    assert audit.payload["source_process_profile_id"] == source.id
    assert audit.payload["source_policy_revision"] == 7
    assert len(audit.payload["transition_rule_id_mapping"]) == 2


@pytest.mark.anyio
async def test_clone_is_tenant_scoped_unique_and_atomic(
    db, tenant_id: str, bootstrap: dict[str, str], monkeypatch
) -> None:
    source, _ = await _source(db, tenant_id)
    kwargs = dict(
        tenant_id=tenant_id,
        source_process_profile_id=source.id,
        new_code="future_unique",
        actor_id=bootstrap["admin_id"],
        reason="Future semantics",
    )
    await clone_process_profile(db, **kwargs)
    with pytest.raises(ProcessProfileCloneCodeConflictError):
        await clone_process_profile(db, **kwargs)
    with pytest.raises(ProcessProfileCloneSourceNotFoundError):
        await clone_process_profile(
            db,
            **{**kwargs, "tenant_id": str(uuid.uuid4()), "new_code": "cross_tenant"},
        )
    assert await db.scalar(
        select(func.count()).select_from(PeProcessProfile).where(
            PeProcessProfile.tenant_id == tenant_id,
            PeProcessProfile.code == "future_unique",
        )
    ) == 1

    profile_count = int(
        await db.scalar(select(func.count()).select_from(PeProcessProfile)) or 0
    )
    rule_count = int(
        await db.scalar(select(func.count()).select_from(PeTransitionRule)) or 0
    )
    audit_count = int(await db.scalar(select(func.count()).select_from(ActivityLog)) or 0)

    async def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        "backend.app.process_engine.profile_cloning.log_activity",
        fail_audit,
    )
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await clone_process_profile(
            db,
            tenant_id=tenant_id,
            source_process_profile_id=source.id,
            new_code="rolled_back_clone",
            actor_id=bootstrap["admin_id"],
            reason="Must be atomic",
        )
    assert (
        int(await db.scalar(select(func.count()).select_from(PeProcessProfile)) or 0)
        == profile_count
    )
    assert (
        int(await db.scalar(select(func.count()).select_from(PeTransitionRule)) or 0)
        == rule_count
    )
    assert (
        int(await db.scalar(select(func.count()).select_from(ActivityLog)) or 0)
        == audit_count
    )


@pytest.mark.anyio
async def test_transition_rule_uniqueness_follows_profile_ownership(db, tenant_id: str) -> None:
    source, source_rules = await _source(db, tenant_id)
    other, other_rules = await _source(db, tenant_id)
    assert other.id != source.id
    assert {row.code for row in other_rules} == {row.code for row in source_rules}

    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            db.add(
                PeTransitionRule(
                    tenant_id=tenant_id,
                    module="recruitment",
                    code=source_rules[0].code,
                    name="Duplicate in profile",
                    config={},
                    process_profile_id=source.id,
                )
            )
            await db.flush()

    unowned_code = f"global_{uuid.uuid4().hex[:8]}"
    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            db.add_all(
                [
                    PeTransitionRule(
                        tenant_id=tenant_id,
                        module="recruitment",
                        code=unowned_code,
                        name="Global one",
                        config={},
                    ),
                    PeTransitionRule(
                        tenant_id=tenant_id,
                        module="recruitment",
                        code=unowned_code,
                        name="Global duplicate",
                        config={},
                    ),
                ]
            )
            await db.flush()


@pytest.mark.anyio
async def test_clone_registry_and_recruitment_versions_remain_independent(
    db, tenant_id: str, bootstrap: dict[str, str]
) -> None:
    manifest = recruitment_module_manifest()
    await ProcessEngineRegistry.register_module(db, manifest, tenant_id=tenant_id)
    source = await db.scalar(
        select(PeProcessProfile).where(
            PeProcessProfile.tenant_id == tenant_id,
            PeProcessProfile.code == "recruitment_default",
        )
    )
    assert source is not None
    v1 = await create_recruitment_profile(
        db, tenant_id=tenant_id, name="Profile v1", process_profile_id=source.id
    )
    clone = await clone_process_profile(
        db,
        tenant_id=tenant_id,
        source_process_profile_id=source.id,
        new_code="recruitment_future",
        actor_id=bootstrap["admin_id"],
        reason="Next hiring policy",
    )
    v2 = await create_recruitment_profile(
        db, tenant_id=tenant_id, name="Profile v2", process_profile_id=clone.id
    )

    assert isinstance(v1, EpEntityProfileVersion)
    assert isinstance(v2, EpEntityProfileVersion)
    assert v1.process_profile_id == source.id
    assert v2.process_profile_id == clone.id
    usage = await classify_process_profile_references(
        db, tenant_id=tenant_id, process_profile_id=clone.id
    )
    assert usage.operationally_protected is True

    clone_rule = await db.scalar(
        select(PeTransitionRule).where(PeTransitionRule.process_profile_id == clone.id)
    )
    assert clone_rule is not None
    clone_config = deepcopy(clone_rule.config)
    await ProcessEngineRegistry.register_module(db, manifest, tenant_id=tenant_id)
    await db.refresh(clone)
    await db.refresh(clone_rule)
    assert clone.is_system is False
    assert clone.code == "recruitment_future"
    assert clone_rule.is_system is False
    assert clone_rule.config == clone_config
