from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import DocumentType  # type: ignore[import]
from backend.app.models.document_policy import DocumentPolicy, DocumentPolicyScope


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


def _merge_policies(
    *,
    tenant_policy: Optional[DocumentPolicy],
    client_policy: Optional[DocumentPolicy],
    vacancy_policy: Optional[DocumentPolicy],
) -> Optional[DocumentRequirement]:
    """Применяет приоритет VACANCY > CLIENT > TENANT и возвращает финальную политику.

    Если нет ни одной политики или все говорят enabled=False, можно вернуть None,
    чтобы не показывать документ вообще (это решается на уровне продукта).
    """

    # Порядок приоритета: vacancy > client > tenant.
    for policy, scope in (
        (vacancy_policy, DocumentPolicyScope.VACANCY),
        (client_policy, DocumentPolicyScope.CLIENT),
        (tenant_policy, DocumentPolicyScope.TENANT),
    ):
        if policy is None:
            continue
        if not policy.enabled:
            # Явное отключение на более высоком уровне.
            return DocumentRequirement(
                document_type_id=policy.document_type_id,
                enabled=False,
                required=False,
                alert_days_before_expiry=policy.alert_days_before_expiry,
                owner_user_id=policy.owner_user_id,
                source_scope=scope,
            )

        # enabled = True на этом уровне — базовая ветка.
        enabled = True
        required = bool(policy.required)
        return DocumentRequirement(
            document_type_id=policy.document_type_id,
            enabled=enabled,
            required=required,
            alert_days_before_expiry=policy.alert_days_before_expiry,
            owner_user_id=policy.owner_user_id,
            source_scope=scope,
        )

    return None


async def compute_document_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    document_type_ids: Iterable[str] | None = None,
    client_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
) -> Dict[str, DocumentRequirement]:
    """Возвращает итоговые требования по документам для заданного контекста.

    На входе: tenant_id и (опционально) client_id, vacancy_id.
    По желанию можно ограничить список document_type_ids, иначе берём все активные DocumentType.
    """

    if document_type_ids is None:
        stmt_types = select(DocumentType.id).where(DocumentType.is_active.is_(True))  # type: ignore[attr-defined]
        doc_ids = [row.id for row in (await db.execute(stmt_types)).all()]
    else:
        doc_ids = list(dict.fromkeys(str(did) for did in document_type_ids))

    if not doc_ids:
        return {}

    # Загружаем все политики для tenant/client/vacancy сразу.
    stmt_policies = (
        select(DocumentPolicy)
        .where(DocumentPolicy.tenant_id == tenant_id)
        .where(DocumentPolicy.document_type_id.in_(doc_ids))
    )
    rows = await db.execute(stmt_policies)
    policies: list[DocumentPolicy] = list(rows.scalars().all())

    tenant_policies_by_doc: dict[str, DocumentPolicy] = {}
    client_policies_by_doc: dict[str, DocumentPolicy] = {}
    vacancy_policies_by_doc: dict[str, DocumentPolicy] = {}

    for policy in policies:
        if policy.scope == DocumentPolicyScope.TENANT and policy.scope_id is None:
            tenant_policies_by_doc[policy.document_type_id] = policy
        elif policy.scope == DocumentPolicyScope.CLIENT and client_id and policy.scope_id == client_id:
            client_policies_by_doc[policy.document_type_id] = policy
        elif policy.scope == DocumentPolicyScope.VACANCY and vacancy_id and policy.scope_id == vacancy_id:
            vacancy_policies_by_doc[policy.document_type_id] = policy

    result: Dict[str, DocumentRequirement] = {}
    for doc_id in doc_ids:
        tenant_policy = tenant_policies_by_doc.get(doc_id)
        client_policy = client_policies_by_doc.get(doc_id)
        vacancy_policy = vacancy_policies_by_doc.get(doc_id)

        merged = _merge_policies(
            tenant_policy=tenant_policy,
            client_policy=client_policy,
            vacancy_policy=vacancy_policy,
        )
        if merged is not None:
            result[doc_id] = merged

    return result


__all__ = ["DocumentRequirement", "compute_document_requirements"]


