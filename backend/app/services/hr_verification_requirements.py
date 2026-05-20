"""Role/position-based required fields for HR data verification (transport vs non-transport)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.hr_verified_field_catalog import BASE_CRITICAL_FIELD_CODES

# Extra fields required when work eligibility position_category is driver.
DRIVER_POSITION_CRITICAL_FIELD_CODES: frozenset[str] = frozenset(
    {
        "driver_license_number",
        "driver_license_categories",
        "driver_license_expiry",
        "code95_number",
        "code95_expiry",
        "tacho_card_number",
        "tacho_card_expiry",
        "exam_valid_until",
    }
)

_DRIVER_ROLE_ALIASES = frozenset({"driver", "kierowca", "kierowca_ce", "truck_driver"})


def normalize_position_category(raw: Any) -> Optional[str]:
    v = str(raw or "").strip().lower()
    return v or None


def is_driver_position(position_category: Optional[str]) -> bool:
    return normalize_position_category(position_category) == "driver"


def resolve_critical_field_codes(position_category: Optional[str]) -> frozenset[str]:
    """Union of base employment fields + transport/compliance fields for drivers."""
    codes = set(BASE_CRITICAL_FIELD_CODES)
    if is_driver_position(position_category):
        codes |= DRIVER_POSITION_CRITICAL_FIELD_CODES
    return frozenset(codes)


def _position_from_mapping(data: Any) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    for key in ("position_category", "positionCategory", "position_type"):
        if data.get(key):
            return normalize_position_category(data.get(key))
    role = normalize_position_category(data.get("role"))
    if role in _DRIVER_ROLE_ALIASES:
        return "driver"
    return None


async def resolve_position_category_for_review(
    db: AsyncSession,
    tenant_id: str,
    *,
    employee_id: Optional[str] = None,
    candidate_id: Optional[str] = None,
) -> Optional[str]:
    """Best-effort position category for HR verification policy."""
    eid = str(employee_id or "").strip()
    if eid:
        from backend.app.services import workforce_employees as we_svc

        bundle = await we_svc.get_hr_bundle(db, tenant_id, eid)
        wel = bundle.get("work_eligibility_profile")
        if wel is not None:
            pc = normalize_position_category(getattr(wel, "position_category", None))
            if pc:
                return pc
        emp = bundle.get("employee")
        if emp is None:
            emp = await we_svc.get_employee(db, tenant_id, eid)
        if emp is not None:
            meta_pc = _position_from_mapping(emp.meta if isinstance(emp.meta, dict) else None)
            if meta_pc:
                return meta_pc
            snap_pc = _position_from_mapping(
                emp.candidate_snapshot if isinstance(emp.candidate_snapshot, dict) else None
            )
            if snap_pc:
                return snap_pc
            if emp.candidate_id and not candidate_id:
                candidate_id = str(emp.candidate_id)

    cid = str(candidate_id or "").strip()
    if cid:
        from backend.app.models.candidate import Candidate

        cand = await db.get(Candidate, cid)
        if cand is not None:
            extra_pc = _position_from_mapping(cand._get_extra())
            if extra_pc:
                return extra_pc
            personal_pc = _position_from_mapping(cand._get_personal_data())
            if personal_pc:
                return personal_pc
    return None
