from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field, AliasChoices, ConfigDict

PYDANTIC_V2 = True
# ---------- Shared ----------


if PYDANTIC_V2:

    class DocumentFile(BaseModel):
        model_config = ConfigDict(extra="ignore")

        name: str
        url: Optional[str] = None
        size: Optional[int] = None
        mime: Optional[str] = None
        uploaded_at: Optional[datetime] = None
        uploaded_by: Optional[str] = None
        version: Optional[int] = None
        user_comment: Optional[str] = None

else:

    class DocumentFile(BaseModel):
        class Config:
            extra = "ignore"
            allow_population_by_field_name = True

        name: str
        url: Optional[str] = None
        size: Optional[int] = None
        mime: Optional[str] = None
        uploaded_at: Optional[datetime] = None
        uploaded_by: Optional[str] = None
        version: Optional[int] = None
        user_comment: Optional[str] = None


class DocumentTypeOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    code: str
    name: str
    description: Optional[str] = None
    kind: Optional[str] = None
    requested_from: Optional[str] = None
    process_type: Optional[str] = None
    default_expire_in_days: Optional[int] = None
    valid_days: Optional[int] = None  # legacy alias
    aliases: List[str] = Field(default_factory=list)
    required_meta: List[str] = Field(default_factory=list)
    owner_summary_weight: int = 0
    i18n_key: Optional[str] = None
    requires_custom_name: bool = False
    required: Optional[bool] = None
    meta_schema: Optional[Dict[str, Any]] = None
    title: Dict[str, Any] = Field(default_factory=dict)
    required_files: Dict[str, Any] = Field(default_factory=dict)
    expiry_rule: Dict[str, Any] = Field(default_factory=dict)
    duplicate_policy: Optional[str] = None
    orderable: bool = False


class DocumentReminderOut(BaseModel):
    due_at: datetime
    message: str
    offset_days: int
    status: str
    step_code: Optional[str] = None
    kind: str = Field(default="expiry")


class DocumentCheckOut(BaseModel):
    id: str
    document_id: str
    reviewer_id: Optional[str] = None
    decision: str
    reason_code: Optional[str] = None
    comment: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime

# ---------- Documents (create / read / update) ----------


class DocumentCreateIn(BaseModel):
    tenant_id: Optional[str] = None
    candidate_id: Optional[str] = None
    company_id: Optional[str] = None
    doc_type: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("doc_type", "type", "key"),
        description="Canonical document type code",
    )
    kind: Optional[str] = None
    requested_from: Optional[str] = None
    process_type: Optional[str] = None
    custom_name: Optional[str] = None
    number: Optional[str] = None
    status: Optional[str] = None
    issue_date: Optional[date] = Field(
        default=None, validation_alias=AliasChoices("issue_date", "issued_at")
    )
    expire_date: Optional[date] = Field(
        default=None, validation_alias=AliasChoices("expire_date", "expires_at")
    )
    ordered_at: Optional[date] = None
    valid_from: Optional[date] = None
    reminder_days_before: Optional[int] = Field(
        default=30, description="Days before expiry to notify"
    )
    owner_id: Optional[str] = None
    files: List[DocumentFile] = Field(default_factory=list)
    source: Optional[str] = Field(default=None, description="upload|ocr|import")
    external_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    workflow: Optional[Dict[str, Any]] = None
    meta: Dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("meta", "meta_json", "extra"),
    )
    user_comment: Optional[str] = None

    def effective_doc_type(self) -> str:
        if self.doc_type and str(self.doc_type).strip():
            return str(self.doc_type).strip()
        possible = self.meta.get("doc_type") if isinstance(self.meta, dict) else None
        if possible:
            return str(possible).strip()
        raise ValueError("doc_type is required")

    if not PYDANTIC_V2:

        @root_validator(pre=True)
        def _apply_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:
            data = dict(values or {})
            for target, aliases in ALIAS_MAP_CREATE.items():
                if target in data and data[target] is not None:
                    continue
                alias_value = _first_present(data, aliases)
                if alias_value is not None:
                    data.setdefault(target, alias_value)
            return data


class DocumentUpdateIn(BaseModel):
    doc_type: Optional[str] = Field(
        default=None, validation_alias=AliasChoices("doc_type", "type")
    )
    kind: Optional[str] = None
    requested_from: Optional[str] = None
    process_type: Optional[str] = None
    custom_name: Optional[str] = None
    number: Optional[str] = None
    status: Optional[str] = None
    issue_date: Optional[date] = Field(
        default=None, validation_alias=AliasChoices("issue_date", "issued_at")
    )
    expire_date: Optional[date] = Field(
        default=None, validation_alias=AliasChoices("expire_date", "expires_at")
    )
    ordered_at: Optional[date] = None
    valid_from: Optional[date] = None
    reminder_days_before: Optional[int] = None
    company_id: Optional[str] = None
    owner_id: Optional[str] = None
    files: Optional[List[DocumentFile]] = None
    source: Optional[str] = None
    external_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    workflow: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = Field(
        default=None, validation_alias=AliasChoices("meta", "meta_json", "extra")
    )
    user_comment: Optional[str] = None

    if not PYDANTIC_V2:

        @root_validator(pre=True)
        def _apply_aliases(cls, values: Dict[str, Any]) -> Dict[str, Any]:
            data = dict(values or {})
            for target, aliases in ALIAS_MAP_UPDATE.items():
                if target in data and data[target] is not None:
                    continue
                alias_value = _first_present(data, aliases)
                if alias_value is not None:
                    data.setdefault(target, alias_value)
            return data


