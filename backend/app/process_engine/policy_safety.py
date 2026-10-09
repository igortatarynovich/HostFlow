"""ADR-043 Step 9A.3a: containment for deliberately-live Process Profile policy."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.entity_profile import EpEntityProfile, EpEntityProfileVersion
from backend.app.models.process_engine import PeProcessProfile, PeTransitionRule
from backend.app.models.vacancy import Vacancy
from backend.app.services.audit import log_activity


PROFILE_METADATA_FIELDS = frozenset({"name", "description"})
PROFILE_PROTECTED_FIELDS = frozenset(
    {
        "config",
        "status",
        "is_default",
        "pipeline_template_id",
        "legacy_candidate_profile_id",
        "tenant_id",
        "module",
        "code",
        "owner_company_id",
        "registry_version",
        "is_system",
    }
)
TRANSITION_RULE_METADATA_FIELDS = frozenset({"name", "description"})
TRANSITION_RULE_PROTECTED_FIELDS = frozenset(
    {
        "config",
        "status",
        "priority",
        "process_profile_id",
        "tenant_id",
        "module",
        "code",
        "registry_version",
        "is_system",
    }
)


class ProcessPolicySafetyError(ValueError):
    pass


class ProcessProfileNotFoundError(ProcessPolicySafetyError):
    pass


class ProcessPolicyRevisionConflictError(ProcessPolicySafetyError):
    def __init__(self, *, expected_revision: int, current_revision: int) -> None:
        self.expected_revision = int(expected_revision)
        self.current_revision = int(current_revision)
        super().__init__(
            f"Process Profile policy revision conflict: expected {self.expected_revision}, "
            f"current {self.current_revision}"
        )


class ProcessPolicyRegistryDriftError(ProcessPolicySafetyError):
    pass


@dataclass(frozen=True)
class ProcessProfileReferenceUsage:
    mutable_profile_heads: int
    immutable_profile_versions: int
    vacancy_runtime_bindings: int
    legacy_candidate_profiles: int

    @property
    def operationally_protected(self) -> bool:
        # CandidateProfile is deliberately conservative during the legacy bridge:
        # any linked profile can participate after assignment to a Vacancy.
        return bool(
            self.immutable_profile_versions
            or self.vacancy_runtime_bindings
            or self.legacy_candidate_profiles
        )

    @property
    def deletion_referenced(self) -> bool:
        return bool(self.mutable_profile_heads or self.operationally_protected)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["operationally_protected"] = self.operationally_protected
        payload["deletion_referenced"] = self.deletion_referenced
        return payload


async def classify_process_profile_references(
    db: AsyncSession,
    *,
    tenant_id: str,
    process_profile_id: str,
) -> ProcessProfileReferenceUsage:
    """Return the canonical tenant-scoped external-reference classification."""

    tenant_key = str(tenant_id)
    profile_key = str(process_profile_id)

    async def count(model: Any, column: Any) -> int:
        value = await db.scalar(
            select(func.count())
            .select_from(model)
            .where(model.tenant_id == tenant_key, column == profile_key)
        )
        return int(value or 0)

    return ProcessProfileReferenceUsage(
        mutable_profile_heads=await count(EpEntityProfile, EpEntityProfile.process_profile_id),
        immutable_profile_versions=await count(
            EpEntityProfileVersion, EpEntityProfileVersion.process_profile_id
        ),
        vacancy_runtime_bindings=await count(Vacancy, Vacancy.pe_process_profile_id),
        legacy_candidate_profiles=await count(
            CandidateProfile, CandidateProfile.pe_process_profile_id
        ),
    )


def _profile_policy_snapshot(profile: PeProcessProfile) -> dict[str, Any]:
    return {
        "config": dict(profile.config or {}),
        "status": str(profile.status or ""),
        "is_default": bool(profile.is_default),
        "pipeline_template_id": profile.pipeline_template_id,
        "legacy_candidate_profile_id": profile.legacy_candidate_profile_id,
        "owner_company_id": profile.owner_company_id,
    }


def _rule_policy_snapshot(rule: PeTransitionRule) -> dict[str, Any]:
    return {
        "id": str(rule.id),
        "code": str(rule.code),
        "config": dict(rule.config or {}),
        "status": str(rule.status or ""),
        "priority": int(rule.priority),
        "process_profile_id": rule.process_profile_id,
    }


async def update_process_profile_metadata(
    db: AsyncSession,
    *,
    tenant_id: str,
    process_profile_id: str,
    changes: dict[str, Any],
) -> PeProcessProfile:
    """Update only harmless display metadata; semantic revision is unchanged."""

    unexpected = set(changes) - PROFILE_METADATA_FIELDS
    if unexpected:
        raise ProcessPolicySafetyError(
            f"Only Process Profile metadata may be updated here: {sorted(unexpected)}"
        )
    profile = await db.scalar(
        select(PeProcessProfile)
        .where(
            PeProcessProfile.id == str(process_profile_id),
            PeProcessProfile.tenant_id == str(tenant_id),
        )
        .with_for_update()
    )
    if profile is None:
        raise ProcessProfileNotFoundError(str(process_profile_id))
    for key, value in changes.items():
        setattr(profile, key, value)
    await db.flush()
    return profile


async def correct_hiring_pipeline_gates_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    process_profile_id: str,
    expected_policy_revision: int,
    gates: Any,
    reason: str,
    actor_id: str,
    source: str,
    rule_code: str,
    ip: str | None = None,
    ua: str | None = None,
) -> PeTransitionRule:
    """Apply the one supported live correction: typed Hiring Pipeline Gates config."""

    clean_reason = str(reason or "").strip()
    clean_actor = str(actor_id or "").strip()
    clean_source = str(source or "").strip()
    if not clean_reason:
        raise ProcessPolicySafetyError("A non-empty correction reason is required")
    if not clean_actor:
        raise ProcessPolicySafetyError("Actor identity is required")
    if not clean_source:
        raise ProcessPolicySafetyError("Correction source is required")

    profile = await db.scalar(
        select(PeProcessProfile)
        .where(
            PeProcessProfile.id == str(process_profile_id),
            PeProcessProfile.tenant_id == str(tenant_id),
            PeProcessProfile.module == "recruitment",
        )
        .with_for_update()
    )
    if profile is None:
        raise ProcessProfileNotFoundError(str(process_profile_id))
    current_revision = int(profile.policy_revision or 1)
    if current_revision != int(expected_policy_revision):
        raise ProcessPolicyRevisionConflictError(
            expected_revision=int(expected_policy_revision),
            current_revision=current_revision,
        )

    rules = list(
        (
            await db.execute(
                select(PeTransitionRule)
                .where(
                    PeTransitionRule.tenant_id == str(tenant_id),
                    PeTransitionRule.process_profile_id == str(profile.id),
                )
                .order_by(PeTransitionRule.code.asc())
                .with_for_update()
            )
        ).scalars()
    )
    rule = next((row for row in rules if str(row.code) == str(rule_code)), None)
    if rule is None:
        raise ProcessPolicySafetyError(
            "Controlled live correction cannot create or reassign a transition rule"
        )
    if str(rule.process_profile_id) != str(profile.id):
        raise ProcessPolicySafetyError("Transition-rule ownership cannot be changed")

    from backend.app.process_engine.transition_rules_adapter import (
        gates_from_transition_rule_config,
        hiring_pipeline_gates_config_from_gates,
    )

    next_config = hiring_pipeline_gates_config_from_gates(gates)
    if gates_from_transition_rule_config(next_config) is None:
        raise ProcessPolicySafetyError("Invalid Hiring Pipeline Gates configuration")
    if dict(rule.config or {}) == next_config:
        return rule

    profile_before = _profile_policy_snapshot(profile)
    rule_before = _rule_policy_snapshot(rule)
    rule.config = next_config
    profile.policy_revision = current_revision + 1
    await db.flush()

    await log_activity(
        db,
        tenant_id=str(tenant_id),
        action="process_profile.policy_corrected",
        actor_id=clean_actor,
        target_type="process_profile",
        target_id=str(profile.id),
        payload={
            "reason": clean_reason,
            "source": clean_source,
            "previous_policy_revision": current_revision,
            "new_policy_revision": int(profile.policy_revision),
            "profile_before": profile_before,
            "profile_after": _profile_policy_snapshot(profile),
            "transition_rules_before": [rule_before],
            "transition_rules_after": [_rule_policy_snapshot(rule)],
        },
        ip=ip,
        ua=ua,
    )
    return rule


__all__ = [
    "PROFILE_METADATA_FIELDS",
    "PROFILE_PROTECTED_FIELDS",
    "TRANSITION_RULE_METADATA_FIELDS",
    "TRANSITION_RULE_PROTECTED_FIELDS",
    "ProcessPolicyRegistryDriftError",
    "ProcessPolicyRevisionConflictError",
    "ProcessPolicySafetyError",
    "ProcessProfileNotFoundError",
    "ProcessProfileReferenceUsage",
    "classify_process_profile_references",
    "correct_hiring_pipeline_gates_policy",
    "update_process_profile_metadata",
]
