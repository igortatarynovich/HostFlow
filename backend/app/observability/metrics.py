from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Set

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus

try:
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore
except Exception:  # pragma: no cover - prometheus not installed
    Counter = None  # type: ignore[assignment]
    Gauge = None  # type: ignore[assignment]
    Histogram = None  # type: ignore[assignment]


class _NoopMetric:
    def labels(self, *args, **kwargs):  # noqa: D401 - simple noop helper
        return self

    def inc(self, amount: float = 1.0) -> None:
        return None

    def set(self, value: float) -> None:
        return None

    def observe(self, value: float) -> None:
        return None


def _create_counter(name: str, description: str, labelnames: Iterable[str]):
    if Counter is None:  # pragma: no cover - no prometheus
        return _NoopMetric()
    return Counter(name, description, labelnames)  # type: ignore[no-any-return]


def _create_gauge(name: str, description: str, labelnames: Iterable[str]):
    if Gauge is None:  # pragma: no cover - no prometheus
        return _NoopMetric()
    return Gauge(name, description, labelnames)  # type: ignore[no-any-return]


def _create_histogram(name: str, description: str, labelnames: Iterable[str], buckets=None):
    if Histogram is None:  # pragma: no cover - no prometheus
        return _NoopMetric()
    return Histogram(name, description, labelnames, buckets=buckets)  # type: ignore[no-any-return]


documents_overdue_gauge = _create_gauge(
    "hf_documents_overdue_total",
    "Number of overdue documents per tenant and doc_type",
    ("tenant_id", "doc_type"),
)

reminders_triggered_counter = _create_counter(
    "hf_reminders_triggered_total",
    "Count of triggered reminders grouped by type and severity",
    ("tenant_id", "type", "severity"),
)

system_automation_workforce_lock_skip_counter = _create_counter(
    "hf_system_automation_workforce_lock_skip_total",
    "Candidate stage/status writes skipped because a WorkforceEmployee row exists",
    ("tenant_id", "source"),
)


def increment_system_automation_workforce_lock_skip(tenant_id: str, source: str) -> None:
    """Record that automation intentionally skipped a recruitment mutation (workforce lock)."""
    system_automation_workforce_lock_skip_counter.labels(
        tenant_id=tenant_id or "unknown",
        source=(source or "unknown").strip() or "unknown",
    ).inc()

_documents_overdue_index: Dict[str, Set[str]] = defaultdict(set)


def set_documents_overdue_counts(tenant_id: str, counts: Dict[str, int]) -> None:
    """
    Update gauge for overdue documents. Ensures old label combinations are reset to zero.
    """
    previous = _documents_overdue_index.get(tenant_id, set())
    current = set(counts.keys())

    for doc_type, value in counts.items():
        documents_overdue_gauge.labels(tenant_id=tenant_id, doc_type=doc_type).set(value)

    for doc_type in previous - current:
        documents_overdue_gauge.labels(tenant_id=tenant_id, doc_type=doc_type).set(0)

    _documents_overdue_index[tenant_id] = current


async def refresh_documents_overdue_metrics(db: AsyncSession, tenant_id: str) -> None:
    """
    Recalculate overdue document counts for the tenant and push them to Prometheus.
    """
    if Counter is None and Gauge is None:  # metrics disabled
        return

    rows = await db.execute(
        select(Document.doc_type, func.count())
        .where(
            Document.tenant_id == tenant_id,
            Document.deleted_at.is_(None),
            Document.status == DocumentStatus.overdue,
        )
        .group_by(Document.doc_type)
    )
    counts = {row[0]: int(row[1]) for row in rows.all()}
    set_documents_overdue_counts(tenant_id, counts)


def increment_reminder_triggered(tenant_id: str, reminder_type: str, severity: str) -> None:
    """
    Increment reminder counter with guard for missing prometheus client.
    """
    reminders_triggered_counter.labels(
        tenant_id=tenant_id,
        type=reminder_type,
        severity=severity or "unknown",
    ).inc()


# Document workflow duration histogram
documents_workflow_duration = _create_histogram(
    "hf_documents_workflow_duration_seconds",
    "Time taken for document workflow steps",
    ("tenant_id", "doc_type", "step_code"),
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0),
)

