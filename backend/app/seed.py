from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.models.tenant import Tenant


async def run_seed(db: AsyncSession) -> None:
    """Run all seed functions for the application."""
    # Получаем все активные тенанты
    stmt = select(Tenant).where(Tenant.is_active == True)
    tenants = (await db.execute(stmt)).scalars().all()

    if not tenants:
        return  # Нет тенантов для seed

    # Seed для каждого тенанта
    for tenant in tenants:
        tenant_id = tenant.id

        # Seed stages (опционально, если модуль доступен)
        try:
            import importlib.util
            from pathlib import Path
            seed_path = Path(__file__).parent.parent.parent / "seed" / "1seed_stages.py"
            if seed_path.exists():
                spec = importlib.util.spec_from_file_location("seed_stages", seed_path)
                if spec and spec.loader:
                    seed_stages_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(seed_stages_module)
                    await seed_stages_module.seed_stages(db)  # type: ignore
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"[seed] Stages seed skipped: {e}")

        # Seed process templates
        try:
            from seed.seed_process_templates import seed_process_templates
            await seed_process_templates(db, tenant_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[seed] Failed to seed process templates for tenant {tenant_id}: {e}")

        # Seed requirements and gates
        try:
            from seed.seed_requirements_and_gates import seed_requirements_and_gates
            await seed_requirements_and_gates(db, tenant_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[seed] Failed to seed requirements and gates for tenant {tenant_id}: {e}")

        # Seed base candidate profile
        try:
            from backend.app.seed_candidate_profiles import ensure_base_candidate_profile
            await ensure_base_candidate_profile(db, tenant_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[seed] Failed to seed base candidate profile for tenant {tenant_id}: {e}")

        # Seed driver_ce_default profile and assign to vacancies without profile
        try:
            from backend.app.seed_candidate_profiles import ensure_driver_ce_default_profile
            await ensure_driver_ce_default_profile(db, tenant_id)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[seed] Failed to seed driver_ce_default profile for tenant {tenant_id}: {e}")
