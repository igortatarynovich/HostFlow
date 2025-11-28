from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, List, Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

try:  # Pydantic v2
    from pydantic import BaseModel, Field, field_validator

    def _model_validate(model: BaseModel.__class__, data: Any) -> BaseModel:
        return model.model_validate(data)

    def _model_dump(model: BaseModel, *, exclude_unset: bool = False) -> dict[str, Any]:
        return model.model_dump(exclude_unset=exclude_unset)

    _ORM_MODE_CONFIG = {"model_config": {"from_attributes": True}}
except ImportError:  # pragma: no cover - Pydantic v1 fallback
    from pydantic import BaseModel, Field, validator

    def field_validator(*fields, **kwargs):  # type: ignore[misc]
        decorator = validator(*fields, **kwargs)

        def _wrapper(func):
            if isinstance(func, classmethod):
                func = func.__func__  # type: ignore[attr-defined]
            return decorator(func)

        return _wrapper

    def _model_validate(model: BaseModel.__class__, data: Any) -> BaseModel:
        return model.from_orm(data)

    def _model_dump(model: BaseModel, *, exclude_unset: bool = False) -> dict[str, Any]:
        return model.dict(exclude_unset=exclude_unset)

    _ORM_MODE_CONFIG = {"Config": type("Config", (), {"orm_mode": True})}  # type: ignore[misc]

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.deps import Role, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.models.candidate_employment import CandidateEmployment
from backend.app.services import candidate_employments as employment_service


router = APIRouter(prefix="/candidates", tags=["candidate-employments"])

MAX_EMPLOYMENTS_PER_CANDIDATE = 3


def _clean_list(values: Optional[Iterable[str]], *, allow_none: bool = False) -> Optional[list[str]]:
    if values is None:
        return None if allow_none else []
    cleaned = []
    for value in values:
        item = (value or "").strip()
        if item:
            cleaned.append(item)
    return cleaned if cleaned or allow_none else ([] if not allow_none else [])


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


