import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4
from backend.app.api.v1.candidates.acl import CandidateACL
from .repo import VacancyRepo
from .schemas import VacancyIn, VacancyOut, VacancyPatch
from .mappers import vacancy_to_out
from .rules import validate_status_transition

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _to_str_or_none(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, Enum):
        return v.value
    s = str(v).strip()
    return s or None

class VacancyService:
    def __init__(self, repo: VacancyRepo) -> None:
        self.repo = repo

    async def list(
        self,
        *,
        company_id: Optional[str],
        status: Optional[str],
        search: Optional[str],
        limit: int,
        offset: int,
        order_by: Optional[str],
        descending: bool,
        acl: CandidateACL | None = None,
    ) -> List[VacancyOut]:
        allowed_company_ids = None
        allowed_vacancy_ids = None
        if acl is not None:
            allowed_company_ids = set(acl.company_ids)
            allowed_vacancy_ids = set(acl.vacancy_ids)

        rows = await self.repo.list(
            company_id=company_id,
            status=status,
            search=search,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending,
            allowed_company_ids=allowed_company_ids,
            allowed_vacancy_ids=allowed_vacancy_ids,
        )
        return [vacancy_to_out(v, company_name=company_name, candidate_count=cand_count)
                for (v, company_name, cand_count) in rows]

    async def get(self, vacancy_id: str) -> VacancyOut:
        obj = await self.repo.get(vacancy_id)
        if not obj:
            raise LookupError("Vacancy not found")
        return vacancy_to_out(obj)

    async def create(self, tenant_id: str, payload: VacancyIn) -> VacancyOut:
        values: Dict[str, Any] = {
            "id": str(uuid4()),
            "tenant_id": tenant_id,
            "company_id": str(payload.company_id),
            "title": payload.title,
            "description": payload.description,
            "location": payload.location,
            "employment_type": _to_str_or_none(payload.employment_type) or "full_time",
            "salary_from": _to_str_or_none(payload.salary_from),
            "salary_to": _to_str_or_none(payload.salary_to),
            "currency": _to_str_or_none(payload.currency) or "EUR",
            "status": payload.status or "open",
            "manager": str(payload.manager) if payload.manager else None,
            "extra": json.dumps(payload.extra, ensure_ascii=False),
        }
        obj = await self.repo.create(values)
        return vacancy_to_out(obj)

    async def patch(self, vacancy_id: str, payload: VacancyPatch) -> VacancyOut:
        obj = await self.repo.get(vacancy_id)
        if not obj:
            raise LookupError("Vacancy not found")

        values: Dict[str, Any] = {}
        for f in ["title", "description", "location"]:
            v = getattr(payload, f)
            if v is not None:
                values[f] = v

        def _pick(*names):
            for n in names:
                v = getattr(payload, n)
                if v is not None:
                    return v
            return None

        salary_from_val = _pick("salary_from", "salary_from_alt1", "salary_from_alt2")
        if isinstance(salary_from_val, str) and not salary_from_val.strip():
            salary_from_val = None
        if salary_from_val is not None:
            values["salary_from"] = _to_str_or_none(salary_from_val)

        salary_to_val = _pick("salary_to", "salary_to_alt1", "salary_to_alt2")
        if isinstance(salary_to_val, str) and not salary_to_val.strip():
            salary_to_val = None
        if salary_to_val is not None:
            values["salary_to"] = _to_str_or_none(salary_to_val)

        currency_val = _pick("currency", "currency_alt1", "currency_alt2")
        if isinstance(currency_val, str) and not currency_val.strip():
            currency_val = None
        if currency_val is not None:
            values["currency"] = _to_str_or_none(currency_val)

        status_val = _pick("status", "status_alt1", "status_alt2")
        if status_val is not None:
            validate_status_transition(getattr(obj, "status", "new"), status_val)
            values["status"] = status_val
            normalized_status = str(status_val).strip().lower()
            if payload.is_archived is None:
                if normalized_status == "archived":
                    values["is_archived"] = True
                    values.setdefault("is_active", False)
                else:
                    values["is_archived"] = False
                    values.setdefault("is_active", True)

        stage_val = getattr(payload, "stage", None)
        if stage_val is not None:
            values["stage"] = stage_val

        if payload.manager is not None:
            values["manager"] = str(payload.manager) if payload.manager else None

        if payload.extra is not None:
            values["extra"] = json.dumps(payload.extra, ensure_ascii=False)

        if payload.employment_type is not None:
            values["employment_type"] = _to_str_or_none(payload.employment_type)

        if payload.company_id is not None:
            values["company_id"] = str(payload.company_id) if payload.company_id else None

        if payload.is_archived is not None:
            archived_flag = bool(payload.is_archived)
            values["is_archived"] = archived_flag
            if archived_flag:
                values.setdefault("is_active", False)
                values.setdefault("status", "archived")
            else:
                values.setdefault("is_active", True)
                values.setdefault("status", getattr(obj, "status", "open") or "open")

        if payload.is_active is not None:
            values["is_active"] = bool(payload.is_active)

        if payload.is_open is not None:
            open_flag = bool(payload.is_open)
            values["is_active"] = open_flag
            values["is_archived"] = not open_flag
            values["status"] = "open" if open_flag else "closed"

        if values:
            values["updated_at"] = _now_utc()
            obj = await self.repo.update(obj, values)

        return vacancy_to_out(obj)

    async def delete(self, vacancy_id: str) -> None:
        obj = await self.repo.get(vacancy_id)
        if not obj:
            raise LookupError("Vacancy not found")
        if await self.repo.has_linked_candidates(obj.id):
            raise ValueError("Cannot delete vacancy with linked candidates")
        await self.repo.delete(obj)
