from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from backend.app.models.vacancy import EmploymentType


# ---- Base / shared fields ---------------------------------------------------
class VacancyBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    description: Optional[str] = None

    # status/state/stage — принимаем любые ключи, сохраняем в .status
    status: Optional[str] = Field(default=None, alias='status')
    state: Optional[str] = Field(default=None, alias='state')
    stage: Optional[str] = Field(default=None, alias='stage')

    # зарплата — поддержка разных названий
    salary_from: Optional[float] = Field(default=None, alias='salary_from')
    salary_to: Optional[float] = Field(default=None, alias='salary_to')
    currency: Optional[str] = Field(default=None, alias='currency')

    # альтернативные алиасы, которые мы примем из запроса
    min_salary: Optional[float] = Field(default=None, alias='min_salary')
    max_salary: Optional[float] = Field(default=None, alias='max_salary')
    salary_min: Optional[float] = Field(default=None, alias='salary_min')
    salary_max: Optional[float] = Field(default=None, alias='salary_max')
    from_salary: Optional[float] = Field(default=None, alias='from_salary')
    to_salary: Optional[float] = Field(default=None, alias='to_salary')
    currency_code: Optional[str] = Field(default=None, alias='currency_code')
    salary_currency: Optional[str] = Field(default=None, alias='salary_currency')
    curr: Optional[str] = Field(default=None, alias='curr')

    # флаги
    is_open: Optional[bool] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None

    # прочее
    employment_type: Optional[EmploymentType] = None
    location: Optional[str] = None
    company_id: Optional[UUID] = None

    def canonical_salary_from(self) -> Optional[float]:
        return (
            self.salary_from
            or self.min_salary
            or self.salary_min
            or self.from_salary
        )

    def canonical_salary_to(self) -> Optional[float]:
        return (
            self.salary_to
            or self.max_salary
            or self.salary_max
            or self.to_salary
        )

    def canonical_currency(self) -> Optional[str]:
        return (
            self.currency
            or self.currency_code
            or self.salary_currency
            or self.curr
        )

    def canonical_status(self) -> Optional[str]:
        return self.status or self.state or self.stage


# ---- Create / Update / Read -------------------------------------------------
class VacancyCreate(VacancyBase):
    title: str
    employment_type: EmploymentType


class VacancyUpdate(VacancyBase):
    title: Optional[str] = None
    """
    Все поля — опциональные, чтобы PATCH принимал только изменённое.
    Дополнительно используем canonical_* геттеры в сервисе для единообразия.
    """


class VacancyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str] = None

    status: Optional[str] = None
    salary_from: Optional[float] = None
    salary_to: Optional[float] = None
    currency: Optional[str] = None

    is_open: Optional[bool] = None
    is_active: Optional[bool] = None
    is_archived: Optional[bool] = None

    employment_type: EmploymentType
    location: Optional[str] = None
    company_id: Optional[UUID] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
