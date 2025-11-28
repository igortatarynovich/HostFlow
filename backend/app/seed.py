from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

# Пример сидера под async-сессию.
# Если у тебя есть реальные модели и данные для сидинга — добавь тут.
# В app.main сидирование auth идёт отдельными ensure_* файлами.


async def run_seed(db: AsyncSession) -> None:
    # Добавь свои сиды здесь (пример):
    # from backend.app.models import Tenant
    # exists = await db.scalar(select(func.count()).select_from(Tenant))
    # if not exists:
    #     db.add(Tenant(name="Default"))
    #     await db.commit()
    return
