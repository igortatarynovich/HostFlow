"""Manual evidence helpers for ADR-018 migration."""

from __future__ import annotations

from typing import Any, Optional

from backend.app.models.candidate_evidence import CandidateEvidence
from backend.app.models.enums import CandidateEvidenceStatus
from backend.app.requirement_rules.slot_registry import get_slot_definition

PROTECTED_EVIDENCE_VARIANT_TOKENS = frozenset(
    {
        "waiver",
        "attestation",
        "registry",
        "no_file",
    }
)

ACTIVE_EVIDENCE_STATUSES = frozenset(
    {
        CandidateEvidenceStatus.draft.value,
        CandidateEvidenceStatus.selected.value,
        CandidateEvidenceStatus.pending_review.value,
        CandidateEvidenceStatus.approved.value,
    }
)

OPERATOR_DECISION_STATUSES = frozenset(
    {
        CandidateEvidenceStatus.approved.value,
        CandidateEvidenceStatus.rejected.value,
    }
)


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_")


def is_protected_evidence_variant(evidence_variant_code: str) -> bool:
    code = _norm(evidence_variant_code)
    return any(token in code for token in PROTECTED_EVIDENCE_VARIANT_TOKENS)


def _variant_in_slot_catalog(requirement_code: str, variant_code: str) -> bool:
    slot = get_slot_definition(requirement_code)
    if not slot:
        return False
    target = _norm(variant_code)
    alts = slot.get("accepted_evidence_variants") or slot.get("satisfaction_alternatives") or []
    for alt in alts:
        if not isinstance(alt, dict):
            continue
        code = _norm(alt.get("evidence_variant_code") or alt.get("alternative_code"))
        if code == target:
            return True
    return False


def _has_operator_decision(evidence: CandidateEvidence) -> bool:
    status = _norm(getattr(evidence, "status", ""))
    if status in OPERATOR_DECISION_STATUSES:
        return True
    if getattr(evidence, "approved_by", None) or getattr(evidence, "rejected_by", None):
        return True
    notes = str(getattr(evidence, "notes", "") or "").strip()
    if notes:
        return True
    return False


def assess_evidence_supersede_eligibility(evidence: CandidateEvidence) -> tuple[bool, Optional[str]]:
    variant = str(evidence.evidence_variant_code or "")
    status = evidence.status.value if hasattr(evidence.status, "value") else str(evidence.status)

    if _norm(status) not in ACTIVE_EVIDENCE_STATUSES:
        return False, "inactive_status"
    if is_protected_evidence_variant(variant):
        return False, "protected_variant"
    if _has_operator_decision(evidence):
        return False, "operator_decision_present"
    if not _variant_in_slot_catalog(str(evidence.requirement_code), variant):
        return False, "not_standard_slot_variant"
    linked_docs = list(getattr(evidence, "documents", None) or [])
    if linked_docs and _norm(status) == CandidateEvidenceStatus.approved.value:
        return False, "approved_evidence_with_linked_documents"
    return True, None


def is_standard_manual_evidence(*, evidence_variant_code: str, status: str) -> bool:
    if _norm(status) not in ACTIVE_EVIDENCE_STATUSES:
        return False
    return not is_protected_evidence_variant(evidence_variant_code)


__all__ = [
    "ACTIVE_EVIDENCE_STATUSES",
    "PROTECTED_EVIDENCE_VARIANT_TOKENS",
    "assess_evidence_supersede_eligibility",
    "is_protected_evidence_variant",
    "is_standard_manual_evidence",
]
