"""ADR-043 HR Employment Profile policy read contract.

This module exposes immutable published profile requirements. It deliberately
does not evaluate or materialize requirements and does not adapt legacy policy
sources.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.entity_profile import (
    EpEntityProfile,
    EpEntityProfileVersion,
    EpEntityProfileVersionDocument,
    EpEntityProfileVersionField,
)
from backend.app.models.field_registry import FrCanonicalField
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
)


CONTRACT_ID = "hr_employment_profile_policy.v1"


class HrEmploymentProfilePolicyResolutionError(LookupError):
    """Raised when a requested HR Employment Profile policy cannot be resolved."""


@dataclass(frozen=True)
class HrEmploymentProfileFieldPolicy:
    canonical_field_id: str
    qualified_code: str
    requirement_level: str
    sort_order: int


@dataclass(frozen=True)
class HrEmploymentProfileDocumentPolicy:
    document_type_id: str
    document_type_code: str
    document_type_version_id: str
    document_type_version_code: str
    requirement_level: str
    sort_order: int


@dataclass(frozen=True)
class HrEmploymentProfilePolicy:
    contract_version: str
    profile_version_id: str
    entity_profile_id: str
    profile_code: str
    profile_version: int
    tenant_id: str
    module_owner: str
    entity_type: str
    fields: tuple[HrEmploymentProfileFieldPolicy, ...]
    documents: tuple[HrEmploymentProfileDocumentPolicy, ...]


def _resolution_error(
    profile_version_id: str,
) -> HrEmploymentProfilePolicyResolutionError:
    return HrEmploymentProfilePolicyResolutionError(
        "HR Employment Profile policy could not be resolved for profile version: "
        f"{profile_version_id}"
    )


async def load_hr_employment_profile_policy(
    db: AsyncSession,
    *,
    tenant_id: str,
    profile_version_id: str,
) -> HrEmploymentProfilePolicy:
    """Load one immutable HR workforce employee profile policy, fail closed."""

    tenant_key = str(tenant_id)
    version_key = str(profile_version_id)

    profile_row = (
        await db.execute(
            select(
                EpEntityProfileVersion.id.label("profile_version_id"),
                EpEntityProfileVersion.entity_profile_id,
                EpEntityProfile.profile_code,
                EpEntityProfileVersion.version.label("profile_version"),
                EpEntityProfileVersion.tenant_id,
                EpEntityProfileVersion.module_owner,
                EpEntityProfileVersion.entity_type,
            )
            .select_from(EpEntityProfileVersion)
            .join(
                EpEntityProfile,
                EpEntityProfile.id == EpEntityProfileVersion.entity_profile_id,
            )
            .where(
                EpEntityProfileVersion.id == version_key,
                EpEntityProfileVersion.tenant_id == tenant_key,
                EpEntityProfile.tenant_id == tenant_key,
            )
        )
    ).one_or_none()

    if (
        profile_row is None
        or profile_row.module_owner != "hr"
        or profile_row.entity_type != "workforce_employee"
    ):
        raise _resolution_error(version_key)

    field_rows = (
        await db.execute(
            select(
                EpEntityProfileVersionField.canonical_field_id,
                EpEntityProfileVersionField.qualified_code,
                EpEntityProfileVersionField.requirement_level,
                EpEntityProfileVersionField.sort_order,
                FrCanonicalField.id.label("resolved_canonical_field_id"),
            )
            .select_from(EpEntityProfileVersionField)
            .outerjoin(
                FrCanonicalField,
                FrCanonicalField.id
                == EpEntityProfileVersionField.canonical_field_id,
            )
            .where(
                EpEntityProfileVersionField.entity_profile_version_id == version_key
            )
            .order_by(
                EpEntityProfileVersionField.sort_order.asc(),
                EpEntityProfileVersionField.canonical_field_id.asc(),
            )
        )
    ).all()

    fields: list[HrEmploymentProfileFieldPolicy] = []
    for row in field_rows:
        if row.resolved_canonical_field_id is None:
            raise _resolution_error(version_key)
        fields.append(
            HrEmploymentProfileFieldPolicy(
                canonical_field_id=str(row.canonical_field_id),
                qualified_code=str(row.qualified_code),
                requirement_level=str(row.requirement_level),
                sort_order=int(row.sort_order),
            )
        )

    document_rows = (
        await db.execute(
            select(
                EpEntityProfileVersionDocument.document_type_version_id,
                EpEntityProfileVersionDocument.requirement_level,
                EpEntityProfileVersionDocument.sort_order,
                RefDocumentTypeVersion.id.label("resolved_document_type_version_id"),
                RefDocumentTypeVersion.version_code.label(
                    "document_type_version_code"
                ),
                RefDocumentType.id.label("document_type_id"),
                RefDocumentType.code.label("document_type_code"),
            )
            .select_from(EpEntityProfileVersionDocument)
            .outerjoin(
                RefDocumentTypeVersion,
                RefDocumentTypeVersion.id
                == EpEntityProfileVersionDocument.document_type_version_id,
            )
            .outerjoin(
                RefDocumentType,
                RefDocumentType.id == RefDocumentTypeVersion.document_type_id,
            )
            .where(
                EpEntityProfileVersionDocument.entity_profile_version_id
                == version_key
            )
            .order_by(
                EpEntityProfileVersionDocument.sort_order.asc(),
                EpEntityProfileVersionDocument.document_type_version_id.asc(),
            )
        )
    ).all()

    documents: list[HrEmploymentProfileDocumentPolicy] = []
    for row in document_rows:
        if (
            row.resolved_document_type_version_id is None
            or row.document_type_id is None
        ):
            raise _resolution_error(version_key)
        documents.append(
            HrEmploymentProfileDocumentPolicy(
                document_type_id=str(row.document_type_id),
                document_type_code=str(row.document_type_code),
                document_type_version_id=str(row.document_type_version_id),
                document_type_version_code=str(row.document_type_version_code),
                requirement_level=str(row.requirement_level),
                sort_order=int(row.sort_order),
            )
        )

    return HrEmploymentProfilePolicy(
        contract_version=CONTRACT_ID,
        profile_version_id=str(profile_row.profile_version_id),
        entity_profile_id=str(profile_row.entity_profile_id),
        profile_code=str(profile_row.profile_code),
        profile_version=int(profile_row.profile_version),
        tenant_id=str(profile_row.tenant_id),
        module_owner=str(profile_row.module_owner),
        entity_type=str(profile_row.entity_type),
        fields=tuple(fields),
        documents=tuple(documents),
    )


__all__ = [
    "CONTRACT_ID",
    "HrEmploymentProfileDocumentPolicy",
    "HrEmploymentProfileFieldPolicy",
    "HrEmploymentProfilePolicy",
    "HrEmploymentProfilePolicyResolutionError",
    "load_hr_employment_profile_policy",
]
