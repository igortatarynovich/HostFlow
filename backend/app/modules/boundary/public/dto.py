"""Published Boundary handoff DTOs (no router import)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class HandoffOut(BaseModel):
    id: str
    candidate_id: str
    agency_tenant_id: str
    destination: str = "client_portal"
    handoff_type: str = "client_portal"
    application_id: Optional[str] = None
    from_company_id: Optional[str] = None
    to_company_id: Optional[str] = None
    locked_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    accepted_by_user_id: Optional[str] = None
    returned_by_user_id: Optional[str] = None
    returned_reason: Optional[str] = None
    client_company_id: Optional[str] = None
    client_tenant_id: Optional[str] = None
    requested_by_user_id: str
    requested_at: datetime
    assigned_to_user_id: Optional[str] = None
    status: str
    reviewed_by_user_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    return_reason: Optional[str] = None
    requested_by_user_name: Optional[str] = None
    assigned_to_user_name: Optional[str] = None

    class Config:
        from_attributes = True


__all__ = ["HandoffOut"]
