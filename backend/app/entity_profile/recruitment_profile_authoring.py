"""ADR-043 tenant-owned Recruitment Profile authoring contract."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.config_deprecation import DEPRECATED_CONFIG_KEYS
from backend.app.entity_profile.exceptions import EntityProfileNotFoundError
from backend.app.entity_profile.publication_versions import publish_entity_profile
from backend.app.models.entity_profile import EpEntityProfile, EpEntityProfileVersion


class RecruitmentProfileAuthoringError(ValueError):
    """Base error for invalid Recruitment Profile authoring requests."""


class RecruitmentProfileAlreadyExistsError(RecruitmentProfileAuthoringError):
    """Raised when a tenant already owns the requested profile code."""


class RecruitmentProfileTemplateError(RecruitmentProfileAuthoringError):
    """Raised when a requested platform template cannot be used."""


class RecruitmentProfileVersionConflictError(RecruitmentProfileAuthoringError):
    """Raised when the caller's expected published version is stale."""

    def __init__(self, *, expected_version: int, current_version: int) -> None:
        self.expected_version = int(expected_version)
        self.current_version = int(current_version)
        super().__init__(
            "Recruitment Profile published version conflict: "
            f"expected {self.expected_version}, current {self.current_version}"
        )


def _tenant_key(tenant_id: str) -> str:
    value = str(tenant_id or "").strip()
    if not value:
        raise RecruitmentProfileAuthoringError(
            "Tenant-owned Recruitment Profiles require a non-empty tenant_id"
        )
    return value


def _profile_code(profile_code: str) -> str:
    value = str(profile_code or "").strip()
    if not value:
        raise RecruitmentProfileAuthoringError("profile_code must be non-empty")
    return value


def _explicit_config(config: dict[str, Any]) -> dict[str, Any]:
    copied = dict(config)
    forbidden_keys = sorted(DEPRECATED_CONFIG_KEYS.intersection(copied))
    if forbidden_keys:
        raise RecruitmentProfileAuthoringError(
            "Recruitment Profile config contains deprecated config keys: "
            + ", ".join(forbidden_keys)
        )
    return copied


def _template_config(template: EpEntityProfile) -> dict[str, Any]:
    return {
        key: value
        for key, value in dict(template.config or {}).items()
        if key not in DEPRECATED_CONFIG_KEYS
    }


async def _load_platform_template(
    db: AsyncSession,
    *,
    template_profile_code: str,
) -> EpEntityProfile:
    code = _profile_code(template_profile_code)
    template = await db.scalar(
        select(EpEntityProfile).where(
            EpEntityProfile.tenant_id == "",
            EpEntityProfile.profile_code == code,
        )
    )
    if (
        template is None
        or template.module_owner != "recruitment"
        or template.entity_type != "candidate"
        or not template.is_system
    ):
        raise RecruitmentProfileTemplateError(
            f"Recruitment Profile template could not be resolved: {code}"
        )
    return template


async def create_recruitment_profile(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_code: str,
    name: str | None = None,
    description: str | None = None,
    default_layout_code: str | None = None,
    config: dict[str, Any] | None = None,
    field_bindings: Sequence[dict[str, Any]] = (),
    document_bindings: Sequence[dict[str, Any]] = (),
    template_profile_code: str | None = None,
) -> EpEntityProfileVersion:
    """Create a tenant Recruitment Profile head and publish immutable v1."""

    tenant_key = _tenant_key(tenant_id)
    code = _profile_code(profile_code)

    existing_id = await db.scalar(
        select(EpEntityProfile.id).where(
            EpEntityProfile.tenant_id == tenant_key,
            EpEntityProfile.profile_code == code,
        )
    )
    if existing_id is not None:
        raise RecruitmentProfileAlreadyExistsError(
            f"Recruitment Profile already exists in tenant scope: {code}"
        )

    template: EpEntityProfile | None = None
    if template_profile_code is not None:
        template = await _load_platform_template(
            db,
            template_profile_code=template_profile_code,
        )

    resolved_name = name if name is not None else (template.name if template else None)
    if not str(resolved_name or "").strip():
        raise RecruitmentProfileAuthoringError("name must be non-empty")

    resolved_description = (
        description
        if description is not None
        else (template.description if template else None)
    )
    resolved_layout = (
        default_layout_code
        if default_layout_code is not None
        else (template.default_layout_code if template else None)
    )
    resolved_config = (
        _explicit_config(config)
        if config is not None
        else _template_config(template)
        if template is not None
        else {}
    )

    async with db.begin_nested():
        profile = EpEntityProfile(
            tenant_id=tenant_key,
            profile_code=code,
            registry_version="entity_profile_v1",
            status="active",
            name=str(resolved_name).strip(),
            description=resolved_description,
            is_system=False,
            entity_type="candidate",
            module_owner="recruitment",
            default_layout_code=resolved_layout,
            document_pack_code=None,
            process_profile_code=None,
            version=1,
            published_version=0,
            config=resolved_config,
        )
        db.add(profile)
        await db.flush()

        published = await publish_entity_profile(
            db,
            tenant_id=tenant_key,
            entity_profile_id=profile.id,
            field_bindings=field_bindings,
            document_bindings=document_bindings,
        )

    return published


async def publish_recruitment_profile_revision(
    db: AsyncSession,
    *,
    tenant_id: str,
    entity_profile_id: str,
    expected_published_version: int,
    name: str,
    description: str | None,
    default_layout_code: str | None,
    config: dict[str, Any],
    field_bindings: Sequence[dict[str, Any]] = (),
    document_bindings: Sequence[dict[str, Any]] = (),
) -> EpEntityProfileVersion:
    """Publish the next immutable revision after locking and checking its head."""

    tenant_key = _tenant_key(tenant_id)
    profile_id = str(entity_profile_id or "").strip()
    if not profile_id:
        raise EntityProfileNotFoundError(profile_id)

    profile = await db.scalar(
        select(EpEntityProfile)
        .where(
            EpEntityProfile.id == profile_id,
            EpEntityProfile.tenant_id == tenant_key,
        )
        .with_for_update()
    )
    if (
        profile is None
        or profile.module_owner != "recruitment"
        or profile.entity_type != "candidate"
        or profile.is_system
    ):
        raise EntityProfileNotFoundError(profile_id)

    current_version = int(profile.published_version or 0)
    expected_version = int(expected_published_version)
    if current_version != expected_version:
        raise RecruitmentProfileVersionConflictError(
            expected_version=expected_version,
            current_version=current_version,
        )

    resolved_name = str(name or "").strip()
    if not resolved_name:
        raise RecruitmentProfileAuthoringError("name must be non-empty")
    resolved_config = _explicit_config(config)

    async with db.begin_nested():
        profile.name = resolved_name
        profile.description = description
        profile.default_layout_code = default_layout_code
        profile.config = resolved_config

        published = await publish_entity_profile(
            db,
            tenant_id=tenant_key,
            entity_profile_id=profile_id,
            field_bindings=field_bindings,
            document_bindings=document_bindings,
        )

    return published


__all__ = [
    "RecruitmentProfileAlreadyExistsError",
    "RecruitmentProfileAuthoringError",
    "RecruitmentProfileTemplateError",
    "RecruitmentProfileVersionConflictError",
    "create_recruitment_profile",
    "publish_recruitment_profile_revision",
]
