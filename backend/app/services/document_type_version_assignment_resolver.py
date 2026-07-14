"""Deterministic document type version assignment for ADR-018 migration (PR 2B-4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from jsonschema import Draft202012Validator
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.document_types.registry import is_canonical_code, normalize_input_doc_type
from backend.app.document_types.schema_registry import normalize_raw_to_document_data
from backend.app.models.document import Document
from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeVersion

INBOX_TYPES = frozenset({"unclassified", "other", "additional_document"})


class VersionAssignmentStatus(str, Enum):
    existing = "existing"
    resolved = "resolved"
    ambiguous = "ambiguous"
    none = "none"


@dataclass(frozen=True)
class VersionAssignmentResult:
    status: VersionAssignmentStatus
    document_type_id: Optional[str]
    document_type_version_id: Optional[str]
    version_code: Optional[str]
    reason: str
    compatible_version_ids: tuple[str, ...] = ()

    @property
    def is_assignable(self) -> bool:
        return self.status in {VersionAssignmentStatus.existing, VersionAssignmentStatus.resolved}


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _reference_date(document: Document) -> date:
    created = getattr(document, "created_at", None)
    if isinstance(created, datetime):
        return created.date()
    if isinstance(created, date):
        return created
    return date.today()


def _merge_meta(document: Document) -> dict[str, Any]:
    meta = getattr(document, "meta", None) or {}
    if not isinstance(meta, dict):
        return {}
    merged = dict(meta)
    extracted = meta.get("extracted_fields") or meta.get("fields")
    if isinstance(extracted, dict):
        for key, value in extracted.items():
            merged.setdefault(key, value)
    return merged


def _schema_valid_for_version(version: RefDocumentTypeVersion, document_data: dict[str, Any]) -> bool:
    schema = version.schema_json if isinstance(version.schema_json, dict) else {}
    if not schema:
        return True
    validator = Draft202012Validator(schema)
    return validator.is_valid(document_data or {})


def _version_active_on(ref_date: date, version: RefDocumentTypeVersion) -> bool:
    if ref_date < version.valid_from:
        return False
    if version.valid_to is not None and ref_date > version.valid_to:
        return False
    return True


class DocumentTypeVersionAssignmentResolver:
    """Assign ref document type version deterministically — never pick latest without compatibility."""

    @classmethod
    async def resolve_for_document(
        cls,
        db: AsyncSession,
        document: Document,
        *,
        canonical_type_code: Optional[str] = None,
    ) -> VersionAssignmentResult:
        canonical = _norm(canonical_type_code or normalize_input_doc_type(getattr(document, "doc_type", "")))
        if canonical in INBOX_TYPES or not is_canonical_code(canonical):
            return VersionAssignmentResult(
                status=VersionAssignmentStatus.none,
                document_type_id=None,
                document_type_version_id=None,
                version_code=None,
                reason=f"non_assignable_type:{canonical}",
            )

        existing_version_id = str(getattr(document, "document_type_version_id", "") or "").strip()
        if existing_version_id:
            verified = await cls._verify_existing_version(db, existing_version_id, canonical_code=canonical)
            if verified:
                return verified
            return VersionAssignmentResult(
                status=VersionAssignmentStatus.ambiguous,
                document_type_id=str(getattr(document, "document_type_id", "") or "") or None,
                document_type_version_id=existing_version_id,
                version_code=None,
                reason="existing_version_incompatible_with_canonical_type",
            )

        ref_date = _reference_date(document)
        document_data = normalize_raw_to_document_data(canonical, _merge_meta(document))

        doc_type = (
            await db.execute(
                select(RefDocumentType).where(
                    RefDocumentType.code == canonical,
                    RefDocumentType.status.in_(["active", "deprecated"]),
                )
            )
        ).scalars().first()
        if not doc_type:
            return VersionAssignmentResult(
                status=VersionAssignmentStatus.none,
                document_type_id=None,
                document_type_version_id=None,
                version_code=None,
                reason=f"ref_document_type_missing:{canonical}",
            )

        versions = list(
            (
                await db.execute(
                    select(RefDocumentTypeVersion)
                    .where(RefDocumentTypeVersion.document_type_id == doc_type.id)
                    .order_by(RefDocumentTypeVersion.valid_from.asc(), RefDocumentTypeVersion.created_at.asc())
                )
            ).scalars()
        )
        if not versions:
            return VersionAssignmentResult(
                status=VersionAssignmentStatus.none,
                document_type_id=str(doc_type.id),
                document_type_version_id=None,
                version_code=None,
                reason="no_versions_for_type",
            )

        date_compatible = [v for v in versions if _version_active_on(ref_date, v)]
        if not date_compatible:
            return VersionAssignmentResult(
                status=VersionAssignmentStatus.ambiguous,
                document_type_id=str(doc_type.id),
                document_type_version_id=None,
                version_code=None,
                reason="no_version_valid_on_document_date",
                compatible_version_ids=tuple(str(v.id) for v in versions),
            )

        schema_compatible = [v for v in date_compatible if _schema_valid_for_version(v, document_data)]
        pool = schema_compatible or date_compatible

        if len(pool) == 1:
            chosen = pool[0]
            return VersionAssignmentResult(
                status=VersionAssignmentStatus.resolved,
                document_type_id=str(doc_type.id),
                document_type_version_id=str(chosen.id),
                version_code=str(chosen.version_code),
                reason="single_compatible_version",
            )

        if len(date_compatible) == 1:
            chosen = date_compatible[0]
            return VersionAssignmentResult(
                status=VersionAssignmentStatus.resolved,
                document_type_id=str(doc_type.id),
                document_type_version_id=str(chosen.id),
                version_code=str(chosen.version_code),
                reason="single_date_compatible_version",
            )

        return VersionAssignmentResult(
            status=VersionAssignmentStatus.ambiguous,
            document_type_id=str(doc_type.id),
            document_type_version_id=None,
            version_code=None,
            reason="multiple_compatible_versions",
            compatible_version_ids=tuple(str(v.id) for v in pool),
        )

    @classmethod
    async def _verify_existing_version(
        cls,
        db: AsyncSession,
        version_id: str,
        *,
        canonical_code: str,
    ) -> Optional[VersionAssignmentResult]:
        row = (
            await db.execute(
                select(RefDocumentTypeVersion, RefDocumentType)
                .join(RefDocumentType, RefDocumentType.id == RefDocumentTypeVersion.document_type_id)
                .where(RefDocumentTypeVersion.id == version_id)
            )
        ).first()
        if not row:
            return None
        ver, doc_type = row
        if _norm(doc_type.code) != _norm(canonical_code):
            return None
        return VersionAssignmentResult(
            status=VersionAssignmentStatus.existing,
            document_type_id=str(doc_type.id),
            document_type_version_id=str(ver.id),
            version_code=str(ver.version_code),
            reason="existing_version_verified",
        )


__all__ = [
    "DocumentTypeVersionAssignmentResolver",
    "VersionAssignmentResult",
    "VersionAssignmentStatus",
]