if PYDANTIC_V2:

    class DocumentOut(BaseModel):
        model_config = ConfigDict(from_attributes=True)

        id: str
        tenant_id: str
        candidate_id: str
        company_id: Optional[str] = None
        own_company_id: Optional[str] = None
        kind: str
        doc_type: str
        type: str
        type_code: str
        custom_name: Optional[str] = None
        title: Optional[str] = None
        owner_type: str
        owner_id: Optional[str] = None
        requested_from: str
        process_type: str
        number: Optional[str] = None
        status: str
        reminder_days_before: int
        files: List[DocumentFile] = Field(default_factory=list)
        workflow: Dict[str, Any] = Field(default_factory=dict)
        source: Optional[str] = None
        external_id: Optional[str] = None
        verified_at: Optional[datetime] = None
        issue_date: Optional[date] = None
        expire_date: Optional[date] = None
        issued_at: Optional[date] = None
        expires_at: Optional[date] = None
        ordered_at: Optional[date] = None
        valid_from: Optional[date] = None
        user_comment: Optional[str] = None
        has_files: bool = False
        readiness_state: str = Field(default="pending")
        status_rank: int = 0
        meta: Dict[str, Any] = Field(default_factory=dict)
        extra: Dict[str, Any] = Field(default_factory=dict)
        meta_json: Dict[str, Any] = Field(default_factory=dict)
        created_at: datetime
        updated_at: datetime
        reminders: List[DocumentReminderOut] = Field(default_factory=list)
        version: Optional[int] = None
        last_check: Optional[DocumentCheckOut] = None
        document_runtime: Optional[Dict[str, Any]] = None
        responsible_user_id: Optional[str] = None
        responsible_name: Optional[str] = None

else:

    class DocumentOut(BaseModel):
        class Config:
            orm_mode = True
            allow_population_by_field_name = True

        id: str
        tenant_id: str
        candidate_id: str
        company_id: Optional[str] = None
        own_company_id: Optional[str] = None
        kind: str
        doc_type: str
        type: str
        type_code: str
        custom_name: Optional[str] = None
        title: Optional[str] = None
        owner_type: str
        owner_id: Optional[str] = None
        requested_from: str
        process_type: str
        number: Optional[str] = None
        status: str
        reminder_days_before: int
        files: List[DocumentFile] = Field(default_factory=list)
        workflow: Dict[str, Any] = Field(default_factory=dict)
        source: Optional[str] = None
        external_id: Optional[str] = None
        verified_at: Optional[datetime] = None
        issue_date: Optional[date] = None
        expire_date: Optional[date] = None
        issued_at: Optional[date] = None
        expires_at: Optional[date] = None
        ordered_at: Optional[date] = None
        valid_from: Optional[date] = None
        user_comment: Optional[str] = None
        has_files: bool = False
        readiness_state: str = Field(default="pending")
        status_rank: int = 0
        meta: Dict[str, Any] = Field(default_factory=dict)
        extra: Dict[str, Any] = Field(default_factory=dict)
        meta_json: Dict[str, Any] = Field(default_factory=dict)
        created_at: datetime
        updated_at: datetime
        reminders: List[DocumentReminderOut] = Field(default_factory=list)
        version: Optional[int] = None
        last_check: Optional[DocumentCheckOut] = None
        document_runtime: Optional[Dict[str, Any]] = None
        responsible_user_id: Optional[str] = None
        responsible_name: Optional[str] = None


class DocumentWithChecksOut(DocumentOut):
    checks: List[DocumentCheckOut] = Field(default_factory=list)


# Backward compatible alias
DocumentListOut = List[DocumentOut]


class RulesetVersionOut(BaseModel):
    id: str
    tenant_id: str
    own_company_id: Optional[str] = None
    version: int
    ruleset: Dict[str, Any]
    comment: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    is_active: bool = True
    signature: str
    origin_version_id: Optional[str] = None
    rollback_comment: Optional[str] = None


class RulesetDiffOut(BaseModel):
    version_id: str
    compare_to: Optional[str] = None
    diff: Dict[str, Any]
    computed_with: Optional[str] = None
    created_at: Optional[datetime] = None


class RulesetUsageOut(BaseModel):
    id: str
    ruleset_version_id: str
    used_in: str
    reference_id: Optional[str] = None
    used_at: datetime
    meta: Dict[str, Any] = Field(default_factory=dict)


class RulesetUsageResponse(BaseModel):
    items: List[RulesetUsageOut] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)


class BulkOperationSummaryOut(BaseModel):
    id: str
    operation_type: str
    target_type: str
    status: str
    items_count: int
    created_by: Optional[str] = None
    created_at: datetime
