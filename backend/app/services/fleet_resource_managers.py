"""Batch queries and validation for fleet vehicle/driver ↔ CRM user managers."""

from __future__ import annotations

from collections import defaultdict
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.catalogs import user_label_expr
from backend.app.models.fleet_driver_manager import FleetDriverManager
from backend.app.models.fleet_vehicle_manager import FleetVehicleManager
from backend.app.models.tenant import user_memberships
from backend.app.models.user import User


async def user_can_be_fleet_manager(db: AsyncSession, tenant_id: str, user_id: str) -> bool:
    """Active user with tenant membership or primary tenant_id match."""
    base = await db.execute(
        select(User.id).where(
            User.id == user_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        ).limit(1)
    )
    if base.scalar_one_or_none() is None:
        return False
    m = await db.execute(
        select(user_memberships.c.user_id).where(
            user_memberships.c.user_id == user_id,
            user_memberships.c.tenant_id == tenant_id,
        ).limit(1)
    )
    if m.scalar_one_or_none() is not None:
        return True
    t = await db.execute(select(User.id).where(User.id == user_id, User.tenant_id == tenant_id).limit(1))
    return t.scalar_one_or_none() is not None


async def batch_vehicle_managers(
    db: AsyncSession, tenant_id: str, vehicle_ids: Sequence[str]
) -> dict[str, list[tuple[str, str, str]]]:
    """Map vehicle_id -> list of (membership_row_id, user_id, display_label)."""
    if not vehicle_ids:
        return {}
    res = await db.execute(
        select(
            FleetVehicleManager.id,
            FleetVehicleManager.vehicle_id,
            FleetVehicleManager.user_id,
            user_label_expr(),
        )
        .join(User, User.id == FleetVehicleManager.user_id)
        .where(
            FleetVehicleManager.tenant_id == tenant_id,
            FleetVehicleManager.vehicle_id.in_(list(vehicle_ids)),
        )
    )
    out: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for mid, vid, uid, label in res.all():
        lbl = (str(label).strip() if label is not None else "") or uid[:8]
        out[str(vid)].append((str(mid), str(uid), lbl))
    return dict(out)


async def batch_driver_managers(
    db: AsyncSession, tenant_id: str, driver_ids: Sequence[str]
) -> dict[str, list[tuple[str, str, str]]]:
    """Map fleet_driver_id -> list of (membership_row_id, user_id, display_label)."""
    if not driver_ids:
        return {}
    res = await db.execute(
        select(
            FleetDriverManager.id,
            FleetDriverManager.fleet_driver_id,
            FleetDriverManager.user_id,
            user_label_expr(),
        )
        .join(User, User.id == FleetDriverManager.user_id)
        .where(
            FleetDriverManager.tenant_id == tenant_id,
            FleetDriverManager.fleet_driver_id.in_(list(driver_ids)),
        )
    )
    out: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for mid, did, uid, label in res.all():
        lbl = (str(label).strip() if label is not None else "") or uid[:8]
        out[str(did)].append((str(mid), str(uid), lbl))
    return dict(out)
