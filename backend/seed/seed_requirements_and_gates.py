"""Seed system requirement types and gates."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.requirement_type import RequirementTypeDefinition
from backend.app.models.gate import Gate
from backend.app.models.enums import RequirementType, GateCode


async def seed_requirements_and_gates(db: AsyncSession, tenant_id: str) -> None:
    """Create system requirement types and gates."""
    
    from uuid import uuid4

    # 1. Create requirement type definitions
    stmt_req = select(RequirementTypeDefinition).where(
        RequirementTypeDefinition.tenant_id == tenant_id,
        RequirementTypeDefinition.is_active == True
    )
    existing_reqs = (await db.execute(stmt_req)).scalars().all()
    existing_req_codes = {req.requirement_code for req in existing_reqs}

    requirements = [
        {
            "requirement_code": RequirementType.ID_EVIDENCE,
            "name": "Документ удостоверения личности",
            "description": "Требование наличия валидного документа удостоверения личности (паспорт)",
            "satisfaction_rules": {
                "satisfied_by_any": [
                    {
                        "document_type": "PASSPORT",
                        "status": ["VERIFIED"],
                        "valid": True,
                    }
                ]
            },
        },
        {
            "requirement_code": RequirementType.CODE95_EVIDENCE,
            "name": "Доказательство Code 95",
            "description": "Требование наличия доказательства Code 95 (карта квалификации или отметка в правах)",
            "satisfaction_rules": {
                "satisfied_by_any": [
                    {
                        "document_type": "DRIVERS_QUALIFICATION_CARD",
                        "status": ["VERIFIED"],
                        "valid": True,
                    },
                    {
                        "document_type": "DRIVING_LICENSE_CE",
                        "status": ["VERIFIED"],
                        "valid": True,
                        "meta": {"code95": True},
                    }
                ]
            },
        },
        {
            "requirement_code": RequirementType.RIGHT_TO_WORK_BASIS,
            "name": "Право работать",
            "description": "Требование наличия валидного основания для работы в Польше",
            "satisfaction_rules": {
                "satisfied_by_any": [
                    {
                        "document_type": "WORK_PERMIT_A",
                        "status": ["ISSUED"],
                        "valid": True,
                    },
                    {
                        "document_type": "EMPLOYER_STATEMENT_OSWIADCZENIE",
                        "status": ["ACTIVE"],
                        "valid": True,
                    },
                    {
                        "document_type": "RESIDENCE_CARD",
                        "status": ["ISSUED"],
                        "valid": True,
                    },
                ]
            },
        },
        {
            "requirement_code": RequirementType.CORE_PRO_DRIVER_SET,
            "name": "Базовый проф-набор для рейса",
            "description": "Базовый набор профессиональных документов для выезда в рейс",
            "satisfaction_rules": {
                "satisfied_by_all": [
                    {
                        "document_type": "DRIVING_LICENSE_CE",
                        "status": ["VERIFIED"],
                        "valid": True,
                    },
                    {
                        "document_type": "TACHOGRAPH_CARD",
                        "status": ["VERIFIED"],
                        "valid": True,
                    },
                    {
                        "requirement_code": "CODE95_EVIDENCE",
                    }
                ]
            },
        },
        {
            "requirement_code": RequirementType.DRIVERS_CERTIFICATE_IF_REQUIRED,
            "name": "Świadectwo kierowcy (если требуется)",
            "description": "Свидетельство водителя, если требуется клиентом/вакансией",
            "satisfaction_rules": {
                "satisfied_by_any": [
                    {
                        "document_type": "DRIVERS_CERTIFICATE",
                        "status": ["VERIFIED"],
                        "valid": True,
                    }
                ]
            },
        },
    ]

    for req_data in requirements:
        if req_data["requirement_code"] not in existing_req_codes:
            req = RequirementTypeDefinition(
                id=str(uuid4()),
                tenant_id=tenant_id,
                requirement_code=req_data["requirement_code"],
                name=req_data["name"],
                description=req_data["description"],
                satisfaction_rules=req_data["satisfaction_rules"],
                is_active=True,
            )
            db.add(req)

    # 2. Create gates
    stmt_gates = select(Gate).where(
        Gate.tenant_id == tenant_id,
        Gate.is_active == True
    )
    existing_gates = (await db.execute(stmt_gates)).scalars().all()
    existing_gate_codes = {gate.gate_code for gate in existing_gates}

    gates = [
        {
            "gate_code": GateCode.GATE_DOCS_RECEIVED,
            "name": "Документы получены",
            "description": "Блокировка этапа 'Документы получены'",
            "blocks_stage": "Документы получены",
            "order": 1,
        },
        {
            "gate_code": GateCode.GATE_PLAN_ARRIVAL,
            "name": "Планируем приезд",
            "description": "Блокировка этапа 'Планируем приезд'",
            "blocks_stage": "Планируем приезд",
            "order": 2,
        },
        {
            "gate_code": GateCode.GATE_ON_CLIENT_BASE,
            "name": "На базе клиента",
            "description": "Блокировка этапа 'На базе клиента'",
            "blocks_stage": "На базе клиента",
            "order": 3,
        },
        {
            "gate_code": GateCode.GATE_ON_ROUTE,
            "name": "Выехал в рейс",
            "description": "Блокировка этапа 'Выехал в рейс'",
            "blocks_stage": "Выехал в рейс",
            "order": 4,
        },
    ]

    for gate_data in gates:
        if gate_data["gate_code"] not in existing_gate_codes:
            gate = Gate(
                id=str(uuid4()),
                tenant_id=tenant_id,
                gate_code=gate_data["gate_code"],
                name=gate_data["name"],
                description=gate_data["description"],
                blocks_stage=gate_data["blocks_stage"],
                is_active=True,
                order=gate_data["order"],
            )
            db.add(gate)

    await db.commit()


__all__ = ["seed_requirements_and_gates"]

