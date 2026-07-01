from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeVersion
from backend.app.services.document_type_canonical_bridge import normalize_legacy_doc_type

logger = logging.getLogger("backend.app.services.document_type_runtime_resolver")


@dataclass
class DocumentTypeRuntimeResolved:
    canonical_document_type_id: Optional[str]
    canonical_code: str
    canonical_public_name: Optional[str]
    document_type_version_id: Optional[str]
    category_code: Optional[str]
    subcategory_code: Optional[str]
    business_purposes: list[str]
    required_fields: list[str]
    expiry_rules: dict[str, Any]
    compliance_criticality: Optional[str]
    verification_profile: dict[str, Any]
    status_model: str
    fallback_used: bool
    fallback_source: Optional[str]


class DocumentTypeRuntimeResolver:
    """Single runtime source for document type metadata with legacy fallback."""

    @staticmethod
    def _log(event: str, **kwargs: Any) -> None:
        logger.info(event, extra={"event": event, **kwargs})

    @classmethod
    async def resolve_for_document(
        cls,
        db: AsyncSession,
        document: Document,
    ) -> DocumentTypeRuntimeResolved:
        # 1) documents.document_type_version_id
        if getattr(document, "document_type_version_id", None):
            resolved = await cls._resolve_by_version_id(db, str(document.document_type_version_id), document=document)
            if resolved:
                cls._log("document_reference_resolved", document_id=str(document.id), source="document_type_version_id", canonical_code=resolved.canonical_code)
                return resolved
            cls._log("document_reference_version_missing", document_id=str(document.id), document_type_version_id=str(document.document_type_version_id))

        # 2) documents.document_type_id -> active/latest version
        if getattr(document, "document_type_id", None):
            resolved = await cls._resolve_by_document_type_id(db, str(document.document_type_id), document=document)
            if resolved:
                cls._log("document_reference_resolved", document_id=str(document.id), source="document_type_id", canonical_code=resolved.canonical_code)
                return resolved

        # 3) legacy documents.doc_type -> canonical mapping
        legacy_raw = str(getattr(document, "doc_type", "") or "").strip()
        canonical_code = normalize_legacy_doc_type(legacy_raw)
        resolved = await cls._resolve_by_canonical_code(db, canonical_code, fallback_used=True, fallback_source="legacy_doc_type", document=document)
        if resolved:
            cls._log(
                "document_reference_runtime_fallback_used",
                document_id=str(document.id),
                legacy_doc_type=legacy_raw,
                canonical_code=canonical_code,
                fallback_source="legacy_doc_type",
            )
            return resolved

        # 4) fallback to other
        cls._log("document_reference_unknown_legacy_type", document_id=str(document.id), legacy_doc_type=legacy_raw)
        resolved_other = await cls._resolve_by_canonical_code(db, "other", fallback_used=True, fallback_source="other", document=document)
        if resolved_other:
            cls._log("document_reference_runtime_fallback_used", document_id=str(document.id), legacy_doc_type=legacy_raw, canonical_code="other", fallback_source="other")
            return resolved_other

        # Last-resort emergency object (should not happen after M2 seed)
        return DocumentTypeRuntimeResolved(
            canonical_document_type_id=None,
            canonical_code="other",
            canonical_public_name="Other",
            document_type_version_id=None,
            category_code="other",
            subcategory_code=None,
            business_purposes=["internal_record"],
            required_fields=["custom_name"],
            expiry_rules={},
            compliance_criticality="informational",
            verification_profile={"manual_review_required": True},
            status_model="evidence",
            fallback_used=True,
            fallback_source="emergency",
        )

    @classmethod
    async def _resolve_by_version_id(
        cls,
        db: AsyncSession,
        version_id: str,
        *,
        document: Document,
    ) -> Optional[DocumentTypeRuntimeResolved]:
        stmt = (
            select(RefDocumentTypeVersion, RefDocumentType)
            .join(RefDocumentType, RefDocumentType.id == RefDocumentTypeVersion.document_type_id)
            .where(RefDocumentTypeVersion.id == version_id)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            return None
        ver, doc_type = row
        return cls._build_resolved(doc_type, ver, fallback_used=False, fallback_source=None)

    @classmethod
    async def _resolve_by_document_type_id(
        cls,
        db: AsyncSession,
        document_type_id: str,
        *,
        document: Document,
    ) -> Optional[DocumentTypeRuntimeResolved]:
        doc_type = await db.get(RefDocumentType, document_type_id)
        if not doc_type:
            return None

        ver_stmt = (
            select(RefDocumentTypeVersion)
            .where(RefDocumentTypeVersion.document_type_id == document_type_id)
            .where(or_(RefDocumentTypeVersion.valid_to.is_(None), RefDocumentTypeVersion.valid_to >= RefDocumentTypeVersion.valid_from))
            .order_by(RefDocumentTypeVersion.valid_from.desc(), RefDocumentTypeVersion.created_at.desc())
        )
        ver = (await db.execute(ver_stmt)).scalars().first()
        if not ver:
            cls._log("document_reference_version_missing", document_id=str(document.id), document_type_id=document_type_id)
            return cls._build_resolved(doc_type, None, fallback_used=True, fallback_source="document_type_no_version")
        return cls._build_resolved(doc_type, ver, fallback_used=False, fallback_source=None)

    @classmethod
    async def _resolve_by_canonical_code(
        cls,
        db: AsyncSession,
        canonical_code: str,
        *,
        fallback_used: bool,
        fallback_source: Optional[str],
        document: Document,
    ) -> Optional[DocumentTypeRuntimeResolved]:
        stmt = select(RefDocumentType).where(and_(RefDocumentType.code == canonical_code, RefDocumentType.status.in_(["active", "deprecated", "draft"])))
        doc_type = (await db.execute(stmt)).scalars().first()
        if not doc_type:
            return None

        ver_stmt = (
            select(RefDocumentTypeVersion)
            .where(RefDocumentTypeVersion.document_type_id == doc_type.id)
            .order_by(RefDocumentTypeVersion.valid_from.desc(), RefDocumentTypeVersion.created_at.desc())
        )
        ver = (await db.execute(ver_stmt)).scalars().first()
        if not ver:
            cls._log("document_reference_version_missing", document_id=str(document.id), canonical_code=canonical_code)
        return cls._build_resolved(doc_type, ver, fallback_used=fallback_used, fallback_source=fallback_source)

    @staticmethod
    def _build_resolved(
        doc_type: RefDocumentType,
        ver: Optional[RefDocumentTypeVersion],
        *,
        fallback_used: bool,
        fallback_source: Optional[str],
    ) -> DocumentTypeRuntimeResolved:
        business_purposes = []
        required_fields = []
        expiry_rules: dict[str, Any] = {}
        verification_profile: dict[str, Any] = {}
        status_model = "evidence"

        if ver is not None:
            purposes_payload = (ver.business_purposes_json or {}).get("purposes")
            if isinstance(purposes_payload, list):
                business_purposes = [str(x) for x in purposes_payload]
            schema_required = (ver.schema_json or {}).get("required")
            if isinstance(schema_required, list):
                required_fields = [str(x) for x in schema_required]
            expiry_rules = dict(ver.expiry_rules_json or {})
            verification_profile = dict(ver.verification_profile_json or {})
            status_model = str(ver.status_model or "evidence")

        return DocumentTypeRuntimeResolved(
            canonical_document_type_id=str(doc_type.id),
            canonical_code=str(doc_type.code),
            canonical_public_name=str(doc_type.public_name or ""),
            document_type_version_id=str(ver.id) if ver is not None else None,
            category_code=str(doc_type.category_code or "") or None,
            subcategory_code=str(doc_type.subcategory_code or "") or None,
            business_purposes=business_purposes,
            required_fields=required_fields,
            expiry_rules=expiry_rules,
            compliance_criticality=str(doc_type.criticality or "") or None,
            verification_profile=verification_profile,
            status_model=status_model,
            fallback_used=fallback_used,
            fallback_source=fallback_source,
        )
