"""Service for managing document status transitions and validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.document import Document
from backend.app.models.document_type import DocumentType
from backend.app.models.enums import DocumentStatus, DocumentStatusModel
from backend.app.models.process_template import ProcessTemplate
from backend.app.services.document_type_runtime_resolver import (
    DocumentTypeRuntimeResolver,
)


@dataclass
class StatusTransition:
    """Разрешённый переход статуса."""

    from_status: str
    to_status: str
    allowed: bool
    requires_fields: List[str] = None
    requires_files: List[str] = None
    auto: bool = False  # Автоматический переход (например, по дате)


@dataclass
class StatusValidationResult:
    """Результат валидации статуса."""

    valid: bool
    message: Optional[str] = None
    missing_fields: List[str] = None
    missing_files: List[str] = None


class StatusTransitionService:
    """Сервис для работы с переходами статусов документов."""

    # Канонические статус-модели (системные, не изменяются пользователем)
    SYSTEM_STATUS_MODELS: Dict[DocumentStatusModel, Dict[str, Any]] = {
        DocumentStatusModel.EVIDENCE: {
            "statuses": {
                "MISSING": {"label": "Отсутствует", "is_terminal": False},
                "UPLOADED": {"label": "Загружен", "is_terminal": False},
                "VERIFIED": {"label": "Проверен", "is_terminal": False, "is_ok": True},
                "EXPIRED": {"label": "Истёк", "is_terminal": False},
                "REJECTED": {"label": "Отклонён", "is_terminal": False},
            },
            "transitions": [
                {"from": "MISSING", "to": "UPLOADED", "allowed": True},
                {"from": "UPLOADED", "to": "VERIFIED", "allowed": True},
                {"from": "UPLOADED", "to": "REJECTED", "allowed": True},
                {"from": "REJECTED", "to": "UPLOADED", "allowed": True},
                {"from": "VERIFIED", "to": "EXPIRED", "allowed": True, "auto": True},
                {"from": "EXPIRED", "to": "UPLOADED", "allowed": True},
            ],
            "ok_conditions": [
                {"status": "VERIFIED", "is_valid": True},
            ],
        },
        DocumentStatusModel.PROCESS_WP_A: {
            "statuses": {
                "NOT_REQUIRED": {"label": "Не требуется", "is_terminal": True},
                "TO_PREPARE": {"label": "К подготовке", "is_terminal": False},
                "SUBMITTED": {"label": "Подано", "is_terminal": False},
                "IN_PROGRESS": {"label": "В процессе", "is_terminal": False},
                "ISSUED": {"label": "Выдано", "is_terminal": False, "is_ok": True},
                "REJECTED": {"label": "Отклонено", "is_terminal": False},
                "EXPIRED": {"label": "Истёк", "is_terminal": False},
                "CANCELLED": {"label": "Отменено", "is_terminal": False},
            },
            "transitions": [
                {"from": "TO_PREPARE", "to": "SUBMITTED", "allowed": True, "requires_fields": ["submitted_at"]},
                {"from": "TO_PREPARE", "to": "CANCELLED", "allowed": True},
                {"from": "SUBMITTED", "to": "IN_PROGRESS", "allowed": True},
                {"from": "SUBMITTED", "to": "CANCELLED", "allowed": True},
                {"from": "IN_PROGRESS", "to": "ISSUED", "allowed": True, "requires_fields": ["decision_at", "valid_from", "valid_to"]},
                {"from": "IN_PROGRESS", "to": "REJECTED", "allowed": True, "requires_fields": ["decision_at"]},
                {"from": "IN_PROGRESS", "to": "CANCELLED", "allowed": True},
                {"from": "ISSUED", "to": "EXPIRED", "allowed": True, "auto": True},
                {"from": "ISSUED", "to": "CANCELLED", "allowed": True},
                {"from": "REJECTED", "to": "TO_PREPARE", "allowed": True},
                {"from": "REJECTED", "to": "CANCELLED", "allowed": True},
                {"from": "EXPIRED", "to": "TO_PREPARE", "allowed": True},
            ],
            "ok_conditions": [
                {"status": "ISSUED", "is_valid": True},
            ],
        },
        DocumentStatusModel.PROCESS_OSWIADCZENIE: {
            "statuses": {
                "NOT_REQUIRED": {"label": "Не требуется", "is_terminal": True},
                "TO_REGISTER": {"label": "К регистрации", "is_terminal": False},
                "REGISTERED": {"label": "Зарегистрировано", "is_terminal": False},
                "ACTIVE": {"label": "Активно", "is_terminal": False, "is_ok": True},
                "EXPIRED": {"label": "Истёк", "is_terminal": False},
                "REJECTED": {"label": "Отклонено", "is_terminal": False},
                "CANCELLED": {"label": "Отменено", "is_terminal": False},
            },
            "transitions": [
                {"from": "TO_REGISTER", "to": "REGISTERED", "allowed": True, "requires_fields": ["registered_at"]},
                {"from": "TO_REGISTER", "to": "REJECTED", "allowed": True},
                {"from": "TO_REGISTER", "to": "CANCELLED", "allowed": True},
                {"from": "REGISTERED", "to": "ACTIVE", "allowed": True, "requires_fields": ["valid_from", "valid_to"]},
                {"from": "REGISTERED", "to": "CANCELLED", "allowed": True},
                {"from": "ACTIVE", "to": "EXPIRED", "allowed": True, "auto": True},
                {"from": "ACTIVE", "to": "CANCELLED", "allowed": True},
                {"from": "REJECTED", "to": "TO_REGISTER", "allowed": True},
                {"from": "REJECTED", "to": "CANCELLED", "allowed": True},
                {"from": "EXPIRED", "to": "TO_REGISTER", "allowed": True},
            ],
            "ok_conditions": [
                {"status": "ACTIVE", "is_valid": True},
            ],
        },
        DocumentStatusModel.PROCESS_RESIDENCE: {
            "statuses": {
                "NOT_REQUIRED": {"label": "Не требуется", "is_terminal": True},
                "SUBMITTED": {"label": "Подано", "is_terminal": False},
                "IN_PROGRESS": {"label": "В процессе", "is_terminal": False},
                "ISSUED": {"label": "Выдано", "is_terminal": False, "is_ok": True},
                "REJECTED": {"label": "Отклонено", "is_terminal": False},
                "EXPIRED": {"label": "Истёк", "is_terminal": False},
                "CANCELLED": {"label": "Отменено", "is_terminal": False},
            },
            "transitions": [
                {"from": "SUBMITTED", "to": "IN_PROGRESS", "allowed": True},
                {"from": "SUBMITTED", "to": "CANCELLED", "allowed": True},
                {"from": "IN_PROGRESS", "to": "ISSUED", "allowed": True, "requires_fields": ["decision_at", "valid_to"]},
                {"from": "IN_PROGRESS", "to": "REJECTED", "allowed": True, "requires_fields": ["decision_at"]},
                {"from": "IN_PROGRESS", "to": "CANCELLED", "allowed": True},
                {"from": "ISSUED", "to": "EXPIRED", "allowed": True, "auto": True},
                {"from": "ISSUED", "to": "CANCELLED", "allowed": True},
                {"from": "REJECTED", "to": "SUBMITTED", "allowed": True},
                {"from": "REJECTED", "to": "CANCELLED", "allowed": True},
                {"from": "EXPIRED", "to": "SUBMITTED", "allowed": True},
            ],
            "ok_conditions": [
                {"status": "ISSUED", "is_valid": True},
            ],
        },
    }

    @classmethod
    async def get_status_model_for_document_type(
        cls, db: AsyncSession, tenant_id: str, document_type_id: str
    ) -> Optional[DocumentStatusModel]:
        """Получить статус-модель для типа документа."""
        stmt = (
            select(DocumentType)
            .where(DocumentType.id == document_type_id)
            .where(DocumentType.tenant_id == tenant_id)
        )
        doc_type = (await db.execute(stmt)).scalar_one_or_none()
        if doc_type and hasattr(doc_type, "status_model") and doc_type.status_model:
            return doc_type.status_model
        # Fallback: определяем по типу документа
        return cls._infer_status_model_from_doc_type(doc_type.code if doc_type else None)

    @classmethod
    async def get_status_model_for_document(
        cls, db: AsyncSession, document: Document
    ) -> DocumentStatusModel:
        """
        M3 runtime path:
        Resolve status model from canonical reference layer first,
        fallback to legacy doc_type inference.
        """
        try:
            resolved = await DocumentTypeRuntimeResolver.resolve_for_document(db, document)
            raw = str(resolved.status_model or "").strip()
            if raw:
                for candidate in DocumentStatusModel:
                    if candidate.value == raw:
                        return candidate
        except Exception:
            pass
        return cls._infer_status_model_from_doc_type(document.doc_type)

    @classmethod
    def _infer_status_model_from_doc_type(cls, doc_type_code: Optional[str]) -> DocumentStatusModel:
        """Определить статус-модель по коду типа документа."""
        if not doc_type_code:
            return DocumentStatusModel.EVIDENCE

        doc_type_upper = doc_type_code.upper()
        if doc_type_upper in ("WORK_PERMIT_A", "Zezwolenie typu A"):
            return DocumentStatusModel.PROCESS_WP_A
        elif doc_type_upper in ("EMPLOYER_STATEMENT_OSWIADCZENIE", "Oświadczenie"):
            return DocumentStatusModel.PROCESS_OSWIADCZENIE
        elif doc_type_upper in ("RESIDENCE_CARD", "Karta pobytu"):
            return DocumentStatusModel.PROCESS_RESIDENCE
        else:
            return DocumentStatusModel.EVIDENCE

    @classmethod
    def get_allowed_transitions(
        cls, status_model: DocumentStatusModel, from_status: str
    ) -> List[str]:
        """Получить список разрешённых переходов из текущего статуса."""
        model_config = cls.SYSTEM_STATUS_MODELS.get(status_model)
        if not model_config:
            return []

        transitions = model_config.get("transitions", [])
        allowed = [
            t["to"]
            for t in transitions
            if t.get("from") == from_status and t.get("allowed", False)
        ]
        return allowed

    @classmethod
    def is_transition_allowed(
        cls,
        status_model: DocumentStatusModel,
        from_status: str,
        to_status: str,
    ) -> bool:
        """Проверить, разрешён ли переход."""
        model_config = cls.SYSTEM_STATUS_MODELS.get(status_model)
        if not model_config:
            return False

        transitions = model_config.get("transitions", [])
        for transition in transitions:
            if (
                transition.get("from") == from_status
                and transition.get("to") == to_status
                and transition.get("allowed", False)
            ):
                return True
        return False

    @classmethod
    def validate_transition(
        cls,
        document: Document,
        to_status: str,
        status_model: Optional[DocumentStatusModel] = None,
    ) -> StatusValidationResult:
        """Валидировать переход статуса документа."""
        if not status_model:
            # Определяем статус-модель по типу документа
            status_model = cls._infer_status_model_from_doc_type(document.doc_type)

        from_status = document.status.value if hasattr(document.status, "value") else str(document.status)

        # Проверяем, разрешён ли переход
        if not cls.is_transition_allowed(status_model, from_status, to_status):
            return StatusValidationResult(
                valid=False,
                message=f"Переход из {from_status} в {to_status} не разрешён для статус-модели {status_model.value}",
            )

        # Получаем требования для перехода
        model_config = cls.SYSTEM_STATUS_MODELS.get(status_model)
        if not model_config:
            return StatusValidationResult(valid=True)

        transitions = model_config.get("transitions", [])
        transition = next(
            (
                t
                for t in transitions
                if t.get("from") == from_status and t.get("to") == to_status
            ),
            None,
        )

        if not transition:
            return StatusValidationResult(valid=True)

        # Проверяем обязательные поля
        required_fields = transition.get("requires_fields", [])
        missing_fields = []
        doc_meta = document.meta or {}

        for field in required_fields:
            if field == "submitted_at" and not hasattr(document, "submitted_at"):
                # Проверяем в meta или других полях
                if "submitted_at" not in doc_meta:
                    missing_fields.append(field)
            elif field == "decision_at" and "decision_at" not in doc_meta:
                missing_fields.append(field)
            elif field == "registered_at" and "registered_at" not in doc_meta:
                missing_fields.append(field)
            elif field in ("valid_from", "valid_to"):
                if not getattr(document, field, None):
                    missing_fields.append(field)
            elif field == "responsible_user_id" and not getattr(document, "owner_id", None):
                missing_fields.append(field)

        if missing_fields:
            return StatusValidationResult(
                valid=False,
                message=f"Отсутствуют обязательные поля: {', '.join(missing_fields)}",
                missing_fields=missing_fields,
            )

        return StatusValidationResult(valid=True)

    @classmethod
    def is_status_ok_for_gate(
        cls,
        document: Document,
        status_model: Optional[DocumentStatusModel] = None,
    ) -> bool:
        """Проверить, считается ли статус документа 'OK' для gates."""
        if not status_model:
            status_model = cls._infer_status_model_from_doc_type(document.doc_type)

        model_config = cls.SYSTEM_STATUS_MODELS.get(status_model)
        if not model_config:
            return False

        ok_conditions = model_config.get("ok_conditions", [])
        doc_status = document.status.value if hasattr(document.status, "value") else str(document.status)

        for condition in ok_conditions:
            required_status = condition.get("status", "").upper()
            require_valid = condition.get("is_valid", False)

            if doc_status.upper() != required_status:
                continue

            if require_valid:
                # Проверяем валидность (expire_date)
                if document.expire_date:
                    if document.expire_date < date.today():
                        continue
                # Если нет expire_date, считаем валидным если статус правильный
            return True

        return False

    @classmethod
    def check_auto_expire(cls, document: Document) -> Optional[str]:
        """Проверить, нужно ли автоматически перевести документ в EXPIRED."""
        status_model = cls._infer_status_model_from_doc_type(document.doc_type)
        model_config = cls.SYSTEM_STATUS_MODELS.get(status_model)
        if not model_config:
            return None

        doc_status = document.status.value if hasattr(document.status, "value") else str(document.status)

        # Проверяем, есть ли авто-переход в EXPIRED
        transitions = model_config.get("transitions", [])
        auto_expire_transition = next(
            (
                t
                for t in transitions
                if t.get("from") == doc_status
                and t.get("to") == "EXPIRED"
                and t.get("auto", False)
            ),
            None,
        )

        if not auto_expire_transition:
            return None

        # Проверяем, истёк ли срок
        if document.expire_date and document.expire_date < date.today():
            return "EXPIRED"

        return None


__all__ = [
    "StatusTransitionService",
    "StatusTransition",
    "StatusValidationResult",
]
