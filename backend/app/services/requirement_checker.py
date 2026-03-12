"""Service for checking document requirements and gate satisfaction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.document_policy import DocumentPolicy, RequirementLevel
from backend.app.models.document_type import DocumentType
from backend.app.models.enums import DocumentStatus, DocumentStatusModel, GateCode, RequirementType
from backend.app.models.requirement_type import RequirementTypeDefinition
from backend.app.services.status_transitions import StatusTransitionService


@dataclass
class RequirementCheckResult:
    """Результат проверки требования."""

    requirement_code: Optional[str]  # requirement_code или document_type_id
    satisfied: bool
    blocking: bool  # Блокирует ли gate
    message: Optional[str] = None
    satisfied_by_documents: List[str] = None  # ID документов, которые удовлетворяют требование


@dataclass
class GateCheckResult:
    """Результат проверки gate."""

    gate_code: GateCode
    passed: bool
    blocking_requirements: List[RequirementCheckResult]
    optional_requirements: List[RequirementCheckResult]


async def check_requirement_satisfaction(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    requirement_code: Optional[RequirementType] = None,
    document_type_id: Optional[str] = None,
    candidate_is_eu: bool = False,
) -> RequirementCheckResult:
    """Проверяет, удовлетворено ли требование для кандидата.

    Args:
        db: Database session
        tenant_id: Tenant ID
        candidate_id: Candidate ID
        requirement_code: Код виртуального требования (например CODE95_EVIDENCE)
        document_type_id: ID типа документа (если проверяем конкретный документ)
        candidate_is_eu: Является ли кандидат гражданином EU (для RIGHT_TO_WORK_BASIS)

    Returns:
        RequirementCheckResult с информацией о том, удовлетворено ли требование
    """
    if requirement_code is None and document_type_id is None:
        raise ValueError("Either requirement_code or document_type_id must be provided")

    # Специальная обработка для RIGHT_TO_WORK_BASIS для EU граждан
    if requirement_code == RequirementType.RIGHT_TO_WORK_BASIS and candidate_is_eu:
        return RequirementCheckResult(
            requirement_code=requirement_code.value if requirement_code else None,
            satisfied=True,
            blocking=False,
            message="EU citizens do not require right-to-work basis docs",
        )

    # Загружаем определение требования, если это виртуальное требование
    if requirement_code:
        stmt_req = (
            select(RequirementTypeDefinition)
            .where(RequirementTypeDefinition.tenant_id == tenant_id)
            .where(RequirementTypeDefinition.requirement_code == requirement_code)
            .where(RequirementTypeDefinition.is_active == True)
        )
        req_def = (await db.execute(stmt_req)).scalar_one_or_none()
        if not req_def:
            return RequirementCheckResult(
                requirement_code=requirement_code.value,
                satisfied=False,
                blocking=True,
                message=f"Requirement definition not found: {requirement_code.value}",
            )

        # Проверяем satisfaction_rules
        rules = req_def.satisfaction_rules or {}
        satisfied_by_any = rules.get("satisfied_by_any", [])

        if not satisfied_by_any:
            return RequirementCheckResult(
                requirement_code=requirement_code.value,
                satisfied=False,
                blocking=True,
                message=f"No satisfaction rules defined for {requirement_code.value}",
            )

        # Проверяем каждый вариант удовлетворения
        satisfied_docs: List[str] = []
        for rule in satisfied_by_any:
            doc_type_code = rule.get("document_type")
            required_statuses = rule.get("status", [])
            require_valid = rule.get("valid", False)
            meta_conditions = rule.get("meta", {})

            # Находим документы этого типа у кандидата
            stmt_docs = (
                select(Document)
                .where(Document.tenant_id == tenant_id)
                .where(Document.candidate_id == candidate_id)
                .where(Document.deleted_at.is_(None))
            )

            # Находим document_type по code
            if doc_type_code:
                stmt_doc_type = (
                    select(DocumentType)
                    .where(DocumentType.tenant_id == tenant_id)
                    .where(DocumentType.code == doc_type_code)
                    .where(DocumentType.is_active == True)
                )
                doc_type = (await db.execute(stmt_doc_type)).scalar_one_or_none()
                if doc_type:
                    stmt_docs = stmt_docs.where(Document.doc_type == doc_type.code)

            docs = (await db.execute(stmt_docs)).scalars().all()

            for doc in docs:
                # Проверяем статус
                if required_statuses:
                    doc_status = doc.status.value if hasattr(doc.status, 'value') else str(doc.status)
                    # Нормализуем статусы (например, VERIFIED -> verified)
                    doc_status_normalized = doc_status.upper()
                    required_statuses_normalized = [s.upper() for s in required_statuses]
                    if doc_status_normalized not in required_statuses_normalized:
                        continue

                # Проверяем валидность используя статус-модель
                if require_valid:
                    # Используем StatusTransitionService для проверки "OK" статуса
                    is_ok = StatusTransitionService.is_status_ok_for_gate(doc)
                    if not is_ok:
                        continue

                # Проверяем meta условия (например, code95: true)
                if meta_conditions:
                    doc_meta = doc.meta or {}
                    for key, expected_value in meta_conditions.items():
                        if doc_meta.get(key) != expected_value:
                            break
                    else:
                        # Все условия выполнены
                        satisfied_docs.append(doc.id)
                        break
                else:
                    satisfied_docs.append(doc.id)
                    break

        satisfied = len(satisfied_docs) > 0
        return RequirementCheckResult(
            requirement_code=requirement_code.value,
            satisfied=satisfied,
            blocking=not satisfied,  # Пока считаем блокирующим, если не удовлетворено
            message=None if satisfied else f"Requirement {requirement_code.value} not satisfied",
            satisfied_by_documents=satisfied_docs,
        )

    # Проверка конкретного типа документа
    if document_type_id:
        stmt_doc_type = (
            select(DocumentType)
            .where(DocumentType.id == document_type_id)
            .where(DocumentType.tenant_id == tenant_id)
        )
        doc_type = (await db.execute(stmt_doc_type)).scalar_one_or_none()
        if not doc_type:
            return RequirementCheckResult(
                requirement_code=document_type_id,
                satisfied=False,
                blocking=True,
                message=f"Document type not found: {document_type_id}",
            )

        # Находим документы этого типа
        stmt_docs = (
            select(Document)
            .where(Document.tenant_id == tenant_id)
            .where(Document.candidate_id == candidate_id)
            .where(Document.doc_type == doc_type.code)
            .where(Document.deleted_at.is_(None))
        )
        docs = (await db.execute(stmt_docs)).scalars().all()

        # Проверяем наличие валидного документа используя статус-модель
        valid_docs: List[str] = []
        for doc in docs:
            # Используем StatusTransitionService для проверки "OK" статуса
            is_ok = StatusTransitionService.is_status_ok_for_gate(doc)
            if is_ok:
                valid_docs.append(doc.id)

        satisfied = len(valid_docs) > 0
        return RequirementCheckResult(
            requirement_code=document_type_id,
            satisfied=satisfied,
            blocking=not satisfied,
            message=None if satisfied else f"Document type {doc_type.code} not found or invalid",
            satisfied_by_documents=valid_docs,
        )

    # Не должно быть достигнуто
    return RequirementCheckResult(
        requirement_code=None,
        satisfied=False,
        blocking=True,
        message="Invalid requirement check",
    )


async def check_gate_requirements(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    gate_code: GateCode,
    client_id: Optional[str] = None,
    vacancy_id: Optional[str] = None,
    candidate_is_eu: bool = False,
) -> GateCheckResult:
    """Проверяет, пройден ли gate для кандидата.

    Args:
        db: Database session
        tenant_id: Tenant ID
        candidate_id: Candidate ID
        gate_code: Код gate для проверки
        client_id: Client ID (для применения client-level policies)
        vacancy_id: Vacancy ID (для применения vacancy-level policies)
        candidate_is_eu: Является ли кандидат гражданином EU

    Returns:
        GateCheckResult с информацией о прохождении gate
    """
    # Загружаем все политики для этого gate
    stmt_policies = (
        select(DocumentPolicy)
        .where(DocumentPolicy.tenant_id == tenant_id)
        .where(DocumentPolicy.enabled == True)
    )

    # Фильтруем по gates (JSONB массив содержит gate_code)
    # В PostgreSQL: WHERE gate_code = ANY(gates)
    # В SQLite: используем JSON функции
    policies = (await db.execute(stmt_policies)).scalars().all()

    # Фильтруем политики, которые применяются к этому gate
    gate_policies: List[DocumentPolicy] = []
    gate_code_str = gate_code.value

    for policy in policies:
        gates = policy.gates or []
        if gate_code_str in gates:
            # Проверяем scope
            if policy.scope.value == "tenant" and policy.scope_id is None:
                gate_policies.append(policy)
            elif policy.scope.value == "client" and client_id and policy.scope_id == client_id:
                gate_policies.append(policy)
            elif policy.scope.value == "vacancy" and vacancy_id and policy.scope_id == vacancy_id:
                gate_policies.append(policy)

    # Применяем приоритет: VACANCY > CLIENT > TENANT
    # Группируем по requirement_code или document_type_id
    final_policies: Dict[str, DocumentPolicy] = {}
    for policy in gate_policies:
        key = policy.requirement_code.value if policy.requirement_code else policy.document_type_id
        if key:
            # Если уже есть политика с более высоким приоритетом, пропускаем
            if key in final_policies:
                existing = final_policies[key]
                priority_map = {"vacancy": 3, "client": 2, "tenant": 1}
                if priority_map.get(policy.scope.value, 0) > priority_map.get(existing.scope.value, 0):
                    final_policies[key] = policy
            else:
                final_policies[key] = policy

    # Проверяем каждое требование
    blocking_requirements: List[RequirementCheckResult] = []
    optional_requirements: List[RequirementCheckResult] = []

    for policy in final_policies.values():
        if policy.required_level == RequirementLevel.DISABLED:
            continue

        check_result = await check_requirement_satisfaction(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            requirement_code=policy.requirement_code,
            document_type_id=policy.document_type_id,
            candidate_is_eu=candidate_is_eu,
        )

        # Устанавливаем blocking в зависимости от required_level
        check_result.blocking = (
            policy.required_level in (RequirementLevel.REQUIRED, RequirementLevel.BLOCKING)
            and not check_result.satisfied
        )

        if check_result.blocking:
            blocking_requirements.append(check_result)
        else:
            optional_requirements.append(check_result)

    passed = len(blocking_requirements) == 0

    return GateCheckResult(
        gate_code=gate_code,
        passed=passed,
        blocking_requirements=blocking_requirements,
        optional_requirements=optional_requirements,
    )


__all__ = [
    "RequirementCheckResult",
    "GateCheckResult",
    "check_requirement_satisfaction",
    "check_gate_requirements",
]

