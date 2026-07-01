from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional

from backend.app.document_types.definitions import DOCUMENT_TYPE_DEFINITIONS
from backend.app.models.enums import (
    DocumentDuplicatePolicy,
    DocumentKind,
    DocumentProcessType,
    DocumentRequestedFrom,
    DocumentStatus,
)


@dataclass(frozen=True)
class DocumentTypeDefaults:
    doc_type: str
    kind: DocumentKind
    requested_from: DocumentRequestedFrom
    process_type: DocumentProcessType = DocumentProcessType.none
    default_expire_in_days: Optional[int] = None
    aliases: tuple[str, ...] = ()
    required_meta: tuple[str, ...] = ()
    owner_summary_weight: int = 0
    i18n_key: Optional[str] = None
    requires_custom_name: bool = False
    title: Dict[str, str] = field(default_factory=dict)
    metadata_schema: Dict[str, Any] = field(default_factory=dict)
    required_files: Dict[str, Any] = field(default_factory=dict)
    expiry_rule: Dict[str, Any] = field(default_factory=dict)
    duplicate_policy: DocumentDuplicatePolicy = DocumentDuplicatePolicy.one_per_candidate
    orderable: bool = False


def _extract_required_fields(schema: Mapping[str, Any]) -> tuple[str, ...]:
    if not isinstance(schema, Mapping):
        return ()
    required = schema.get("required")
    if isinstance(required, (list, tuple)):
        return tuple(str(item) for item in required)
    return ()


def _alias_tuple(code: str, aliases: Iterable[str]) -> tuple[str, ...]:
    ordered: Dict[str, None] = {code: None}
    for alias in aliases:
        ordered[str(alias)] = None
    return tuple(ordered.keys())


DOCUMENT_TYPE_DEFAULTS: Dict[str, DocumentTypeDefaults] = {}
for definition in DOCUMENT_TYPE_DEFINITIONS:
    DOCUMENT_TYPE_DEFAULTS[definition.code] = DocumentTypeDefaults(
        doc_type=definition.code,
        kind=definition.kind,
        requested_from=definition.requested_from,
        process_type=definition.process_type,
        default_expire_in_days=definition.default_expire_in_days,
        aliases=_alias_tuple(definition.code, definition.aliases),
        required_meta=_extract_required_fields(definition.metadata_schema),
        owner_summary_weight=definition.owner_summary_weight,
        i18n_key=definition.i18n_key or f"documents.catalog.{definition.code}",
        requires_custom_name=definition.requires_custom_name,
        title=copy.deepcopy(definition.title),
        metadata_schema=copy.deepcopy(definition.metadata_schema),
        required_files=copy.deepcopy(definition.required_files),
        expiry_rule=copy.deepcopy(definition.expiry_rule),
        duplicate_policy=definition.duplicate_policy,
        orderable=definition.orderable,
    )


DOCUMENT_TYPE_ALIASES: Dict[str, str] = {}
for defaults in DOCUMENT_TYPE_DEFAULTS.values():
    for alias in defaults.aliases:
        DOCUMENT_TYPE_ALIASES[alias] = defaults.doc_type


def normalize_doc_type(raw: str | None) -> str:
    value = (raw or "").strip().lower()
    if not value:
        return "additional_document"
    # Primary codes (e.g. "passport") are not listed in ALIASES — only alias → canonical.
    if value in DOCUMENT_TYPE_DEFAULTS:
        return value
    return DOCUMENT_TYPE_ALIASES.get(value, "additional_document")


def get_doc_type_defaults(raw: str | None) -> DocumentTypeDefaults:
    canonical = normalize_doc_type(raw)
    defaults = DOCUMENT_TYPE_DEFAULTS.get(canonical)
    if defaults is not None:
        return defaults
    return DocumentTypeDefaults(
        doc_type=canonical,
        kind=DocumentKind.driver,
        requested_from=DocumentRequestedFrom.driver,
        process_type=DocumentProcessType.other,
        default_expire_in_days=None,
        aliases=(canonical,),
        required_meta=(),
        owner_summary_weight=0,
        i18n_key=f"documents.catalog.{canonical}",
        requires_custom_name=False,
        title={},
        metadata_schema={},
        required_files={},
        expiry_rule={},
        duplicate_policy=DocumentDuplicatePolicy.one_per_candidate,
        orderable=False,
    )


def doc_type_requires_user_comment(raw: str | None) -> bool:
    """
    Return True when the canonical doc type mandates a user comment.
    Currently only additional_document requires it, but the helper keeps the logic centralized.
    """
    defaults = get_doc_type_defaults(raw)
    return defaults.doc_type == "additional_document"


