from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.stage import Stage

STAGES: Sequence[tuple[str, str, int, bool, bool, bool, bool]] = [
    ("new", "Новый", 10, False, False, False, False),
    ("contacted", "Контакт установлен", 20, False, False, False, False),
    ("docs_wait", "Ожидаем документы", 30, False, False, False, False),
    ("docs_got", "Документы получены", 40, False, False, False, False),
    ("permit_ordered", "Заказ разрешения на работу", 50, True, False, False, False),
    ("permit_got", "Разрешение на работу получено", 60, True, False, False, False),
    ("visa", "Виза", 70, False, True, False, False),
    ("red_paper_ordered", "Красная бумага заказана", 80, False, False, True, False),
    ("arrival_planned", "Планируем приезд", 90, False, False, False, False),
    ("on_client_base", "На базе клиента", 100, False, False, False, False),
    ("left_to_trip", "Выехал в рейс", 110, False, False, False, False),
    ("probation_passed", "Прошел пробный период", 120, False, False, False, False),
    ("employed", "Трудоустроен", 130, False, False, False, True),
    ("rejected", "Отклонён", 140, False, False, False, True),
]


async def seed_stages(db: AsyncSession) -> None:
    # если таблица пуста — добавим
    existing = (await db.execute(select(Stage))).scalars().all()
    if existing:
        return
    now = datetime.now(timezone.utc)
    for code, label, sort, need_permit, need_visa, need_red, terminal in STAGES:
        db.add(
            Stage(
                code=code,
                label=label,
                sort=sort,
                need_work_permit=need_permit,
                need_visa=need_visa,
                need_red_paper=need_red,
                is_terminal=terminal,
                created_at=now,
                updated_at=None,
            )
        )
    await db.commit()
