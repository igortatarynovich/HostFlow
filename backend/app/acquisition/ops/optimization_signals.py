"""Stage 5 PR-1 — Flight optimization signals (read-only).

Composes Stage 4 ``get_flight_runtime_snapshot`` identity/status/KPI strip with
**windowed** Activity Timeline counters (same allowlist as Live Intake Monitor).
Does **not** invent a second metrics store, emit Activity on GET, or mutate
Campaign/Flight.

Canon: docs/specs/tasks/acquisition-stage-5-optimization.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.flights.runtime_commands import FlightRuntimeError
from backend.app.acquisition.ops.runtime_read import get_flight_runtime_snapshot
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent

# Subset of Live Intake Monitor allowlist — windowed counts only (Timeline SoT).
_SIGNAL_EVENT_TYPES: tuple[str, ...] = (
    "SubmissionReceived",
    "RoutingCompleted",
    "RoutingFailed",
    "DeliveryErrorOccurred",
)

# --- Locked thresholds (PR-1) -------------------------------------------------

DEFAULT_WINDOW_HOURS = 24
MIN_WINDOW_HOURS = 1
MAX_WINDOW_HOURS = 168

# Minimum intake/routing/delivery observations in the window before deciding.
MIN_DECISION_VOLUME = 5

# Routing fail rate threshold (inclusive — exactly on threshold → suggest_pause).
ROUTING_FAIL_RATE_THRESHOLD = 0.50
MIN_ROUTING_SAMPLE = 5

# Absolute DeliveryErrorOccurred count in window (inclusive).
DELIVERY_ERROR_THRESHOLD = 3

Assessment = Literal["insufficient_data", "healthy", "suggest_pause"]
RecommendedAction = Literal["none", "suggest_pause"]
SignalSeverity = Literal["info", "warn", "critical"]


@dataclass(frozen=True)
class OptimizationSignal:
    code: str
    severity: SignalSeverity
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass(frozen=True)
class WindowCounters:
    """Windowed Activity counts — not a second KPI ledger."""

    submissions: int
    routing_completed: int
    routing_failed: int
    delivery_errors: int

    @property
    def routing_sample(self) -> int:
        return int(self.routing_completed) + int(self.routing_failed)

    @property
    def decision_volume(self) -> int:
        return (
            int(self.submissions)
            + int(self.routing_completed)
            + int(self.routing_failed)
            + int(self.delivery_errors)
        )

    @property
    def routing_fail_rate(self) -> float | None:
        n = self.routing_sample
        if n <= 0:
            return None
        return float(self.routing_failed) / float(n)

    def to_dict(self) -> dict[str, int]:
        return {
            "submissions": self.submissions,
            "routing_completed": self.routing_completed,
            "routing_failed": self.routing_failed,
            "delivery_errors": self.delivery_errors,
            "routing_sample": self.routing_sample,
            "decision_volume": self.decision_volume,
        }


@dataclass(frozen=True)
class OptimizationInputs:
    """Deterministic inputs for ``evaluate_flight_optimization`` (no I/O)."""

    campaign_id: str
    flight_id: str
    campaign_status: str
    flight_status: str
    window_hours: int
    window_start: datetime
    window_end: datetime
    counters: WindowCounters
    # KPI strip from Stage 4 runtime (SoT for spend/leads) — informational only.
    kpi_leads: int
    spend: str


@dataclass(frozen=True)
class FlightOptimizationSnapshot:
    tenant_id: str
    campaign_id: str
    flight_id: str
    campaign_status: str
    flight_status: str
    assessment: Assessment
    recommended_action: RecommendedAction
    reason_codes: tuple[str, ...]
    signals: tuple[OptimizationSignal, ...]
    window_hours: int
    window_start: datetime
    window_end: datetime
    counters: WindowCounters
    kpi_leads: int
    spend: str
    generated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "campaign_id": self.campaign_id,
            "flight_id": self.flight_id,
            "campaign_status": self.campaign_status,
            "flight_status": self.flight_status,
            "assessment": self.assessment,
            "recommended_action": self.recommended_action,
            "reason_codes": list(self.reason_codes),
            "signals": [s.to_dict() for s in self.signals],
            "window_hours": self.window_hours,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "counters": self.counters.to_dict(),
            "kpi_leads": self.kpi_leads,
            "spend": self.spend,
            "generated_at": self.generated_at.isoformat(),
            "thresholds": {
                "min_decision_volume": MIN_DECISION_VOLUME,
                "routing_fail_rate_threshold": ROUTING_FAIL_RATE_THRESHOLD,
                "min_routing_sample": MIN_ROUTING_SAMPLE,
                "delivery_error_threshold": DELIVERY_ERROR_THRESHOLD,
            },
        }


def clamp_window_hours(raw: int | None) -> int:
    hours = int(raw if raw is not None else DEFAULT_WINDOW_HOURS)
    return max(MIN_WINDOW_HOURS, min(hours, MAX_WINDOW_HOURS))


def evaluate_flight_optimization(
    inputs: OptimizationInputs,
    *,
    tenant_id: str = "",
    generated_at: datetime | None = None,
) -> FlightOptimizationSnapshot:
    """Pure threshold evaluation — no DB, no mutations."""
    now = generated_at or datetime.now(timezone.utc)
    reasons: list[str] = []
    signals: list[OptimizationSignal] = []
    status = str(inputs.flight_status or "").strip().lower()
    counters = inputs.counters

    if status != "active":
        reasons.append("flight_not_active")
        signals.append(
            OptimizationSignal(
                code="flight_not_active",
                severity="info",
                message=f"Flight status is '{inputs.flight_status}'; pause recommendation applies only while active.",
            )
        )
        return _snapshot(
            inputs,
            tenant_id=tenant_id,
            assessment="insufficient_data",
            recommended_action="none",
            reason_codes=tuple(reasons),
            signals=tuple(signals),
            generated_at=now,
        )

    if counters.decision_volume < MIN_DECISION_VOLUME:
        reasons.append("insufficient_volume")
        signals.append(
            OptimizationSignal(
                code="insufficient_volume",
                severity="info",
                message=(
                    f"Need at least {MIN_DECISION_VOLUME} intake/routing/delivery "
                    f"observations in the window (have {counters.decision_volume})."
                ),
            )
        )
        return _snapshot(
            inputs,
            tenant_id=tenant_id,
            assessment="insufficient_data",
            recommended_action="none",
            reason_codes=tuple(reasons),
            signals=tuple(signals),
            generated_at=now,
        )

    pause = False
    rate = counters.routing_fail_rate
    if (
        counters.routing_sample >= MIN_ROUTING_SAMPLE
        and rate is not None
        and rate >= ROUTING_FAIL_RATE_THRESHOLD
    ):
        pause = True
        reasons.append("routing_fail_rate")
        signals.append(
            OptimizationSignal(
                code="routing_fail_rate",
                severity="critical",
                message=(
                    f"Routing fail rate {rate:.2f} "
                    f"({counters.routing_failed}/{counters.routing_sample}) "
                    f">= {ROUTING_FAIL_RATE_THRESHOLD:.2f}."
                ),
            )
        )

    if counters.delivery_errors >= DELIVERY_ERROR_THRESHOLD:
        pause = True
        reasons.append("delivery_errors")
        signals.append(
            OptimizationSignal(
                code="delivery_errors",
                severity="warn",
                message=(
                    f"DeliveryErrorOccurred count {counters.delivery_errors} "
                    f">= {DELIVERY_ERROR_THRESHOLD} in window."
                ),
            )
        )

    if pause:
        assessment: Assessment = "suggest_pause"
        action: RecommendedAction = "suggest_pause"
    else:
        assessment = "healthy"
        action = "none"
        reasons.append("within_thresholds")
        signals.append(
            OptimizationSignal(
                code="within_thresholds",
                severity="info",
                message="Intake/routing/delivery counters are within pause thresholds for this window.",
            )
        )

    return _snapshot(
        inputs,
        tenant_id=tenant_id,
        assessment=assessment,
        recommended_action=action,
        reason_codes=tuple(reasons),
        signals=tuple(signals),
        generated_at=now,
    )


def _snapshot(
    inputs: OptimizationInputs,
    *,
    tenant_id: str,
    assessment: Assessment,
    recommended_action: RecommendedAction,
    reason_codes: tuple[str, ...],
    signals: tuple[OptimizationSignal, ...],
    generated_at: datetime,
) -> FlightOptimizationSnapshot:
    return FlightOptimizationSnapshot(
        tenant_id=str(tenant_id),
        campaign_id=str(inputs.campaign_id),
        flight_id=str(inputs.flight_id),
        campaign_status=str(inputs.campaign_status),
        flight_status=str(inputs.flight_status),
        assessment=assessment,
        recommended_action=recommended_action,
        reason_codes=reason_codes,
        signals=signals,
        window_hours=int(inputs.window_hours),
        window_start=inputs.window_start,
        window_end=inputs.window_end,
        counters=inputs.counters,
        kpi_leads=int(inputs.kpi_leads),
        spend=str(inputs.spend),
        generated_at=generated_at,
    )


async def _windowed_activity_counts(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    occurred_after: datetime,
) -> WindowCounters:
    """Count allowlisted Timeline events in the observation window only."""
    stmt = (
        select(AcquisitionActivityEvent.event_type, func.count())
        .where(
            AcquisitionActivityEvent.tenant_id == str(tenant_id),
            AcquisitionActivityEvent.campaign_id == str(campaign_id),
            AcquisitionActivityEvent.flight_id == str(flight_id),
            AcquisitionActivityEvent.event_type.in_(list(_SIGNAL_EVENT_TYPES)),
            AcquisitionActivityEvent.occurred_at > occurred_after,
        )
        .group_by(AcquisitionActivityEvent.event_type)
    )
    rows = await db.execute(stmt)
    counts = {str(et): int(n) for et, n in rows.all()}
    return WindowCounters(
        submissions=counts.get("SubmissionReceived", 0),
        routing_completed=counts.get("RoutingCompleted", 0),
        routing_failed=counts.get("RoutingFailed", 0),
        delivery_errors=counts.get("DeliveryErrorOccurred", 0),
    )


async def get_flight_optimization(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    flight_id: str,
    own_company_id: str | None = None,
    window_hours: int | None = None,
    now: datetime | None = None,
) -> FlightOptimizationSnapshot:
    """Read-only compose: Stage 4 runtime snapshot + windowed Timeline counters."""
    hours = clamp_window_hours(window_hours)
    end = now or datetime.now(timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    start = end - timedelta(hours=hours)

    try:
        runtime = await get_flight_runtime_snapshot(
            db,
            tenant_id=str(tenant_id),
            campaign_id=str(campaign_id),
            flight_id=str(flight_id),
            own_company_id=own_company_id,
        )
    except FlightRuntimeError:
        raise

    counters = await _windowed_activity_counts(
        db,
        tenant_id=str(tenant_id),
        campaign_id=str(runtime.campaign_id),
        flight_id=str(runtime.flight_id),
        occurred_after=start,
    )
    inputs = OptimizationInputs(
        campaign_id=runtime.campaign_id,
        flight_id=runtime.flight_id,
        campaign_status=runtime.campaign_status,
        flight_status=runtime.flight_status,
        window_hours=hours,
        window_start=start,
        window_end=end,
        counters=counters,
        kpi_leads=int(runtime.kpi.leads),
        spend=str(runtime.kpi.spend),
    )
    return evaluate_flight_optimization(
        inputs, tenant_id=str(tenant_id), generated_at=end
    )


__all__ = [
    "DEFAULT_WINDOW_HOURS",
    "DELIVERY_ERROR_THRESHOLD",
    "MIN_DECISION_VOLUME",
    "MIN_ROUTING_SAMPLE",
    "MIN_WINDOW_HOURS",
    "MAX_WINDOW_HOURS",
    "ROUTING_FAIL_RATE_THRESHOLD",
    "Assessment",
    "FlightOptimizationSnapshot",
    "OptimizationInputs",
    "OptimizationSignal",
    "RecommendedAction",
    "WindowCounters",
    "clamp_window_hours",
    "evaluate_flight_optimization",
    "get_flight_optimization",
]
