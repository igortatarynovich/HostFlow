"""Document Runtime Engine evaluator (P1) — pure lifecycle + expiry evaluation."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from backend.app.document_runtime.constants import (
    DOCUMENT_RUNTIME_V1,
    ExpiryStatus,
    RuntimeSignal,
    WorkflowStatus,
)
from backend.app.services.document_expiry_engine import evaluate_document_expiry

_APPROVED_STATUSES = frozenset(
    {
        "approved",
        "verified",
        "completed",
        "delivered",
        "received",
        "issued",
        "registered",
        "active",
        "not_required",
    }
)
_PENDING_REVIEW_STATUSES = frozenset({"submitted", "in_progress", "pending_review"})
_REJECTED_STATUSES = frozenset({"rejected", "cancelled"})
_MISSING_STATUSES = frozenset({"missing"})


def _norm_status(value: Any) -> str:
    return str(value or "").strip().lower()


def _document_type_code(doc: dict[str, Any]) -> str:
    for key in ("document_type_code", "type", "type_code", "doc_type"):
        raw = doc.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip().lower()
    return ""


def resolve_workflow_status(snapshot: Optional[dict[str, Any]]) -> WorkflowStatus:
    """Map document snapshot to canonical workflow status."""
    if not snapshot or not isinstance(snapshot, dict):
        return "missing"

    meta = snapshot.get("meta") if isinstance(snapshot.get("meta"), dict) else {}
    if bool(snapshot.get("superseded") or meta.get("superseded")):
        return "superseded"
    if bool(snapshot.get("replaced") or meta.get("replaced")):
        return "replaced"

    status = _norm_status(snapshot.get("status"))
    has_files = snapshot.get("has_files") is True

    if status in _REJECTED_STATUSES:
        return "rejected"
    if status in _MISSING_STATUSES or (not has_files and status in {"", "requested"}):
        return "missing"
    if status in _APPROVED_STATUSES:
        return "approved"
    if status in _PENDING_REVIEW_STATUSES:
        return "pending_review"
    if status == "uploaded" or has_files:
        return "uploaded"
    if status in {"expired", "overdue"}:
        return "approved"
    return "missing"


def expires_on_present(snapshot: Optional[dict[str, Any]]) -> bool:
    if not snapshot or not isinstance(snapshot, dict):
        return False
    expires_on = snapshot.get("expires_on") or snapshot.get("expire_date")
    if expires_on is None and isinstance(snapshot.get("meta"), dict):
        expires_on = snapshot["meta"].get("expires_at") or snapshot["meta"].get("expire_date")
    return expires_on is not None and str(expires_on).strip() != ""


def resolve_expiry_status(
    snapshot: Optional[dict[str, Any]],
    *,
    expiry_required: bool = False,
    reference_date: Optional[date] = None,
    expiring_soon_days: int = 30,
) -> ExpiryStatus:
    """Map document snapshot to canonical expiry status."""
    if not snapshot or not isinstance(snapshot, dict):
        return "no_expiry" if not expiry_required else "no_expiry"

    expires_on = snapshot.get("expires_on")
    if expires_on is None:
        expires_on = snapshot.get("expire_date")
    if expires_on is None and isinstance(snapshot.get("meta"), dict):
        expires_on = snapshot["meta"].get("expires_at") or snapshot["meta"].get("expire_date")

    evaluation = evaluate_document_expiry(
        expires_on=expires_on,
        expiry_required=expiry_required,
        reference_date=reference_date,
        expiring_soon_days=expiring_soon_days,
    )
    if evaluation.state == "missing_expiry":
        return "no_expiry"
    if evaluation.state == "valid" and not expires_on_present(snapshot):
        return "no_expiry"
    return evaluation.state  # type: ignore[return-value]


def _runtime_signal(
    workflow_status: WorkflowStatus,
    expiry_status: ExpiryStatus,
    *,
    expiry_required: bool,
    expires_on_present: bool,
) -> Optional[RuntimeSignal]:
    if workflow_status == "missing":
        return "missing"
    if workflow_status == "rejected":
        return "rejected"
    if expiry_status == "expired":
        return "expired"
    if expiry_required and not expires_on_present and expiry_status == "no_expiry":
        return "missing_expiry"
    if workflow_status in {"uploaded", "pending_review"}:
        return "pending_verification"
    if expiry_status == "expiring_soon":
        return "expiring_soon"
    return None


def compute_satisfies_requirement(
    workflow_status: WorkflowStatus,
    expiry_status: ExpiryStatus,
    *,
    expiry_required: bool = False,
    expires_on_present: bool = False,
) -> bool:
    """Satisfied only when lifecycle is approved and expiry is acceptable."""
    if workflow_status != "approved":
        return False
    if expiry_status == "expired":
        return False
    if expiry_required and not expires_on_present:
        return False
    return True


def evaluate_document_runtime(
    snapshot: Optional[dict[str, Any]],
    *,
    document_type_code: str | None = None,
    expiry_required: bool = False,
    reference_date: Optional[date] = None,
    expiring_soon_days: int = 30,
) -> dict[str, Any]:
    """
    Evaluate a single document instance into ``document_runtime_v1``.

    Requirement Engine decides *which* document types are required; this function
    decides whether a concrete instance satisfies that requirement.
    """
    doc_type = document_type_code or (_document_type_code(snapshot) if snapshot else "")
    workflow_status = resolve_workflow_status(snapshot)

    expires_on = None
    if snapshot and isinstance(snapshot, dict):
        expires_on = snapshot.get("expires_on") or snapshot.get("expire_date")
        if expires_on is None and isinstance(snapshot.get("meta"), dict):
            expires_on = snapshot["meta"].get("expires_at") or snapshot["meta"].get("expire_date")

    expiry_status = resolve_expiry_status(
        snapshot,
        expiry_required=expiry_required,
        reference_date=reference_date,
        expiring_soon_days=expiring_soon_days,
    )
    expires_on_present_flag = expires_on_present(snapshot)

    satisfies = compute_satisfies_requirement(
        workflow_status,
        expiry_status,
        expiry_required=expiry_required,
        expires_on_present=expires_on_present_flag,
    )

    signal = _runtime_signal(
        workflow_status,
        expiry_status,
        expiry_required=expiry_required,
        expires_on_present=expires_on_present_flag,
    )

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    doc_code = str(doc_type or "").strip().lower()

    if signal == "missing":
        blockers.append(
            {
                "code": "document_missing",
                "message": f"Required document missing: {doc_code or 'unknown'}",
                "document_type_code": doc_code or None,
                "source_layer": "document_runtime",
            }
        )
    elif signal == "rejected":
        blockers.append(
            {
                "code": "document_rejected",
                "message": f"Document rejected: {doc_code or 'unknown'}",
                "document_type_code": doc_code or None,
                "source_layer": "document_runtime",
            }
        )
    elif signal == "expired":
        blockers.append(
            {
                "code": "document_expired",
                "message": f"Document expired: {doc_code or 'unknown'}",
                "document_type_code": doc_code or None,
                "source_layer": "document_runtime",
            }
        )
    elif signal == "missing_expiry":
        blockers.append(
            {
                "code": "document_missing_expiry",
                "message": f"Document missing expiry date: {doc_code or 'unknown'}",
                "document_type_code": doc_code or None,
                "source_layer": "document_runtime",
            }
        )
    elif signal == "pending_verification":
        warnings.append(
            {
                "code": "document_pending_verification",
                "message": f"Document pending verification: {doc_code or 'unknown'}",
                "document_type_code": doc_code or None,
                "source_layer": "document_runtime",
                "severity": "warning",
            }
        )
    elif signal == "expiring_soon":
        warnings.append(
            {
                "code": "document_expiring_soon",
                "message": f"Document expiring soon: {doc_code or 'unknown'}",
                "document_type_code": doc_code or None,
                "source_layer": "document_runtime",
                "severity": "warning",
            }
        )

    document_id = None
    if snapshot and isinstance(snapshot, dict):
        raw_id = snapshot.get("document_id") or snapshot.get("id")
        if raw_id is not None and str(raw_id).strip():
            document_id = str(raw_id).strip()

    return {
        "evaluation_version": DOCUMENT_RUNTIME_V1,
        "document_id": document_id,
        "document_type_code": doc_code or None,
        "workflow_status": workflow_status,
        "expiry_status": expiry_status,
        "satisfies_requirement": satisfies,
        "runtime_signal": signal,
        "blockers": blockers,
        "warnings": warnings,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def runtime_precedence(runtime: dict[str, Any]) -> int:
    """Higher rank wins when multiple instances share a document type."""
    if runtime.get("satisfies_requirement"):
        return 4
    workflow = str(runtime.get("workflow_status") or "")
    if workflow in {"uploaded", "pending_review", "approved"}:
        return 3
    if workflow in {"replaced", "rejected"}:
        return 2
    return 1


def map_runtime_to_requirement_items(
    runtime: dict[str, Any],
    *,
    doc_code: str,
    verification: str,
    reason_code: str,
    level: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Translate document_runtime_v1 into requirement-engine blockers/warnings."""
    if runtime.get("satisfies_requirement"):
        return [], list(runtime.get("warnings") or [])

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    signal = str(runtime.get("runtime_signal") or "")

    if signal == "pending_verification":
        item = {
            "code": reason_code or f"document_pending:{doc_code}",
            "message": f"Required document pending verification: {doc_code}",
            "source_rule_id": doc_code,
            "layer": "document_runtime",
            "document_type_code": doc_code,
            "source_layer": "document_runtime",
        }
        if verification == "required" or level == "blocking":
            blockers.append(item)
        else:
            item["severity"] = "warning"
            warnings.append(item)
        return blockers, warnings

    for row in runtime.get("blockers") or []:
        if not isinstance(row, dict):
            continue
        blockers.append(
            {
                "code": str(row.get("code") or reason_code or f"document_required:{doc_code}"),
                "message": str(row.get("message") or f"Required document not satisfied: {doc_code}"),
                "source_rule_id": doc_code,
                "layer": "document_runtime",
                "document_type_code": doc_code,
                "source_layer": "document_runtime",
            }
        )

    for row in runtime.get("warnings") or []:
        if isinstance(row, dict):
            warnings.append(dict(row))

    if not blockers and signal not in {"pending_verification"}:
        blockers.append(
            {
                "code": reason_code or f"document_required:{doc_code}",
                "message": f"Required document not satisfied: {doc_code}",
                "source_rule_id": doc_code,
                "layer": "document_runtime",
                "document_type_code": doc_code,
                "source_layer": "document_runtime",
            }
        )

    return blockers, warnings
