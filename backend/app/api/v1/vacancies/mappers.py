import json
from datetime import datetime
from typing import Any, Dict, Optional
from backend.app.models import Vacancy
from backend.app.models.vacancy import EmploymentType
from .schemas import VacancyOut

_EMPLOYMENT_VALUES = {et.value for et in EmploymentType}

def _loads_extra(extra: Optional[str]) -> Dict[str, Any]:
    if not extra:
        return {}
    try:
        return json.loads(extra)
    except Exception:
        return {}

def vacancy_to_out(v: Vacancy, *, company_name: Optional[str] = None,
                   manager_short: Optional[str] = None,
                   manager_name: Optional[str] = None,
                   candidate_profile_id: Optional[str] = None,
                   candidate_profile_name: Optional[str] = None,
                   candidate_count: Optional[int] = None,
                   last_candidate_activity_at: Optional[datetime] = None) -> VacancyOut:
    employment_raw = getattr(v, "employment_type", None)
    if isinstance(employment_raw, EmploymentType):
        employment_value = employment_raw.value
    else:
        employment_value = (employment_raw or EmploymentType.full_time.value)
        if employment_value not in _EMPLOYMENT_VALUES:
            employment_value = EmploymentType.full_time.value

    # Get candidate_profile_id from vacancy if not provided
    profile_id = candidate_profile_id or getattr(v, "candidate_profile_id", None)

    return VacancyOut(
        id=v.id,
        tenant_id=v.tenant_id,
        company_id=v.company_id,
        title=v.title,
        description=v.description,
        location=v.location,
        salary_from=v.salary_from,
        salary_to=v.salary_to,
        currency=v.currency,
        status=v.status,
        is_open=getattr(v, "is_open", None),
        is_active=getattr(v, "is_active", None),
        is_archived=getattr(v, "is_archived", None),
        manager=v.manager,
        candidate_profile_id=str(profile_id) if profile_id else None,
        candidate_profile_name=candidate_profile_name,
        required_documents_template_id=getattr(v, "required_documents_template_id", None),
        extra=_loads_extra(v.extra),
        employment_type=employment_value,
        created_at=getattr(v, "created_at", None),
        updated_at=getattr(v, "updated_at", None),
        company_name=company_name,
        manager_short=manager_short,
        manager_name=manager_name,
        candidate_count=candidate_count or 0,
        last_candidate_activity_at=last_candidate_activity_at,
        headcount_target=getattr(v, "headcount_target", None),
        order_line_id=getattr(v, "order_line_id", None),
        funnel_id=str(getattr(v, "funnel_id", None) or "") or None,
    )
