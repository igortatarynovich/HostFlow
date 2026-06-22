from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.models.tenant import Tenant


async def run_seed(db: AsyncSession) -> None:
    """Run all seed functions for the application."""
    import logging
    logger = logging.getLogger(__name__)
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
            try:
                await db.rollback()
            except Exception:
                pass
            logger.debug(f"[seed] Stages seed skipped: {e}")

        # Seed process templates
        try:
            from seed.seed_process_templates import seed_process_templates
            await seed_process_templates(db, tenant_id)
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(f"[seed] Failed to seed process templates for tenant {tenant_id}: {e}")

        # Seed requirements and gates
        try:
            from seed.seed_requirements_and_gates import seed_requirements_and_gates
            await seed_requirements_and_gates(db, tenant_id)
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(f"[seed] Failed to seed requirements and gates for tenant {tenant_id}: {e}")

        # Seed driver_ce_default profile and assign to vacancies without profile
        try:
            from backend.app.seed_candidate_profiles import (
                cleanup_legacy_base_candidate_profile,
                ensure_driver_ce_default_profile,
            )
            await ensure_driver_ce_default_profile(db, tenant_id)
            await cleanup_legacy_base_candidate_profile(db, tenant_id)
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(f"[seed] Failed to reconcile default candidate profile for tenant {tenant_id}: {e}")

        # Process Engine P1 — recruitment registry defaults
        try:
            from backend.app.process_engine.seed import ensure_recruitment_process_engine_defaults

            await ensure_recruitment_process_engine_defaults(db, tenant_id)
            await db.commit()
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(f"[seed] Failed to seed Process Engine defaults for tenant {tenant_id}: {e}")

        # Field Registry P1 — canonical fields + default card layouts
        try:
            from backend.app.field_registry.seed import ensure_tenant_field_registry_defaults

            await ensure_tenant_field_registry_defaults(db, tenant_id)
            await db.commit()
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(f"[seed] Failed to seed Field Registry defaults for tenant {tenant_id}: {e}")

        # Entity Profile Definition Registry P1 — composition layer over Field Registry
        try:
            from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults

            await ensure_tenant_entity_profile_defaults(db, tenant_id)
            await db.commit()
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(f"[seed] Failed to seed Entity Profile defaults for tenant {tenant_id}: {e}")

        # P6 — default driver_ce public intake form + intake source binding
        try:
            from backend.app.entity_profile.seed_intake_demo_form import ensure_tenant_default_driver_ce_intake_form

            await ensure_tenant_default_driver_ce_intake_form(db, tenant_id)
            await db.commit()
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(f"[seed] Failed to seed default driver_ce intake form for tenant {tenant_id}: {e}")

        # Module Registry P1 — canonical module catalog + tenant installation rows
        try:
            from backend.app.module_registry.seed import ensure_tenant_module_installations

            await ensure_tenant_module_installations(db, tenant_id)
            await db.commit()
        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(f"[seed] Failed to seed Module Registry defaults for tenant {tenant_id}: {e}")
