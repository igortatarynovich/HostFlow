"""Marketing Source Diagnostics API — list + case (+ filters / duplicate / mapping / export / drift)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.ops.source_diagnostics import (
    build_diagnostic_export_bundle,
    get_diagnostic_case,
    list_diagnostic_submissions,
    summarize_mapping_drift_alerts,
)
from backend.app.auth.deps import Role, UserCtx, get_current_user, require_roles
from backend.app.db.deps import get_db_with_tenant
from backend.app.security.event_taxonomy import (
    EVENT_EXPORT_DENIED,
    EVENT_EXPORT_GENERATED,
    EVENT_EXPORT_REQUESTED,
)
from backend.app.security.export_events import (
    clip_export_filter_scope,
    emit_export_security_event_v1,
)

router = APIRouter(
    prefix="/platform/marketing/diagnostics",
    tags=["marketing-diagnostics"],
    redirect_slashes=False,
)

_READ = [
    Depends(
        require_roles(
            Role.administrator,
            Role.supervisor,
            Role.recruiter,
            Role.client_manager,
            Role.viewer,
            Role.hr_officer,
            Role.superadmin,
        )
    )
]

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200
_DEFAULT_DRIFT_WINDOW_HOURS = 168
_MAX_DRIFT_WINDOW_HOURS = 24 * 30


class DiagnosticsCursorOut(BaseModel):
    created_at: datetime
    id: str


class DiagnosticsDriftSummaryOut(BaseModel):
    drift_count: int = 0
    window_hours: int = _DEFAULT_DRIFT_WINDOW_HOURS
    scanned: int = 0
    scan_capped: bool = False
    # Deep-link path for SPA (relative to CRM shell).
    diagnostics_href: str = "/app/marketing/diagnostics?drift_only=1"


class DiagnosticsSubmissionOut(BaseModel):
    lead_id: str
    created_at: Optional[datetime] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    lead_status: str = ""
    disposition: Optional[str] = None
    status_label: str = ""
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    route_intent: Optional[str] = None
    routing_status: Optional[str] = None
    source: Optional[str] = None
    # PR7: True when mapping_applied_v1 fingerprint ≠ current Source rules; null if no stamp.
    mapping_drift: Optional[bool] = None


class DiagnosticsListOut(BaseModel):
    items: list[DiagnosticsSubmissionOut]
    next_cursor: Optional[DiagnosticsCursorOut] = None
    drift_alert_count: int = 0


class DiagnosticsTimelineEventOut(BaseModel):
    id: str
    event_type: str
    occurred_at: datetime
    campaign_id: str
    flight_id: Optional[str] = None
    submission_id: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class DiagnosticsDuplicateOut(BaseModel):
    active: bool = False
    lead_status: str = ""
    disposition: Optional[str] = None
    match_level: Optional[str] = None
    suggested_candidate_id: Optional[str] = None
    attach_candidate_id: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)
    hr_blockers: list[str] = Field(default_factory=list)
    error_code: Optional[str] = None
    needs_duplicate_review: bool = False
    stamped_at: Optional[str] = None


class DiagnosticsMappingOut(BaseModel):
    active: bool = False
    source_id: Optional[str] = None
    display_name: Optional[str] = None
    provider: Optional[str] = None
    mapping_health: Optional[str] = None
    mapping_rules_count: int = 0
    rules_source: Optional[str] = None
    meta_form_id: Optional[str] = None
    mapping_path: Optional[str] = None
    profile_updated_at: Optional[str] = None
    historical_version_available: bool = False
    profile_missing: bool = False
    applied_rules_count: int = 0
    applied_rules_fingerprint: Optional[str] = None
    applied_rules_source: Optional[str] = None
    applied_stamped_at: Optional[str] = None
    current_rules_fingerprint: Optional[str] = None
    drift: bool = False


class DiagnosticsCaseOut(BaseModel):
    lead_id: str
    created_at: Optional[datetime] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    lead_status: str = ""
    disposition: Optional[str] = None
    status_label: str = ""
    candidate_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    route_intent: Optional[str] = None
    routing_status: Optional[str] = None
    source: Optional[str] = None
    submission_id: Optional[str] = None
    campaign_id: Optional[str] = None
    flight_id: Optional[str] = None
    routing: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)
    normalized: dict[str, Any] = Field(default_factory=dict)
    lead_error: Optional[str] = None
    duplicate: DiagnosticsDuplicateOut = Field(default_factory=DiagnosticsDuplicateOut)
    mapping: DiagnosticsMappingOut = Field(default_factory=DiagnosticsMappingOut)
    timeline: list[DiagnosticsTimelineEventOut] = Field(default_factory=list)


def _require_uuid(value: str, *, field: str) -> str:
    raw = str(value or "").strip()
    try:
        return str(UUID(raw))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid {field}") from exc


@router.get("/drift-summary", response_model=DiagnosticsDriftSummaryOut, dependencies=_READ)
async def get_drift_summary(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    window_hours: int = Query(
        default=_DEFAULT_DRIFT_WINDOW_HOURS,
        ge=1,
        le=_MAX_DRIFT_WINDOW_HOURS,
    ),
) -> DiagnosticsDriftSummaryOut:
    """In-app Mapping Health drift alert count (PR9) — no email/webhook."""
    db, tenant_id = db_tenant
    summary = await summarize_mapping_drift_alerts(
        db,
        tenant_id=str(tenant_id),
        window_hours=int(window_hours),
    )
    return DiagnosticsDriftSummaryOut(
        drift_count=summary.drift_count,
        window_hours=summary.window_hours,
        scanned=summary.scanned,
        scan_capped=summary.scan_capped,
        diagnostics_href="/app/marketing/diagnostics?drift_only=1",
    )


@router.get("/submissions", response_model=DiagnosticsListOut, dependencies=_READ)
async def list_submissions(
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    after_created_at: Optional[datetime] = Query(default=None),
    after_id: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None, max_length=64),
    flight_id: Optional[str] = Query(default=None),
    failed_only: bool = Query(default=False),
    drift_only: bool = Query(default=False),
) -> DiagnosticsListOut:
    db, tenant_id = db_tenant
    cursor_id = _require_uuid(after_id, field="after_id") if after_id is not None else None
    flight = (
        _require_uuid(flight_id, field="flight_id") if flight_id is not None and str(flight_id).strip() else None
    )
    try:
        rows, cursor = await list_diagnostic_submissions(
            db,
            tenant_id=str(tenant_id),
            limit=limit,
            after_created_at=after_created_at,
            after_id=cursor_id,
            source=source,
            flight_id=flight,
            failed_only=bool(failed_only),
            drift_only=bool(drift_only),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    drift_alert_count = sum(1 for row in rows if row.mapping_drift is True)
    return DiagnosticsListOut(
        items=[
            DiagnosticsSubmissionOut(
                lead_id=row.applicant.lead_id,
                created_at=row.applicant.created_at,
                full_name=row.applicant.full_name,
                phone=row.applicant.phone,
                email=row.applicant.email,
                lead_status=row.applicant.lead_status,
                disposition=row.applicant.disposition,
                status_label=row.applicant.status_label,
                candidate_id=row.applicant.candidate_id,
                vacancy_id=row.applicant.vacancy_id,
                route_intent=row.applicant.route_intent,
                routing_status=row.applicant.routing_status,
                source=row.applicant.source,
                mapping_drift=row.mapping_drift,
            )
            for row in rows
        ],
        next_cursor=(
            DiagnosticsCursorOut(created_at=cursor[0], id=cursor[1]) if cursor else None
        ),
        drift_alert_count=drift_alert_count,
    )


@router.get(
    "/submissions/{lead_id}",
    response_model=DiagnosticsCaseOut,
    dependencies=_READ,
)
async def get_submission_case(
    lead_id: str,
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> DiagnosticsCaseOut:
    db, tenant_id = db_tenant
    lid = _require_uuid(lead_id, field="lead_id")
    detail = await get_diagnostic_case(db, tenant_id=str(tenant_id), lead_id=lid)
    if detail is None:
        raise HTTPException(status_code=404, detail="submission_not_found")
    app = detail.applicant
    dup = detail.duplicate
    return DiagnosticsCaseOut(
        lead_id=app.lead_id,
        created_at=app.created_at,
        full_name=app.full_name,
        phone=app.phone,
        email=app.email,
        lead_status=app.lead_status,
        disposition=app.disposition,
        status_label=app.status_label,
        candidate_id=app.candidate_id,
        vacancy_id=app.vacancy_id,
        route_intent=app.route_intent,
        routing_status=app.routing_status,
        source=app.source,
        submission_id=detail.submission_id,
        campaign_id=detail.campaign_id,
        flight_id=detail.flight_id,
        routing=detail.routing,
        decision=detail.decision,
        payload=detail.payload,
        normalized=detail.normalized,
        lead_error=detail.lead_error,
        duplicate=DiagnosticsDuplicateOut(
            active=dup.active,
            lead_status=dup.lead_status,
            disposition=dup.disposition,
            match_level=dup.match_level,
            suggested_candidate_id=dup.suggested_candidate_id,
            attach_candidate_id=dup.attach_candidate_id,
            reasons=list(dup.reasons),
            hr_blockers=list(dup.hr_blockers),
            error_code=dup.error_code,
            needs_duplicate_review=dup.needs_duplicate_review,
            stamped_at=dup.stamped_at,
        ),
        mapping=DiagnosticsMappingOut(
            active=detail.mapping.active,
            source_id=detail.mapping.source_id,
            display_name=detail.mapping.display_name,
            provider=detail.mapping.provider,
            mapping_health=detail.mapping.mapping_health,
            mapping_rules_count=detail.mapping.mapping_rules_count,
            rules_source=detail.mapping.rules_source,
            meta_form_id=detail.mapping.meta_form_id,
            mapping_path=detail.mapping.mapping_path,
            profile_updated_at=detail.mapping.profile_updated_at,
            historical_version_available=detail.mapping.historical_version_available,
            profile_missing=detail.mapping.profile_missing,
            applied_rules_count=detail.mapping.applied_rules_count,
            applied_rules_fingerprint=detail.mapping.applied_rules_fingerprint,
            applied_rules_source=detail.mapping.applied_rules_source,
            applied_stamped_at=detail.mapping.applied_stamped_at,
            current_rules_fingerprint=detail.mapping.current_rules_fingerprint,
            drift=detail.mapping.drift,
        ),
        timeline=[
            DiagnosticsTimelineEventOut(
                id=str(ev.id),
                event_type=str(ev.event_type),
                occurred_at=ev.occurred_at,
                campaign_id=str(ev.campaign_id),
                flight_id=str(ev.flight_id) if ev.flight_id else None,
                submission_id=str(ev.submission_id) if ev.submission_id else None,
                payload=dict(ev.payload or {}),
            )
            for ev in detail.timeline
        ],
    )


@router.get(
    "/submissions/{lead_id}/export",
    dependencies=_READ,
)
async def export_submission_case(
    lead_id: str,
    ctx: UserCtx = Depends(get_current_user),
    db_tenant: tuple[AsyncSession, UUID] = Depends(get_db_with_tenant),
) -> Response:
    """Download a single diagnostics case as JSON (ops support; audited export)."""
    db, tenant_id = db_tenant
    lid = _require_uuid(lead_id, field="lead_id")
    access_kind = str(db.info.get("security_access_kind") or "").strip() or None
    tenant_s = str(tenant_id)
    _src = "http:marketing.diagnostics:export_case"
    _et = "marketing_diagnostics_case_json"
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_REQUESTED,
        result="success",
        severity="info",
        source=_src,
        tenant_id=tenant_s,
        access_kind=access_kind,
        entity_type="lead",
        entity_id=lid,
        export_type=_et,
        actor_id=str(ctx.sub),
        filter_scope=clip_export_filter_scope(f"diagnostics_case:{lid}"),
        export_scope="single_lead_diagnostics",
        contains_class3=True,
        bulk_operation=False,
    )
    detail = await get_diagnostic_case(db, tenant_id=tenant_s, lead_id=lid)
    if detail is None:
        emit_export_security_event_v1(
            event_type=EVENT_EXPORT_DENIED,
            result="denied",
            severity="low",
            source=_src,
            tenant_id=tenant_s,
            access_kind=access_kind,
            entity_type="lead",
            entity_id=lid,
            export_type=_et,
            actor_id=str(ctx.sub),
            filter_scope=clip_export_filter_scope(f"diagnostics_case:{lid}"),
            export_scope="single_lead_diagnostics",
            contains_class3=True,
            bulk_operation=False,
            reason="submission_not_found",
            response_mode="attachment_json",
        )
        raise HTTPException(status_code=404, detail="submission_not_found")

    bundle = build_diagnostic_export_bundle(detail)
    body = json.dumps(bundle, ensure_ascii=False, default=str, indent=2).encode("utf-8")
    emit_export_security_event_v1(
        event_type=EVENT_EXPORT_GENERATED,
        result="success",
        severity="info",
        source=_src,
        tenant_id=tenant_s,
        access_kind=access_kind,
        entity_type="lead",
        entity_id=lid,
        export_type=_et,
        actor_id=str(ctx.sub),
        row_count=1,
        byte_size=len(body),
        filter_scope=clip_export_filter_scope(f"diagnostics_case:{lid}"),
        export_scope="single_lead_diagnostics",
        contains_class3=True,
        bulk_operation=False,
        response_mode="attachment_json",
    )
    filename = f"diagnostics-case-{lid}.json"
    return Response(
        content=body,
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
