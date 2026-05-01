"""HR workforce satellites — PATCH/POST payloads (storage MVP, not payroll math)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PayrollProfilePatch(BaseModel):
    pay_type: Optional[str] = Field(default=None, max_length=64)
    base_rate: Optional[str] = Field(default=None, max_length=64, description="Decimal string, e.g. 6500.00")
    currency: Optional[str] = Field(default=None, max_length=8)
    calculation_system: Optional[str] = Field(default=None, max_length=128)
    pay_day_note: Optional[str] = Field(default=None, max_length=256)
    bank_account: Optional[str] = Field(default=None, max_length=128)
    tax_status: Optional[str] = Field(default=None, max_length=64)
    pit_declarations: Optional[dict[str, Any]] = None
    allowances: Optional[dict[str, Any]] = None
    deductions: Optional[dict[str, Any]] = None
    payroll_status: Optional[str] = Field(default=None, max_length=64)
    external_refs: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None


# --- ZUS ---
class ZusProfilePatch(BaseModel):
    registration_status: Optional[str] = Field(default=None, max_length=64)
    submitted_at: Optional[date] = None
    employment_basis: Optional[str] = Field(default=None, max_length=64)
    responsible_party: Optional[str] = Field(default=None, max_length=64)
    insurance_coverage: Optional[dict[str, Any]] = None
    forms: Optional[list[Any]] = None
    meta: Optional[dict[str, Any]] = None


# --- Employment / contract ---
class EmploymentCreate(BaseModel):
    contract_type: str = Field(default="unknown", max_length=64)
    rate_model: Optional[dict[str, Any]] = None
    schedule: Optional[dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    conditions_text: Optional[str] = None
    vacancy_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class EmploymentPatch(BaseModel):
    contract_type: Optional[str] = Field(default=None, max_length=64)
    rate_model: Optional[dict[str, Any]] = None
    schedule: Optional[dict[str, Any]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    conditions_text: Optional[str] = None
    vacancy_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class OnboardingTaskPatch(BaseModel):
    title: Optional[str] = Field(default=None, max_length=512)
    sort_order: Optional[int] = None
    status: Optional[str] = Field(default=None, max_length=32)
    due_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assignee_user_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class AbsenceCreate(BaseModel):
    absence_type: str = Field(..., max_length=64)
    start_date: date
    end_date: Optional[date] = None
    source: str = Field(default="manual", max_length=64)
    status: str = Field(default="reported", max_length=64)
    payer: Optional[str] = Field(default=None, max_length=32)
    payroll_impact: Optional[str] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class AbsencePatch(BaseModel):
    absence_type: Optional[str] = Field(default=None, max_length=64)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    source: Optional[str] = Field(default=None, max_length=64)
    status: Optional[str] = Field(default=None, max_length=64)
    payer: Optional[str] = Field(default=None, max_length=32)
    payroll_impact: Optional[str] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class LeaveRequestCreate(BaseModel):
    leave_type: str = Field(..., max_length=64)
    start_date: date
    end_date: date
    status: str = Field(default="pending", max_length=64)
    year_entitlement_days: Optional[str] = Field(default=None, max_length=32, description="Decimal days")
    used_days_before: Optional[str] = Field(default=None, max_length=32)
    conflict_flags: Optional[dict[str, Any]] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None


class LeaveRequestPatch(BaseModel):
    leave_type: Optional[str] = Field(default=None, max_length=64)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=64)
    year_entitlement_days: Optional[str] = None
    used_days_before: Optional[str] = None
    conflict_flags: Optional[dict[str, Any]] = None
    approver_user_id: Optional[str] = None
    decided_at: Optional[datetime] = None
    comment: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
