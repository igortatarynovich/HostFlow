from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr


class ProfileIn(BaseModel):
    first_name: str
    last_name: str
    middle_name: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    position: Optional[str] = None
    employment_type: Optional[str] = None
    manager_id: Optional[int] = None
    hire_date: Optional[date] = None
    fire_date: Optional[date] = None


class TermsIn(BaseModel):
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    salary_monthly: Optional[float] = None
    bonus_scheme_code: Optional[str] = None
    work_hours_per_week: Optional[int] = None
    currency: Optional[str] = None
    comment: Optional[str] = None


class CreateUserProfileIn(BaseModel):
    email: EmailStr
    role: str
    is_active: bool = True
    password: Optional[str] = None
    profile: ProfileIn
    terms: Optional[TermsIn] = None
