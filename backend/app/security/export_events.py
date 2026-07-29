"""Export security telemetry (emit_security_event_v1 only).

Includes Phase 4 anomaly detection v1: after ``export.generated``, optionally emit
``export.anomaly.detected`` when documented per-request thresholds are exceeded.
Sliding-window / after-hours detectors remain Phase 7 backlog.
"""

from __future__ import annotations

from typing import Any

from backend.app.security.canonical_emit import emit_security_event_v1
from backend.app.security.event_taxonomy import (
    EVENT_EXPORT_ANOMALY_DETECTED,
    EVENT_EXPORT_GENERATED,
)

EXPORT_EVENT_EXTRA_ALLOWLIST = frozenset(
    {
        "export_type",
        "row_count",
        "byte_size",
        "filter_scope",
        "async_job_id",
        "export_scope",
        "contains_class3",
        "bulk_operation",
        "reason",
        "response_mode",
        "anomaly_codes",
        "threshold_row_count",
        "threshold_byte_size",
        "threshold_class3_rows",
    }
)

# --- Phase 4 anomaly thresholds v1 (documented in runtime-roadmap.md) ---------
# Per-request heuristics only (no sliding window). Tuned to catch mass / CLASS3
# dumps without blocking normal single-candidate exports (~tens of rows).
EXPORT_ANOMALY_ROW_COUNT_THRESHOLD = 500
EXPORT_ANOMALY_BYTE_SIZE_THRESHOLD = 5_000_000  # 5 MiB serialized / attachment
EXPORT_ANOMALY_CLASS3_ROW_COUNT_THRESHOLD = 50
# False positives expected: org-structure snapshots for large tenants; large
# analytics CSV. Triage via anomaly_codes + export_type — do not auto-block.


def clip_export_filter_scope(value: str | None, *, max_len: int = 256) -> str | None:
    """Keep ``filter_scope`` bounded; producers must not put SQL / raw filters here."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return s[:max_len]


def evaluate_export_anomaly_codes(
    *,
    row_count: int | None,
    byte_size: int | None,
    contains_class3: bool | None,
    bulk_operation: bool | None,
    row_count_threshold: int = EXPORT_ANOMALY_ROW_COUNT_THRESHOLD,
    byte_size_threshold: int = EXPORT_ANOMALY_BYTE_SIZE_THRESHOLD,
    class3_row_threshold: int = EXPORT_ANOMALY_CLASS3_ROW_COUNT_THRESHOLD,
) -> list[str]:
    """Return short machine codes when per-request thresholds fire (empty = no anomaly)."""
    codes: list[str] = []
    if row_count is not None and int(row_count) >= int(row_count_threshold):
        codes.append("row_count_threshold")
    if byte_size is not None and int(byte_size) >= int(byte_size_threshold):
        codes.append("byte_size_threshold")
    if bool(contains_class3) and bool(bulk_operation):
        codes.append("class3_bulk")
    if (
        bool(contains_class3)
        and row_count is not None
        and int(row_count) >= int(class3_row_threshold)
    ):
        codes.append("class3_row_count")
    return codes


def emit_export_security_event_v1(
    *,
    event_type: str,
    result: str,
    severity: str,
    source: str,
    tenant_id: str | None,
    access_kind: str | None,
    entity_type: str,
    entity_id: str | None,
    export_type: str,
    actor_id: str | None = None,
    correlation_id: str | None = None,
    row_count: int | None = None,
    byte_size: int | None = None,
    filter_scope: str | None = None,
    async_job_id: str | None = None,
    export_scope: str | None = None,
    contains_class3: bool | None = None,
    bulk_operation: bool | None = None,
    reason: str | None = None,
    response_mode: str | None = None,
    anomaly_codes: str | None = None,
    threshold_row_count: int | None = None,
    threshold_byte_size: int | None = None,
    threshold_class3_rows: int | None = None,
    _skip_anomaly_check: bool = False,
) -> dict[str, Any]:
    """Emit an export-scoped security event with a strict ``extra`` allowlist."""
    extra: dict[str, Any] = {"export_type": str(export_type).strip()[:128]}
    if row_count is not None:
        extra["row_count"] = int(row_count)
    if byte_size is not None:
        extra["byte_size"] = int(byte_size)
    fs = clip_export_filter_scope(filter_scope)
    if fs is not None:
        extra["filter_scope"] = fs
    if async_job_id is not None:
        extra["async_job_id"] = str(async_job_id).strip()[:128]
    if export_scope is not None:
        extra["export_scope"] = str(export_scope).strip()[:64]
    if contains_class3 is not None:
        extra["contains_class3"] = bool(contains_class3)
    if bulk_operation is not None:
        extra["bulk_operation"] = bool(bulk_operation)
    if reason is not None:
        extra["reason"] = str(reason).strip()[:256]
    if response_mode is not None:
        extra["response_mode"] = str(response_mode).strip()[:64]
    if anomaly_codes is not None:
        extra["anomaly_codes"] = str(anomaly_codes).strip()[:256]
    if threshold_row_count is not None:
        extra["threshold_row_count"] = int(threshold_row_count)
    if threshold_byte_size is not None:
        extra["threshold_byte_size"] = int(threshold_byte_size)
    if threshold_class3_rows is not None:
        extra["threshold_class3_rows"] = int(threshold_class3_rows)

    payload = emit_security_event_v1(
        event_type=event_type,
        result=result,
        severity=severity,
        source=source,
        tenant_id=tenant_id,
        actor_id=actor_id,
        correlation_id=correlation_id,
        access_kind=access_kind,
        action=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        extra=extra,
        extra_allowlist=EXPORT_EVENT_EXTRA_ALLOWLIST,
    )

    if (
        not _skip_anomaly_check
        and event_type == EVENT_EXPORT_GENERATED
        and result == "success"
    ):
        codes = evaluate_export_anomaly_codes(
            row_count=row_count,
            byte_size=byte_size,
            contains_class3=contains_class3,
            bulk_operation=bulk_operation,
        )
        if codes:
            emit_export_security_event_v1(
                event_type=EVENT_EXPORT_ANOMALY_DETECTED,
                result="success",
                severity="medium",
                source=source,
                tenant_id=tenant_id,
                access_kind=access_kind,
                entity_type=entity_type,
                entity_id=entity_id,
                export_type=export_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                row_count=row_count,
                byte_size=byte_size,
                filter_scope=filter_scope,
                async_job_id=async_job_id,
                export_scope=export_scope,
                contains_class3=contains_class3,
                bulk_operation=bulk_operation,
                reason=",".join(codes),
                response_mode=response_mode,
                anomaly_codes=",".join(codes),
                threshold_row_count=EXPORT_ANOMALY_ROW_COUNT_THRESHOLD,
                threshold_byte_size=EXPORT_ANOMALY_BYTE_SIZE_THRESHOLD,
                threshold_class3_rows=EXPORT_ANOMALY_CLASS3_ROW_COUNT_THRESHOLD,
                _skip_anomaly_check=True,
            )

    return payload


__all__ = [
    "EXPORT_ANOMALY_BYTE_SIZE_THRESHOLD",
    "EXPORT_ANOMALY_CLASS3_ROW_COUNT_THRESHOLD",
    "EXPORT_ANOMALY_ROW_COUNT_THRESHOLD",
    "EXPORT_EVENT_EXTRA_ALLOWLIST",
    "clip_export_filter_scope",
    "emit_export_security_event_v1",
    "evaluate_export_anomaly_codes",
]
