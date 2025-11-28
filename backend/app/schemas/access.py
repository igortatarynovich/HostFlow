from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class CompanyAccessGrant(BaseModel):
    user_id: str = Field(..., description="Target user ID")
    can_edit: bool = Field(default=False, description="Allow write operations")


class CompanyAccessEntry(BaseModel):
    user_id: str
    email: EmailStr
    role: str
    full_name: str | None = None
    short_id: str | None = None
    supervisor_id: str | None = None
    can_edit: bool = False


class CompanyAccessUpdate(BaseModel):
    entries: list[CompanyAccessEntry] = Field(default_factory=list)
