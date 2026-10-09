"""ADR-043 Step 9A.3b: future-only Process Profile cloning."""

from __future__ import annotations

from copy import deepcopy
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.process_engine import (
    REGISTRY_STATUS_ACTIVE,
    PeProcessProfile,
    PeTransitionRule,
)
from backend.app.services.audit import log_activity


class ProcessProfileCloneError(ValueError):
    pass


class ProcessProfileCloneSourceNotFoundError(ProcessProfileCloneError):
    pass


class ProcessProfileCloneCodeConflictError(ProcessProfileCloneError):
    pass


async def clone_process_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    source_process_profile_id: str,
    new_code: str,
    actor_id: str,
    reason: str,
    source: str = "internal",
    ip: str | None = None,
    ua: str | None = None,
) -> PeProcessProfile:
    """Clone recruitment policy into an independent, active, non-system identity.

    The caller owns the outer transaction and commit. A savepoint ensures that a
    failed clone leaves no profile, rules, or audit row in a caller-managed
    transaction.
    """

    tenant_key = str(tenant_id or "").strip()
    code = str(new_code or "").strip()
    clean_actor = str(actor_id or "").strip()
    clean_reason = str(reason or "").strip()
    clean_source = str(source or "").strip()
    if not code:
        raise ProcessProfileCloneError("A non-empty new Process Profile code is required")
    if not clean_actor:
        raise ProcessProfileCloneError("Actor identity is required")
    if not clean_reason:
        raise ProcessProfileCloneError("A non-empty clone reason is required")
    if not clean_source:
        raise ProcessProfileCloneError("Clone source is required")

    async with db.begin_nested():
        profile = await db.scalar(
            select(PeProcessProfile)
            .where(
                PeProcessProfile.id == str(source_process_profile_id),
                PeProcessProfile.tenant_id == tenant_key,
                PeProcessProfile.module == "recruitment",
            )
            .with_for_update()
        )
        if profile is None:
            raise ProcessProfileCloneSourceNotFoundError(str(source_process_profile_id))

        conflict = await db.scalar(
            select(PeProcessProfile.id).where(
                PeProcessProfile.tenant_id == tenant_key,
                PeProcessProfile.module == profile.module,
                PeProcessProfile.code == code,
            )
        )
        if conflict is not None:
            raise ProcessProfileCloneCodeConflictError(code)

        rules = list(
            (
                await db.execute(
                    select(PeTransitionRule)
                    .where(
                        PeTransitionRule.tenant_id == tenant_key,
                        PeTransitionRule.process_profile_id == profile.id,
                    )
                    .order_by(PeTransitionRule.code.asc(), PeTransitionRule.id.asc())
                    .with_for_update()
                )
            ).scalars()
        )

        cloned = PeProcessProfile(
            id=str(uuid4()),
            tenant_id=tenant_key,
            module=profile.module,
            code=code,
            registry_version=profile.registry_version,
            status=REGISTRY_STATUS_ACTIVE,
            name=profile.name,
            description=profile.description,
            config=deepcopy(profile.config or {}),
            is_system=False,
            is_default=False,
            policy_revision=1,
            pipeline_template_id=profile.pipeline_template_id,
            owner_company_id=profile.owner_company_id,
            legacy_candidate_profile_id=None,
        )
        db.add(cloned)

        rule_id_mapping: dict[str, str] = {}
        for rule in rules:
            cloned_rule_id = str(uuid4())
            rule_id_mapping[str(rule.id)] = cloned_rule_id
            db.add(
                PeTransitionRule(
                    id=cloned_rule_id,
                    tenant_id=tenant_key,
                    module=rule.module,
                    code=rule.code,
                    registry_version=rule.registry_version,
                    status=rule.status,
                    name=rule.name,
                    description=rule.description,
                    config=deepcopy(rule.config or {}),
                    is_system=False,
                    process_profile_id=cloned.id,
                    priority=rule.priority,
                )
            )
        await db.flush()

        await log_activity(
            db,
            tenant_id=tenant_key,
            action="process_profile.cloned",
            actor_id=clean_actor,
            target_type="process_profile",
            target_id=cloned.id,
            payload={
                "reason": clean_reason,
                "source": clean_source,
                "source_process_profile_id": str(profile.id),
                "source_policy_revision": int(profile.policy_revision or 1),
                "cloned_process_profile_id": cloned.id,
                "source_code": str(profile.code),
                "new_code": cloned.code,
                "transition_rule_id_mapping": rule_id_mapping,
                "source_profile": {
                    "module": profile.module,
                    "status": profile.status,
                    "pipeline_template_id": profile.pipeline_template_id,
                    "owner_company_id": profile.owner_company_id,
                    "is_default": bool(profile.is_default),
                    "is_system": bool(profile.is_system),
                },
            },
            ip=ip,
            ua=ua,
        )
        return cloned


__all__ = [
    "ProcessProfileCloneCodeConflictError",
    "ProcessProfileCloneError",
    "ProcessProfileCloneSourceNotFoundError",
    "clone_process_profile",
]
