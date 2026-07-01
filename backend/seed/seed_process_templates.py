"""Seed system process templates for document status models."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.process_template import ProcessTemplate
from backend.app.models.enums import DocumentStatusModel


async def seed_process_templates(db: AsyncSession, tenant_id: str) -> None:
    """Create system process templates for all status models."""
    
    # Проверяем, есть ли уже шаблоны для этого тенанта
    stmt = select(ProcessTemplate).where(
        ProcessTemplate.tenant_id == tenant_id,
        ProcessTemplate.is_system == True
    )
    existing = (await db.execute(stmt)).scalars().all()
    if existing:
        return  # Уже есть системные шаблоны

    from uuid import uuid4

    templates = [
        {
            "code": "TPL_EVIDENCE",
            "name": "Документы-доказательства",
            "description": "Шаблон для документов-доказательств (паспорт, права, тахо, świadectwo, карта квалификации)",
            "status_model": DocumentStatusModel.EVIDENCE,
            "config": {
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
                "auto_logic": {
                    "expire_on_valid_to": True,
                    "expire_status": "EXPIRED",
                    "is_valid_check": "valid_to >= today",
                },
            },
        },
        {
            "code": "TPL_WP_A",
            "name": "Work Permit A (Zezwolenie typu A)",
            "description": "Шаблон процесса для Work Permit A",
            "status_model": DocumentStatusModel.PROCESS_WP_A,
            "config": {
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
                "steps": [
                    {
                        "step_code": "PREPARE",
                        "name": "Подготовка",
                        "entry_status": "TO_PREPARE",
                        "required_fields": ["responsible_user_id"],
                        "optional_fields": ["case_number"],
                        "required_files": [],
                        "optional_files": ["APPLICATION_SET"],
                        "sla_days": 7,
                    },
                    {
                        "step_code": "SUBMIT",
                        "name": "Подача",
                        "entry_status": "SUBMITTED",
                        "required_fields": ["submitted_at"],
                        "required_files": ["SUBMISSION_CONFIRMATION"],
                        "sla_days": 3,
                        "auto_transition_from": "TO_PREPARE",
                    },
                    {
                        "step_code": "WAIT",
                        "name": "Ожидание",
                        "entry_status": "IN_PROGRESS",
                        "sla_days": 45,
                    },
                    {
                        "step_code": "DECISION",
                        "name": "Решение",
                        "entry_status": "ISSUED",
                        "required_fields": ["decision_at", "valid_from", "valid_to"],
                        "required_files": ["DECISION"],
                    },
                ],
                "auto_logic": {
                    "expire_on_valid_to": True,
                    "expire_status": "EXPIRED",
                },
            },
        },
        {
            "code": "TPL_OSW",
            "name": "Oświadczenie",
            "description": "Шаблон процесса для Oświadczenie o powierzeniu pracy cudzoziemcowi",
            "status_model": DocumentStatusModel.PROCESS_OSWIADCZENIE,
            "config": {
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
                "steps": [
                    {
                        "step_code": "PREPARE",
                        "name": "Подготовка",
                        "entry_status": "TO_REGISTER",
                        "required_fields": ["responsible_user_id"],
                        "sla_days": 3,
                    },
                    {
                        "step_code": "REGISTER",
                        "name": "Регистрация",
                        "entry_status": "REGISTERED",
                        "required_fields": ["registered_at"],
                        "required_files": ["REGISTRATION_CONFIRMATION"],
                    },
                    {
                        "step_code": "ACTIVATE",
                        "name": "Активация",
                        "entry_status": "ACTIVE",
                        "required_fields": ["valid_from", "valid_to"],
                        "required_files": ["DOCUMENT_COPY"],
                    },
                ],
                "auto_logic": {
                    "expire_on_valid_to": True,
                    "expire_status": "EXPIRED",
                },
            },
        },
        {
            "code": "TPL_RESIDENCE",
            "name": "Residence Card (Karta pobytu)",
            "description": "Шаблон процесса для Residence Card",
            "status_model": DocumentStatusModel.PROCESS_RESIDENCE,
            "config": {
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
                "auto_logic": {
                    "expire_on_valid_to": True,
                    "expire_status": "EXPIRED",
                },
            },
        },
    ]

    for template_data in templates:
        template = ProcessTemplate(
            id=str(uuid4()),
            tenant_id=tenant_id,
            code=template_data["code"],
            name=template_data["name"],
            description=template_data["description"],
            status_model=template_data["status_model"],
            config=template_data["config"],
            is_active=True,
            is_system=True,
            order=0,
        )
        db.add(template)

    await db.commit()


__all__ = ["seed_process_templates"]

