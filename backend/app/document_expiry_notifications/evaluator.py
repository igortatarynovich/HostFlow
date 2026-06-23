"""Document Expiry Notifications P1 — expiry event evaluator (evaluation only)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.app.document_expiry_notifications.constants import (
    DEFAULT_EXPIRING_SOON_DAYS,
    EVENT_DOCUMENT_EXPIRED,
    EVENT_DOCUMENT_EXPIRING_SOON,
    EXPIRY_ELIGIBLE_WORKFLOW_STATUSES,
    NOTIFICATION_EVENT_V1,
    SEVERITY_CRITICAL,
    SEVERITY_WARNING,
    SOURCE_LAYER,
)
from backend.app.document_runtime.constants import DOCUMENT_RUNTIME_V1

_P0_EXPIRY_EVENT_STATUSES = frozenset({"expiring_soon", "expired"})


def build_expiry_event_key(
    *,
    tenant_id: str,
    owner_type: str,
    owner_id: str,
    event_code: str,
    document_id: str | None = None,
    document_type_code: str | None = None,
) -> str:
    """Deterministic dedup identity for one expiry notification event."""
    doc_ref = str(document_id or document_type_code or "unknown").strip()
    return ":".join(
        [
            str(tenant_id or "").strip(),
            str(owner_type or "").strip().lower(),
            str(owner_id or "").strip(),
            doc_ref,
            str(event_code or "").strip(),
        ]
    )


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _event_code_for_expiry_status(expiry_status: str) -> str | None:
    if expiry_status == "expired":
        return EVENT_DOCUMENT_EXPIRED
    if expiry_status == "expiring_soon":
        return EVENT_DOCUMENT_EXPIRING_SOON
    return None


def _severity_for_event_code(event_code: str) -> str:
    if event_code == EVENT_DOCUMENT_EXPIRED:
        return SEVERITY_CRITICAL
    return SEVERITY_WARNING


def _runtime_from_snapshot(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    runtime = snapshot.get("document_runtime")
    if isinstance(runtime, dict) and runtime.get("evaluation_version") == DOCUMENT_RUNTIME_V1:
        return runtime
    if snapshot.get("evaluation_version") == DOCUMENT_RUNTIME_V1:
        return snapshot
    return None


def _expires_on_from_snapshot(snapshot: dict[str, Any]) -> str | None:
    for key in ("expires_on", "expire_date"):
        raw = snapshot.get(key)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    meta = snapshot.get("meta")
    if isinstance(meta, dict):
        for key in ("expires_at", "expire_date"):
            raw = meta.get(key)
            if raw is not None and str(raw).strip():
                return str(raw).strip()
    return None


def _embedded_document_runtime(runtime: dict[str, Any], *, expires_on: str | None) -> dict[str, Any]:
    embedded = dict(runtime)
    if expires_on and not embedded.get("expires_on"):
        embedded["expires_on"] = expires_on
    return embedded


def evaluate_document_expiry_events(
    runtime_snapshots: list[dict[str, Any]],
    *,
    expiring_soon_days: int = DEFAULT_EXPIRING_SOON_DAYS,
) -> list[dict[str, Any]]:
    """
    Evaluate ``notification_event_v1`` rows from pre-computed ``document_runtime_v1`` snapshots.

    Does not recalculate expiry, dispatch messages, or persist events. Input must come from
    Document Runtime Delivery Contract output (runtime already evaluated upstream).
    """
    events: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    evaluated_at = datetime.now(timezone.utc).isoformat()
    window_days = max(0, int(expiring_soon_days))

    for raw in runtime_snapshots or []:
        if not isinstance(raw, dict):
            continue

        runtime = _runtime_from_snapshot(raw)
        if runtime is None:
            continue

        workflow_status = _norm(runtime.get("workflow_status"))
        if workflow_status not in EXPIRY_ELIGIBLE_WORKFLOW_STATUSES:
            continue

        expiry_status = _norm(runtime.get("expiry_status"))
        if expiry_status not in _P0_EXPIRY_EVENT_STATUSES:
            continue

        event_code = _event_code_for_expiry_status(expiry_status)
        if not event_code:
            continue

        tenant_id = str(raw.get("tenant_id") or "").strip()
        owner_type = str(raw.get("owner_type") or "candidate").strip().lower()
        owner_id = str(raw.get("owner_id") or "").strip()
        document_id = runtime.get("document_id")
        document_type_code = runtime.get("document_type_code")
        expires_on = _expires_on_from_snapshot(raw)

        event_key = build_expiry_event_key(
            tenant_id=tenant_id,
            owner_type=owner_type,
            owner_id=owner_id,
            event_code=event_code,
            document_id=str(document_id) if document_id else None,
            document_type_code=str(document_type_code) if document_type_code else None,
        )
        if event_key in seen_keys:
            continue
        seen_keys.add(event_key)

        events.append(
            {
                "evaluation_version": NOTIFICATION_EVENT_V1,
                "event_key": event_key,
                "event_code": event_code,
                "source_layer": SOURCE_LAYER,
                "tenant_id": tenant_id or None,
                "owner_type": owner_type,
                "owner_id": owner_id or None,
                "document_id": document_id,
                "document_type_code": document_type_code,
                "severity": _severity_for_event_code(event_code),
                "expiring_soon_window_days": window_days,
                "document_runtime": _embedded_document_runtime(runtime, expires_on=expires_on),
                "evaluated_at": evaluated_at,
            }
        )

    events.sort(key=lambda row: str(row.get("event_key") or ""))
    return events


def evaluate_expiry_events_from_runtime_delivery(
    instances_delivery: dict[str, Any],
    *,
    owner_context: dict[str, Any],
    expiring_soon_days: int = DEFAULT_EXPIRING_SOON_DAYS,
) -> list[dict[str, Any]]:
    """Evaluate expiry events from ``build_instances_delivery_via_contract`` output."""
    snapshots: list[dict[str, Any]] = []
    for runtime in instances_delivery.get("documents") or []:
        if not isinstance(runtime, dict):
            continue
        snapshots.append({**owner_context, "document_runtime": runtime})
    return evaluate_document_expiry_events(snapshots, expiring_soon_days=expiring_soon_days)
