"""Requirement Evaluation result contract (ADR-018 PR 2B-1).

Single immutable DTO for UI, stage gate, transfer, and audit consumers.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from backend.app.document_types.registry import (
    is_canonical_code,
    is_runtime_alias,
    registry_entry_for,
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


class RequirementEvaluationStatus(str, Enum):
    fulfilled = "fulfilled"
    missing = "missing"
    pending_review = "pending_review"
    invalid = "invalid"
    expired = "expired"
    not_applicable = "not_applicable"
    not_required_yet = "not_required_yet"
    not_selected = "not_selected"
    process_pending = "process_pending"
    waived = "waived"
    unresolved = "unresolved"


class RequirementApplicability(str, Enum):
    applicable = "applicable"
    not_applicable = "not_applicable"
    unresolved = "unresolved"


class OverallEvaluationStatus(str, Enum):
    ready = "ready"
    blocked = "blocked"
    pending = "pending"
    unresolved = "unresolved"


class EvaluationReasonCode(str, Enum):
    document_missing = "document_missing"
    document_expired = "document_expired"
    document_pending_review = "document_pending_review"
    required_field_missing = "required_field_missing"
    citizenship_unknown = "citizenship_unknown"
    alternative_excluded = "alternative_excluded"
    process_not_started = "process_not_started"
    process_pending = "process_pending"
    policy_condition_not_met = "policy_condition_not_met"
    schema_invalid = "schema_invalid"
    document_not_classified = "document_not_classified"
    legacy_alias_rejected = "legacy_alias_rejected"


class EvaluationReasonSeverity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"
    blocker = "blocker"


class EvaluationReasonSourceType(str, Enum):
    policy = "policy"
    document = "document"
    person = "person"
    process = "process"
    dependency = "dependency"
    override = "override"


class NextActionCode(str, Enum):
    upload_document = "upload_document"
    classify_document = "classify_document"
    complete_document_data = "complete_document_data"
    review_document = "review_document"
    start_process = "start_process"
    submit_application = "submit_application"
    await_authority = "await_authority"
    record_decision = "record_decision"
    issue_document = "issue_document"
    resolve_person_context = "resolve_person_context"
    none = "none"


class MatchRole(str, Enum):
    identity_evidence = "identity_evidence"
    legal_stay_evidence = "legal_stay_evidence"
    labor_access_evidence = "labor_access_evidence"
    entitlement_evidence = "entitlement_evidence"
    qualification_evidence = "qualification_evidence"
    medical_evidence = "medical_evidence"
    psychological_evidence = "psychological_evidence"
    attestation_evidence = "attestation_evidence"
    process_evidence = "process_evidence"
    general_evidence = "general_evidence"


FORBIDDEN_EVIDENCE_TYPE_CODES = frozenset({"unclassified", "other"})

NON_BLOCKING_STATUSES = frozenset(
    {
        RequirementEvaluationStatus.fulfilled,
        RequirementEvaluationStatus.not_applicable,
        RequirementEvaluationStatus.not_required_yet,
        RequirementEvaluationStatus.waived,
    }
)


@dataclass(frozen=True)
class EvaluationReason:
    code: EvaluationReasonCode
    message_key: str
    severity: EvaluationReasonSeverity
    source_type: EvaluationReasonSourceType
    source_ref: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message_key": self.message_key,
            "severity": self.severity.value,
            "source_type": self.source_type.value,
            "source_ref": self.source_ref,
            "details": dict(self.details),
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EvaluationReason:
        return cls(
            code=_require_enum(EvaluationReasonCode, raw.get("code"), "reason.code"),
            message_key=str(raw.get("message_key") or ""),
            severity=_require_enum(EvaluationReasonSeverity, raw.get("severity"), "reason.severity"),
            source_type=_require_enum(EvaluationReasonSourceType, raw.get("source_type"), "reason.source_type"),
            source_ref=str(raw.get("source_ref") or ""),
            details=dict(raw.get("details") or {}) if isinstance(raw.get("details"), dict) else {},
        )


@dataclass(frozen=True)
class MatchedDocumentReference:
    document_id: str
    document_type_code: str
    document_type_version_id: Optional[str]
    review_status: str
    valid_to: Optional[date]
    match_role: MatchRole

    def __post_init__(self) -> None:
        validate_matched_document_reference(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "document_type_code": self.document_type_code,
            "document_type_version_id": self.document_type_version_id,
            "review_status": self.review_status,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "match_role": self.match_role.value,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MatchedDocumentReference:
        return cls(
            document_id=str(raw.get("document_id") or ""),
            document_type_code=_norm(raw.get("document_type_code")),
            document_type_version_id=str(raw.get("document_type_version_id")).strip()
            if raw.get("document_type_version_id")
            else None,
            review_status=str(raw.get("review_status") or ""),
            valid_to=_parse_date(raw.get("valid_to")),
            match_role=_require_enum(MatchRole, raw.get("match_role"), "match_role"),
        )


@dataclass(frozen=True)
class MatchedProcessReference:
    process_code: str
    process_state: str
    requirement_code: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "process_code": self.process_code,
            "process_state": self.process_state,
            "requirement_code": self.requirement_code,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MatchedProcessReference:
        return cls(
            process_code=str(raw.get("process_code") or ""),
            process_state=str(raw.get("process_state") or ""),
            requirement_code=_norm(raw.get("requirement_code")),
        )


@dataclass(frozen=True)
class ExcludedAlternative:
    alternative_code: str
    disposition: str
    reason_code: EvaluationReasonCode

    def to_dict(self) -> dict[str, Any]:
        return {
            "alternative_code": self.alternative_code,
            "disposition": self.disposition,
            "reason_code": self.reason_code.value,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ExcludedAlternative:
        return cls(
            alternative_code=str(raw.get("alternative_code") or ""),
            disposition=str(raw.get("disposition") or ""),
            reason_code=_require_enum(EvaluationReasonCode, raw.get("reason_code"), "reason_code"),
        )


@dataclass(frozen=True)
class RequirementOwnership:
    source_responsibility: str
    operational_owner: str
    verification_role: str
    acquisition_mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_responsibility": self.source_responsibility,
            "operational_owner": self.operational_owner,
            "verification_role": self.verification_role,
            "acquisition_mode": self.acquisition_mode,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RequirementOwnership:
        return cls(
            source_responsibility=str(raw.get("source_responsibility") or ""),
            operational_owner=str(raw.get("operational_owner") or ""),
            verification_role=str(raw.get("verification_role") or ""),
            acquisition_mode=str(raw.get("acquisition_mode") or ""),
        )


@dataclass(frozen=True)
class RequirementEvaluationRow:
    requirement_code: str
    applicability: RequirementApplicability
    status: RequirementEvaluationStatus
    is_blocking: bool
    required_by_stage: Optional[str]
    blocks_stage: Optional[str]
    matched_alternative: Optional[str]
    matched_documents: tuple[MatchedDocumentReference, ...]
    matched_person_facts: tuple[str, ...]
    matched_process: Optional[MatchedProcessReference]
    excluded_alternatives: tuple[ExcludedAlternative, ...]
    missing_fields: tuple[str, ...]
    reasons: tuple[EvaluationReason, ...]
    ownership: Optional[RequirementOwnership]
    next_action: NextActionCode

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_code": self.requirement_code,
            "applicability": self.applicability.value,
            "status": self.status.value,
            "is_blocking": self.is_blocking,
            "required_by_stage": self.required_by_stage,
            "blocks_stage": self.blocks_stage,
            "matched_alternative": self.matched_alternative,
            "matched_documents": [row.to_dict() for row in self.matched_documents],
            "matched_person_facts": list(self.matched_person_facts),
            "matched_process": self.matched_process.to_dict() if self.matched_process else None,
            "excluded_alternatives": [row.to_dict() for row in self.excluded_alternatives],
            "missing_fields": list(self.missing_fields),
            "reasons": [row.to_dict() for row in self.reasons],
            "ownership": self.ownership.to_dict() if self.ownership else None,
            "next_action": self.next_action.value,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RequirementEvaluationRow:
        matched_docs_raw = raw.get("matched_documents") or []
        excluded_raw = raw.get("excluded_alternatives") or []
        reasons_raw = raw.get("reasons") or []
        process_raw = raw.get("matched_process")
        ownership_raw = raw.get("ownership")
        return cls(
            requirement_code=_norm(raw.get("requirement_code")),
            applicability=_require_enum(RequirementApplicability, raw.get("applicability"), "applicability"),
            status=_require_enum(RequirementEvaluationStatus, raw.get("status"), "status"),
            is_blocking=bool(raw.get("is_blocking")),
            required_by_stage=_norm(raw.get("required_by_stage")) or None,
            blocks_stage=_norm(raw.get("blocks_stage")) or None,
            matched_alternative=str(raw.get("matched_alternative")).strip()
            if raw.get("matched_alternative")
            else None,
            matched_documents=tuple(
                MatchedDocumentReference.from_dict(row)
                for row in matched_docs_raw
                if isinstance(row, dict)
            ),
            matched_person_facts=tuple(str(x) for x in (raw.get("matched_person_facts") or [])),
            matched_process=MatchedProcessReference.from_dict(process_raw)
            if isinstance(process_raw, dict)
            else None,
            excluded_alternatives=tuple(
                ExcludedAlternative.from_dict(row) for row in excluded_raw if isinstance(row, dict)
            ),
            missing_fields=tuple(str(x) for x in (raw.get("missing_fields") or [])),
            reasons=tuple(EvaluationReason.from_dict(row) for row in reasons_raw if isinstance(row, dict)),
            ownership=RequirementOwnership.from_dict(ownership_raw)
            if isinstance(ownership_raw, dict)
            else None,
            next_action=_require_enum(NextActionCode, raw.get("next_action"), "next_action"),
        )


@dataclass(frozen=True)
class RequirementEvaluationResult:
    entity_type: str
    entity_id: str
    policy_ref: str
    policy_version: str
    target_stage: str
    evaluated_at: datetime
    input_fingerprint: str
    overall_status: OverallEvaluationStatus
    can_transition: bool
    blocking_requirements: tuple[str, ...]
    requirements: tuple[RequirementEvaluationRow, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "policy_ref": self.policy_ref,
            "policy_version": self.policy_version,
            "target_stage": self.target_stage,
            "evaluated_at": self.evaluated_at.isoformat(),
            "input_fingerprint": self.input_fingerprint,
            "overall_status": self.overall_status.value,
            "can_transition": self.can_transition,
            "blocking_requirements": list(self.blocking_requirements),
            "requirements": [row.to_dict() for row in self.requirements],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RequirementEvaluationResult:
        requirements_raw = raw.get("requirements") or []
        return cls(
            entity_type=str(raw.get("entity_type") or ""),
            entity_id=str(raw.get("entity_id") or ""),
            policy_ref=str(raw.get("policy_ref") or ""),
            policy_version=str(raw.get("policy_version") or ""),
            target_stage=_norm(raw.get("target_stage")),
            evaluated_at=_parse_datetime(raw.get("evaluated_at")) or datetime.min.replace(tzinfo=None),
            input_fingerprint=str(raw.get("input_fingerprint") or ""),
            overall_status=_require_enum(OverallEvaluationStatus, raw.get("overall_status"), "overall_status"),
            can_transition=bool(raw.get("can_transition")),
            blocking_requirements=tuple(_norm(x) for x in (raw.get("blocking_requirements") or [])),
            requirements=tuple(
                RequirementEvaluationRow.from_dict(row) for row in requirements_raw if isinstance(row, dict)
            ),
        )

    def to_pipeline_blocker_lists(self) -> tuple[list[str], list[str], list[str]]:
        """Map blocking requirements to legacy gate list shape for hiring_pipeline_gates."""
        missing: list[str] = []
        problematic: list[str] = []
        pending_review: list[str] = []
        for row in self.requirements:
            if not row.is_blocking:
                continue
            code = row.requirement_code
            if row.status == RequirementEvaluationStatus.pending_review:
                pending_review.append(code)
            elif row.status in {
                RequirementEvaluationStatus.invalid,
                RequirementEvaluationStatus.expired,
            }:
                problematic.append(code)
            else:
                missing.append(code)
        return missing, problematic, pending_review

    def to_stage_gate_detail(self) -> dict[str, Any]:
        """HTTP 409 payload for stage guard consumers."""
        missing, problematic, pending_review = self.to_pipeline_blocker_lists()
        unfulfilled = [
            {
                "requirement_code": row.requirement_code,
                "status": row.status.value,
                "applicability": row.applicability.value,
                "is_blocking": row.is_blocking,
                "matched_alternative": row.matched_alternative,
                "reasons": [reason.to_dict() for reason in row.reasons],
                "next_action": row.next_action.value,
            }
            for row in self.requirements
            if row.is_blocking
        ]
        return {
            "code": "stage_blocked_by_requirements",
            "message": "Cannot move stage forward: required recruitment confirmations are incomplete",
            "blocker_source": "requirement_evaluation_v2",
            "policy_ref": self.policy_ref,
            "policy_version": self.policy_version,
            "target_stage": self.target_stage,
            "input_fingerprint": self.input_fingerprint,
            "overall_status": self.overall_status.value,
            "can_transition": self.can_transition,
            "blocking_requirements": list(self.blocking_requirements),
            "missing_requirements": missing,
            "problematic_requirements": problematic,
            "pending_review_requirements": pending_review,
            "unfulfilled_requirements": unfulfilled,
            "requirement_evaluation_v2": self.to_dict(),
            # Transitional aliases for older clients.
            "missing_types": missing,
            "problematic_types": problematic,
            "in_progress_types": pending_review,
        }


def _require_enum(enum_cls: type[Enum], value: Any, field_name: str) -> Enum:
    if isinstance(value, enum_cls):
        return value
    key = _norm(value)
    try:
        return enum_cls(key)  # type: ignore[return-value]
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_cls)
        raise ValueError(f"Unknown {field_name}: {value!r}; allowed: {allowed}") from exc


def validate_matched_document_reference(ref: MatchedDocumentReference) -> None:
    code = _norm(ref.document_type_code)
    if not code:
        raise ValueError("matched document requires document_type_code")
    if is_runtime_alias(code):
        raise ValueError(f"legacy alias not permitted in evaluation DTO: {code}")
    if code in FORBIDDEN_EVIDENCE_TYPE_CODES:
        raise ValueError(f"forbidden evidence type in evaluation DTO: {code}")
    if not is_canonical_code(code):
        raise ValueError(f"non-canonical document type in evaluation DTO: {code}")
    entry = registry_entry_for(code)
    if entry is not None and entry.classification_inbox_only:
        raise ValueError(f"classification inbox type not permitted as evidence: {code}")


def compute_is_blocking(
    *,
    applicability: RequirementApplicability,
    status: RequirementEvaluationStatus,
    blocks_stage: Optional[str],
    target_stage: str,
) -> bool:
    """Blocking is relative to target_stage; base status is unchanged."""
    if applicability != RequirementApplicability.applicable:
        return False
    if status in NON_BLOCKING_STATUSES:
        return False
    if not blocks_stage:
        return False
    return _norm(blocks_stage) == _norm(target_stage)


def recompute_blocking_for_target_stage(
    row: RequirementEvaluationRow,
    *,
    target_stage: str,
) -> RequirementEvaluationRow:
    """Recompute is_blocking only — status and applicability stay the same."""
    return replace(
        row,
        is_blocking=compute_is_blocking(
            applicability=row.applicability,
            status=row.status,
            blocks_stage=row.blocks_stage,
            target_stage=target_stage,
        ),
    )


def compute_blocking_requirements(
    requirements: tuple[RequirementEvaluationRow, ...],
) -> tuple[str, ...]:
    return tuple(
        sorted({row.requirement_code for row in requirements if row.is_blocking and row.requirement_code})
    )


def compute_can_transition(
    requirements: tuple[RequirementEvaluationRow, ...],
) -> bool:
    return not any(row.is_blocking for row in requirements)


def compute_overall_status(
    requirements: tuple[RequirementEvaluationRow, ...],
    *,
    can_transition: bool,
) -> OverallEvaluationStatus:
    if any(row.applicability == RequirementApplicability.unresolved for row in requirements):
        return OverallEvaluationStatus.unresolved
    if can_transition:
        if any(
            row.applicability == RequirementApplicability.applicable
            and row.status
            in {
                RequirementEvaluationStatus.pending_review,
                RequirementEvaluationStatus.process_pending,
                RequirementEvaluationStatus.missing,
            }
            for row in requirements
        ):
            return OverallEvaluationStatus.pending
        return OverallEvaluationStatus.ready
    return OverallEvaluationStatus.blocked


__all__ = [
    "EvaluationReason",
    "EvaluationReasonCode",
    "EvaluationReasonSeverity",
    "EvaluationReasonSourceType",
    "ExcludedAlternative",
    "FORBIDDEN_EVIDENCE_TYPE_CODES",
    "MatchRole",
    "MatchedDocumentReference",
    "MatchedProcessReference",
    "NextActionCode",
    "NON_BLOCKING_STATUSES",
    "OverallEvaluationStatus",
    "RequirementApplicability",
    "RequirementEvaluationResult",
    "RequirementEvaluationRow",
    "RequirementEvaluationStatus",
    "RequirementOwnership",
    "compute_blocking_requirements",
    "compute_can_transition",
    "compute_is_blocking",
    "compute_overall_status",
    "recompute_blocking_for_target_stage",
    "validate_matched_document_reference",
]