STATUS_NORMALIZATION: Dict[str, DocumentStatus] = {
    "missing": DocumentStatus.missing,
    "requested": DocumentStatus.requested,
    "in_progress": DocumentStatus.in_progress,
    "submitted": DocumentStatus.submitted,
    "received": DocumentStatus.received,
    "delivered": DocumentStatus.delivered,
    "approved": DocumentStatus.approved,
    "completed": DocumentStatus.completed,
    "overdue": DocumentStatus.overdue,
    "rejected": DocumentStatus.rejected,
    "expired": DocumentStatus.expired,
    "planned": DocumentStatus.missing,
    "pending": DocumentStatus.requested,
    "pending_validation": DocumentStatus.in_progress,
    "upload": DocumentStatus.received,
    "uploaded": DocumentStatus.received,
    "ready": DocumentStatus.approved,
    "verified": DocumentStatus.approved,
    "invalid": DocumentStatus.rejected,
    "ordered": DocumentStatus.in_progress,
    "awaiting_review": DocumentStatus.in_progress,
    "awaiting_check": DocumentStatus.in_progress,
    "problem": DocumentStatus.rejected,
}


def normalize_status(
    value: object | None,
    *,
    default: DocumentStatus = DocumentStatus.missing,
) -> DocumentStatus:
    if isinstance(value, DocumentStatus):
        return value
    if value is None:
        return DocumentStatus.missing
    status = str(value).strip().lower()
    mapped = STATUS_NORMALIZATION.get(status)
    if mapped is not None:
        return mapped
    if status:
        return default
    return DocumentStatus.missing


def normalize_kind(value: Optional[str], fallback: DocumentKind) -> DocumentKind:
    if not value:
        return fallback
    try:
        return DocumentKind(value)
    except ValueError as exc:
        raise ValueError(f"Invalid document kind: {value}") from exc


def normalize_requested_from(
    value: Optional[str], fallback: DocumentRequestedFrom
) -> DocumentRequestedFrom:
    if not value:
        return fallback
    try:
        return DocumentRequestedFrom(value)
    except ValueError as exc:
        raise ValueError(f"Invalid requested_from: {value}") from exc


def normalize_process_type(
    value: Optional[str], fallback: DocumentProcessType
) -> DocumentProcessType:
    if not value:
        return fallback
    candidate = str(value).strip().lower()
    try:
        return DocumentProcessType(candidate)
    except ValueError:
        if fallback:
            return fallback
        return DocumentProcessType.other


def prepare_template_documents(
    raw_docs: Iterable[Mapping[str, object]]
) -> list[dict[str, object]]:
    """
    Prepare template documents, ensuring PESEL is always included and required.
    PESEL is automatically added if not present in the template.
    """
    prepared: dict[str, dict[str, object]] = {}
    for item in raw_docs or []:  # type: ignore[arg-type]
        if not isinstance(item, Mapping):
            continue
        raw_doc_type = item.get("doc_type")
        doc_type = normalize_doc_type(str(raw_doc_type or ""))
        if not doc_type:
            continue

        defaults = get_doc_type_defaults(doc_type)
        try:
            kind = normalize_kind(item.get("kind"), defaults.kind)
        except ValueError:
            kind = defaults.kind
        try:
            requested_from = normalize_requested_from(
                item.get("requested_from"), defaults.requested_from
            )
        except ValueError:
            requested_from = defaults.requested_from
        try:
            process_type = normalize_process_type(
                item.get("process_type"), defaults.process_type
            )
        except ValueError:
            process_type = defaults.process_type

        meta_raw = item.get("meta")
        meta = dict(meta_raw) if isinstance(meta_raw, Mapping) else {}

        remind_days = item.get("remind_days_before")
        try:
            remind_days_int = int(remind_days) if remind_days is not None else None
        except (TypeError, ValueError):
            remind_days_int = None

        prepared[doc_type] = {
            "doc_type": doc_type,
            "kind": kind.value,
            "requested_from": requested_from.value,
            "process_type": process_type.value,
            "required": bool(item.get("required", True)),
            "meta": meta,
            "remind_days_before": remind_days_int,
        }

    # Ensure PESEL is always included and required (API guard)
    if "pesel" not in prepared:
        pesel_defaults = get_doc_type_defaults("pesel")
        prepared["pesel"] = {
            "doc_type": "pesel",
            "kind": pesel_defaults.kind.value,
            "requested_from": pesel_defaults.requested_from.value,
            "process_type": pesel_defaults.process_type.value,
            "required": True,  # Always required
            "meta": {},
            "remind_days_before": None,
        }
    else:
        # Ensure PESEL is marked as required even if template doesn't specify it
        prepared["pesel"]["required"] = True

    return list(prepared.values())
