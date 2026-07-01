"""Service for checking candidate profile field limits based on tenant subscription."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.tenant import TenantLicense


# Field type categories
FIELD_CATEGORIES: Dict[str, str] = {
    # System fields (always available, don't count)
    "first_name": "system",
    "last_name": "system",
    "email": "system",
    "phone": "system",
    
    # Simple fields (basic)
    "text": "simple",
    "textarea": "simple",
    "number": "simple",
    "date": "simple",
    "checkbox": "simple",
    
    # Medium fields
    "select": "medium",
    "multiselect": "medium",
    "address": "medium",
    
    # Resource-intensive fields
    "file": "resource",
    "image": "resource",
    "signature": "resource",
    "employment_history": "resource",
}

# Plan limits: (simple_max, medium_max, resource_max, total_custom_fields_max)
PLAN_LIMITS: Dict[str, tuple[int, int, int, int]] = {
    "free": (2, 0, 0, 2),  # 2 простых поля, всего 2 кастомных
    "trial": (5, 2, 1, 5),  # 5 простых, 2 средних, 1 ресурсоемкое, всего 5
    "basic": (10, 5, 2, 10),  # 10 простых, 5 средних, 2 ресурсоемких, всего 10
    "pro": (15, 8, 5, 30),  # 15 простых, 8 средних, 5 ресурсоемких, всего 30
    "scale": (999999, 999999, 999999, 999999),  # Unlimited
    "enterprise": (999999, 999999, 999999, 999999),  # Unlimited
}


def get_field_category(field_type: str) -> str:
    """Get category for a field type."""
    return FIELD_CATEGORIES.get(field_type.lower(), "simple")  # Default to simple if unknown


def get_plan_limits(plan: Optional[str]) -> tuple[int, int, int, int]:
    """Get field limits for a plan: (simple_max, medium_max, resource_max, total_custom_max)."""
    if not plan:
        return PLAN_LIMITS.get("free", (2, 0, 0, 2))
    plan_lower = plan.lower()
    return PLAN_LIMITS.get(plan_lower, PLAN_LIMITS.get("free", (2, 0, 0, 2)))


def calculate_field_counts(config: Dict[str, Any]) -> tuple[int, int, int, int]:
    """Calculate field counts by category in a profile config.
    
    Returns: (simple_count, medium_count, resource_count, total_custom_count)
    
    Config format:
    {
        "field_configs": [
            {"field_key": "first_name", "field_type": "text", "required": true, "order": 1},
            {"field_key": "custom_field_1", "field_type": "textarea", "required": false, "order": 2},
            ...
        ]
    }
    """
    simple_count = 0
    medium_count = 0
    resource_count = 0
    total_custom = 0
    
    field_configs = config.get("field_configs", [])
    
    for field_config in field_configs:
        field_type = field_config.get("field_type", "text")
        field_key = field_config.get("field_key", "")
        
        # System fields don't count
        if field_key in ["first_name", "last_name", "email", "phone"]:
            continue
        
        category = get_field_category(field_type)
        total_custom += 1
        
        if category == "simple":
            simple_count += 1
        elif category == "medium":
            medium_count += 1
        elif category == "resource":
            resource_count += 1
    
    return (simple_count, medium_count, resource_count, total_custom)


async def get_tenant_plan(db: AsyncSession, tenant_id: str) -> Optional[str]:
    """Get tenant's subscription plan."""
    from backend.app.models.tenant import TenantLicense
    
    stmt = select(TenantLicense).where(TenantLicense.tenant_id == tenant_id)
    result = await db.execute(stmt)
    license = result.scalar_one_or_none()
    
    if not license:
        return None
    
    return license.plan


async def check_profile_limit(
    db: AsyncSession,
    tenant_id: str,
    config: Dict[str, Any],
    exclude_profile_id: Optional[str] = None,
) -> tuple[bool, Dict[str, Any], str]:
    """Check if profile config exceeds tenant's limits.
    
    Returns:
        (is_valid, limits_info, plan_name)
        limits_info: {
            "simple": {"used": int, "limit": int},
            "medium": {"used": int, "limit": int},
            "resource": {"used": int, "limit": int},
            "total_custom": {"used": int, "limit": int}
        }
    """
    plan = await get_tenant_plan(db, tenant_id)
    simple_limit, medium_limit, resource_limit, total_custom_limit = get_plan_limits(plan)
    
    # Calculate counts for this profile
    profile_simple, profile_medium, profile_resource, profile_total = calculate_field_counts(config)
    
    total_simple, total_medium, total_resource, total_custom = await get_tenant_profile_usage_counts(
        db,
        tenant_id,
        exclude_profile_id=exclude_profile_id,
    )
    
    # Add current profile counts
    total_simple += profile_simple
    total_medium += profile_medium
    total_resource += profile_resource
    total_custom += profile_total
    
    limits_info = {
        "simple": {"used": total_simple, "limit": simple_limit},
        "medium": {"used": total_medium, "limit": medium_limit},
        "resource": {"used": total_resource, "limit": resource_limit},
        "total_custom": {"used": total_custom, "limit": total_custom_limit},
    }
    
    is_valid = (
        total_simple <= simple_limit
        and total_medium <= medium_limit
        and total_resource <= resource_limit
        and total_custom <= total_custom_limit
    )
    
    plan_name = plan or "free"
    
    return (is_valid, limits_info, plan_name)


async def get_tenant_profile_usage_counts(
    db: AsyncSession,
    tenant_id: str,
    *,
    exclude_profile_id: Optional[str] = None,
) -> tuple[int, int, int, int]:
    """Return aggregate usage counts for tenant-scoped custom profiles.

    System profiles are seeded by the platform and must not consume tenant plan
    budget, otherwise a single default template can block all custom profile
    creation for paid tenants.
    """
    stmt = select(CandidateProfile).where(
        CandidateProfile.tenant_id == tenant_id,
        CandidateProfile.is_active == True,
        CandidateProfile.is_system == False,
    )
    if exclude_profile_id:
        stmt = stmt.where(CandidateProfile.id != exclude_profile_id)

    result = await db.execute(stmt)
    profiles = result.scalars().all()

    total_simple = 0
    total_medium = 0
    total_resource = 0
    total_custom = 0
    for profile in profiles:
        s, m, r, t = calculate_field_counts(profile.config or {})
        total_simple += s
        total_medium += m
        total_resource += r
        total_custom += t

    return (total_simple, total_medium, total_resource, total_custom)


def get_field_type_label(field_type: str) -> str:
    """Get human-readable label for field type."""
    labels = {
        "text": "Текстовое поле",
        "textarea": "Многострочный текст",
        "number": "Число",
        "date": "Дата",
        "checkbox": "Чекбокс",
        "select": "Выпадающий список",
        "multiselect": "Множественный выбор",
        "file": "Файл",
        "image": "Изображение",
        "signature": "Подпись",
        "employment_history": "История трудоустройства",
        "address": "Адрес",
    }
    return labels.get(field_type.lower(), field_type)


__all__ = [
    "get_field_category",
    "get_plan_limits",
    "calculate_field_counts",
    "get_tenant_plan",
    "check_profile_limit",
    "get_tenant_profile_usage_counts",
    "get_field_type_label",
    "FIELD_CATEGORIES",
    "PLAN_LIMITS",
]