class EmploymentBase(BaseModel):
    employer_name: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(
        default=None,
        description="ISO-2 country code",
        min_length=2,
        max_length=2,
    )
    position: Optional[str] = Field(default=None, max_length=255)
    start_date: date
    end_date: Optional[date] = None
    trailer_types: List[str] = Field(default_factory=list)
    route_types: List[str] = Field(default_factory=list)
    truck_brands: Optional[List[str]] = Field(default=None)
    eu_routes: Optional[bool] = None
    reason_for_leaving: Optional[str] = None
    reference_contact: Optional[str] = None

    @field_validator("employer_name")
    @classmethod
    def _trim_employer(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("employer_name must not be empty")
        return cleaned

    @field_validator("country")
    @classmethod
    def _normalize_country(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        code = value.strip().upper()
        if not code:
            return None
        if len(code) != 2:
            raise ValueError("country must be a 2-letter ISO code")
        return code

    @field_validator("trailer_types", "route_types")
    @classmethod
    def _normalize_lists(cls, value: Optional[Iterable[str]]) -> List[str]:
        if value is None:
            return []
        return [item.strip() for item in value if str(item).strip()]

    @field_validator("truck_brands")
    @classmethod
    def _normalize_trucks(cls, value: Optional[Iterable[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if str(item).strip()]
        return cleaned or None


class EmploymentCreate(EmploymentBase):
    pass


class EmploymentUpdate(BaseModel):
    employer_name: Optional[str] = Field(default=None, max_length=255)
    country: Optional[str] = Field(default=None, min_length=2, max_length=2)
    position: Optional[str] = Field(default=None, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    trailer_types: Optional[List[str]] = None
    route_types: Optional[List[str]] = None
    truck_brands: Optional[List[str]] = None
    eu_routes: Optional[bool] = None
    reason_for_leaving: Optional[str] = None
    reference_contact: Optional[str] = None

    @field_validator("employer_name")
    @classmethod
    def _trim_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("employer_name must not be empty")
        return cleaned

    @field_validator("country")
    @classmethod
    def _normalize_country(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        code = value.strip().upper()
        if not code:
            return None
        if len(code) != 2:
            raise ValueError("country must be a 2-letter ISO code")
        return code

    @field_validator("trailer_types", "route_types")
    @classmethod
    def _normalize_lists(cls, value: Optional[Iterable[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if str(item).strip()]
        return cleaned

    @field_validator("truck_brands")
    @classmethod
    def _normalize_trucks(cls, value: Optional[Iterable[str]]) -> Optional[List[str]]:
        if value is None:
            return None
        cleaned = [item.strip() for item in value if str(item).strip()]
        return cleaned or None


class EmploymentOut(EmploymentBase):
    id: str
    candidate_id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    # Attach orm_mode/from_attributes compat
    if "model_config" in _ORM_MODE_CONFIG:
        model_config = _ORM_MODE_CONFIG["model_config"]  # type: ignore[assignment]
    else:  # pragma: no cover
        Config = _ORM_MODE_CONFIG["Config"]  # type: ignore[misc]


def _employment_to_out(record: CandidateEmployment) -> EmploymentOut:
    return _model_validate(EmploymentOut, record)  # type: ignore[arg-type]


def _ensure_date_order(start_date: date, end_date: Optional[date]) -> None:
    if end_date and end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date_before_start_date",
        )


def _payload_to_record_dict(payload: EmploymentBase | EmploymentUpdate) -> dict[str, Any]:
    data = _model_dump(payload, exclude_unset=True)
    if "employer_name" in data and isinstance(data["employer_name"], str):
        data["employer_name"] = data["employer_name"].strip()
    for field in ("position", "reason_for_leaving", "reference_contact"):
        if field in data:
            data[field] = _clean_text(data[field])
    for field in ("trailer_types", "route_types", "truck_brands"):
        if field in data:
            normalized = _clean_list(data[field], allow_none=True)
            if field == "truck_brands":
                data[field] = normalized
            else:
                data[field] = normalized or []
    return data


async def _get_employment_or_404(
    db: AsyncSession,
    tenant_id: str,
    candidate_id: str,
    employment_id: str,
) -> CandidateEmployment:
    record = await employment_service.get_employment(
        db, tenant_id, candidate_id, employment_id
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="employment_not_found")
    return record


@router.get(
    "/{candidate_id}/employments",
    response_model=list[EmploymentOut],
    dependencies=[Depends(require_roles(Role.manager, Role.recruiter, Role.admin, Role.viewer))],
)
async def list_employments(
    candidate_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    rows = await employment_service.list_employments(db, str(tenant_id), str(candidate_id))
    return [_employment_to_out(row) for row in rows]


@router.post(
    "/{candidate_id}/employments",
    status_code=status.HTTP_201_CREATED,
    response_model=EmploymentOut,
    dependencies=[Depends(require_roles(Role.manager, Role.recruiter, Role.admin))],
)
async def create_employment(
    candidate_id: UUID,
    payload: EmploymentCreate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    _ensure_date_order(payload.start_date, payload.end_date)

    current = await employment_service.count_employments(db, str(tenant_id), str(candidate_id))
    if current >= MAX_EMPLOYMENTS_PER_CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="employment_limit_reached",
        )

    record_payload = _payload_to_record_dict(payload)
    record = await employment_service.create_employment(
        db,
        str(tenant_id),
        str(candidate_id),
        record_payload,
    )
    await db.commit()
    return _employment_to_out(record)


@router.put(
    "/{candidate_id}/employments/{employment_id}",
    response_model=EmploymentOut,
    dependencies=[Depends(require_roles(Role.manager, Role.recruiter, Role.admin))],
)
async def update_employment(
    candidate_id: UUID,
    employment_id: UUID,
    payload: EmploymentUpdate,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    record = await _get_employment_or_404(db, str(tenant_id), str(candidate_id), str(employment_id))

    updates = _payload_to_record_dict(payload)
    if not updates:
        return _employment_to_out(record)

    new_start = updates.get("start_date", record.start_date)
    new_end = updates.get("end_date", record.end_date)
    if new_start:
        _ensure_date_order(new_start, new_end)

    updated = await employment_service.update_employment(db, record, updates)
    await db.commit()
    return _employment_to_out(updated)


@router.delete(
    "/{candidate_id}/employments/{employment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(Role.manager, Role.recruiter, Role.admin))],
)
async def delete_employment(
    candidate_id: UUID,
    employment_id: UUID,
    db_tenant: Tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
):
    db, tenant_id = db_tenant
    deleted = await employment_service.delete_employment(
        db,
        str(tenant_id),
        str(candidate_id),
        str(employment_id),
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="employment_not_found")
    await db.commit()
