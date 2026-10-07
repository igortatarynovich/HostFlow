from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document_policy import DocumentPolicyScope


@dataclass
class DocumentRequirement:
    """Итоговая политика документа для конкретного контекста."""

    document_type_id: str
    enabled: bool
    required: bool
    alert_days_before_expiry: Optional[int]
    owner_user_id: Optional[str]
    # Для отладки можно хранить источник (TENANT / CLIENT / VACANCY).
    source_scope: Optional[DocumentPolicyScope] = None


async def compute_document_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    document_type_ids: Iterable[str] | None = None,
    client_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
) -> Dict[str, DocumentRequirement]:
    """Document_policies table is no longer required-X authority (RPM-3A).

    Returns empty — callers must use R5 merge / Requirement Policy operator.
    Signature kept for compatibility until RPM-3B removes call sites.
    """
    _ = (db, tenant_id, document_type_ids, client_id, vacancy_id)
    return {}


__all__ = ["DocumentRequirement", "compute_document_requirements"]
