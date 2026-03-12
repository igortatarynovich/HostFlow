#!/usr/bin/env python3
"""Seed CE driver profile and attach to vacancy 807759e4-dbb7-4b7e-9a29-4219a97dab09."""

from __future__ import annotations

import asyncio
import os
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import async_session_maker
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.vacancy import Vacancy

VACANCY_ID = "807759e4-dbb7-4b7e-9a29-4219a97dab09"
PROFILE_CODE = "ce_driver"
PROFILE_NAME = "Водитель C+E"

# Anna's stages: Gotowy do przekazania, Procesowany przez zleceniodawcę,
# Złożono dokumenty na zezwolenie, Otrzymano zezwolenie, Zatrudnienie + handoff_returned
PROFILE_CONFIG = {
    "stage_codes": [
        "new",
        "no_answer",
        "contacted",
        "questionnaire_submitted",
        "docs_wait",
        "docs_got",
        "ready_for_handoff",  # Gotowy do przekazania — last before handoff
        "processing_by_client",  # Procesowany przez zleceniodawcę — first after handoff
        "docs_submitted_permit",  # Złożono dokumenty na zezwolenie
        "permit_received",  # Otrzymano zezwolenie
        "employed",  # Zatrudnienie
        "handoff_returned",  # Zwrócono
    ],
    "stage_labels": {
        "ready_for_handoff": {
            "pl": "Gotowy do przekazania",
            "ru": "Готов к передаче",
            "en": "Ready for handoff",
        },
        "processing_by_client": {
            "pl": "Procesowany przez zleceniodawcę",
            "ru": "Обработка заказчиком",
            "en": "Processed by client",
        },
        "docs_submitted_permit": {
            "pl": "Złożono dokumenty na zezwolenie",
            "ru": "Документы поданы на разрешение",
            "en": "Documents submitted for permit",
        },
        "permit_received": {
            "pl": "Otrzymano zezwolenie",
            "ru": "Разрешение получено",
            "en": "Permit received",
        },
        "employed": {
            "pl": "Zatrudnienie",
            "ru": "Трудоустройство",
            "en": "Employment",
        },
        "handoff_returned": {
            "pl": "Zwrócono",
            "ru": "Возвращён",
            "en": "Returned",
        },
    },
    "stage_columns": {
        "new": ["new", "no_answer"],
        "interview": ["contacted", "questionnaire_submitted", "docs_wait", "docs_got"],
        "ready": ["ready_for_handoff"],
        "client_process": ["processing_by_client", "docs_submitted_permit", "permit_received"],
        "employed": ["employed"],
        "returned": ["handoff_returned"],
    },
    "column_order": ["new", "interview", "ready", "client_process", "employed", "returned"],
}


async def run(db: AsyncSession) -> None:
    # Get vacancy to find tenant_id
    vac_row = await db.execute(
        select(Vacancy).where(Vacancy.id == VACANCY_ID)
    )
    vacancy = vac_row.scalar_one_or_none()
    if not vacancy:
        print(f"Vacancy {VACANCY_ID} not found. Skip.")
        return
    tenant_id = str(vacancy.tenant_id)
    print(f"Tenant: {tenant_id}")

    # Check if profile already exists
    existing = (
        await db.execute(
            select(CandidateProfile).where(
                CandidateProfile.tenant_id == tenant_id,
                CandidateProfile.code == PROFILE_CODE,
            )
        )
    ).scalar_one_or_none()

    if existing:
        profile = existing
        cfg = dict(profile.config or {})
        cfg.update(PROFILE_CONFIG)
        profile.config = cfg
        profile.name = PROFILE_NAME
        print(f"Updated existing profile {profile.id}")
    else:
        profile = CandidateProfile(
            id=str(uuid4()),
            tenant_id=tenant_id,
            code=PROFILE_CODE,
            name=PROFILE_NAME,
            description="Профиль водителей СЕ. Этапы согласованы с клиентом.",
            client_id=None,
            config=PROFILE_CONFIG,
            is_active=True,
            is_system=False,
            owner_user_id=None,
            notes="Drivers pipeline: handoff flow (Gotowy do przekazania → handoff → Procesowany przez zleceniodawcę → …)",
        )
        db.add(profile)
        await db.flush()
        print(f"Created profile {profile.id}")

    # Attach profile to vacancy
    await db.execute(
        update(Vacancy)
        .where(Vacancy.id == VACANCY_ID)
        .values(candidate_profile_id=profile.id)
    )
    print(f"Attached profile to vacancy {VACANCY_ID}")


async def main() -> None:
    async with async_session_maker() as db:
        await run(db)
        await db.commit()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