# Leads conversion rate gauge
leads_conversion_rate = _create_gauge(
    "hf_leads_conversion_rate",
    "Lead conversion rate by stage and source",
    ("tenant_id", "source", "stage"),
)

# Notifications unread gauge
notifications_unread = _create_gauge(
    "hf_notifications_unread_total",
    "Number of unread notifications per tenant and role",
    ("tenant_id", "role"),
)

# Tenant seats usage gauge
tenant_seats_used = _create_gauge(
    "hf_tenant_seats_used",
    "Number of used seats per tenant and role",
    ("tenant_id", "role"),
)

# Tenant license expiry gauge
tenant_license_expiry_days = _create_gauge(
    "hf_tenant_license_expiry_days",
    "Days until license expiry per tenant",
    ("tenant_id",),
)

# Calendar integration maintenance metrics
calendar_sync_lag_seconds = _create_gauge(
    "hf_calendar_sync_lag_seconds",
    "Estimated calendar sync lag in seconds per tenant",
    ("tenant_id",),
)

calendar_maintenance_queued_total = _create_counter(
    "hf_calendar_maintenance_queued_total",
    "Calendar maintenance jobs queued by type",
    ("tenant_id", "job_type"),
)

calendar_maintenance_errors_total = _create_counter(
    "hf_calendar_maintenance_errors_total",
    "Calendar maintenance errors by type",
    ("tenant_id", "error_type"),
)

_notifications_unread_index: Dict[str, Set[str]] = defaultdict(set)
_tenant_seats_index: Dict[str, Set[str]] = defaultdict(set)


def set_notifications_unread_count(tenant_id: str, counts: Dict[str, int]) -> None:
    """
    Update gauge for unread notifications. Ensures old label combinations are reset to zero.
    """
    previous = _notifications_unread_index.get(tenant_id, set())
    current = set(counts.keys())

    for role, value in counts.items():
        notifications_unread.labels(tenant_id=tenant_id, role=role).set(value)

    for role in previous - current:
        notifications_unread.labels(tenant_id=tenant_id, role=role).set(0)

    _notifications_unread_index[tenant_id] = current


def set_tenant_seats_used(tenant_id: str, counts: Dict[str, int]) -> None:
    """
    Update gauge for tenant seat usage. Ensures old label combinations are reset to zero.
    """
    previous = _tenant_seats_index.get(tenant_id, set())
    current = set(counts.keys())

    for role, value in counts.items():
        tenant_seats_used.labels(tenant_id=tenant_id, role=role).set(value)

    for role in previous - current:
        tenant_seats_used.labels(tenant_id=tenant_id, role=role).set(0)

    _tenant_seats_index[tenant_id] = current


def set_tenant_license_expiry_days(tenant_id: str, days: int) -> None:
    """
    Update gauge for tenant license expiry days.
    """
    tenant_license_expiry_days.labels(tenant_id=tenant_id).set(days)


def set_calendar_sync_lag_seconds(tenant_id: str, lag_seconds: int) -> None:
    calendar_sync_lag_seconds.labels(tenant_id=tenant_id).set(max(0, int(lag_seconds or 0)))


def increment_calendar_maintenance_queued(tenant_id: str, job_type: str) -> None:
    calendar_maintenance_queued_total.labels(
        tenant_id=tenant_id,
        job_type=(job_type or "unknown"),
    ).inc()


def increment_calendar_maintenance_error(tenant_id: str, error_type: str) -> None:
    calendar_maintenance_errors_total.labels(
        tenant_id=tenant_id,
        error_type=(error_type or "unknown"),
    ).inc()


def observe_document_workflow_duration(
    tenant_id: str,
    doc_type: str,
    step_code: str,
    duration_seconds: float,
) -> None:
    """
    Record document workflow step duration.
    """
    documents_workflow_duration.labels(
        tenant_id=tenant_id,
        doc_type=doc_type,
        step_code=step_code,
    ).observe(duration_seconds)


def set_leads_conversion_rate(
    tenant_id: str,
    source: str,
    stage: str,
    rate: float,
) -> None:
    """
    Set lead conversion rate for a specific source and stage.
    Rate should be between 0.0 and 1.0.
    """
    leads_conversion_rate.labels(
        tenant_id=tenant_id,
        source=source,
        stage=stage,
    ).set(rate)
