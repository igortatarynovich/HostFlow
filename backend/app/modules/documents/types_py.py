from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Literal, Optional

EntityType = Literal["candidate", "company", "vacancy"]
DocStatus = Literal["missing", "uploaded", "approved", "rejected", "expired"]


@dataclass
class OwnerRef:
    type: EntityType
    id: str


@dataclass
class DocumentType:
    id: str
    code: str
    name: str
    entity_scope: EntityType  # для кого предназначен
    number_regex: Optional[str] = None
    default_validity_days: Optional[int] = None
    meta_schema: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass
class Attachment:
    id: str
    storage_key: str
    mime: Optional[str] = None
    size: Optional[int] = None
    checksum: Optional[str] = None
    created_at: Optional[date] = None


@dataclass
class CheckDecision:
    id: str
    reviewer_id: str
    decision: Literal["approved", "rejected", "pending"]
    reason_code: Optional[str] = None
    comment: Optional[str] = None
    created_at: Optional[date] = None


@dataclass
class Document:
    id: str
    tenant_id: str
    type_code: str
    owner: OwnerRef
    title: Optional[str] = None
    status: DocStatus = "uploaded"
    issued_at: Optional[date] = None
    expires_at: Optional[date] = None
    meta_json: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    attachments: List[Attachment] = field(default_factory=list)
    checks: List[CheckDecision] = field(default_factory=list)


@dataclass
class OwnerContext:
    citizenship: Optional[str] = None
    residency_status: Optional[str] = None
    vacancy: Dict[str, Any] = field(default_factory=dict)
