"""Sales-owned binders: GDPR notice + operational emails → Communication Pipeline.

Ensures SalesInquiry + email Thread Result Link + G13. Does not send mail.
Must not invent Recruitment Application context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.candidate_activity import read_acquisition_routing_stamp
from backend.app.acquisition.flights.destination_contract import OpaqueResultRef
from backend.app.communications.entity_link import ensure_thread_entity_link
from backend.app.communications.result_link import (
    ThreadResultLinkError,
    attach_thread_result_link,
)
from backend.app.communications.template_metadata import (
    CommunicationTemplateMetadata,
    build_template_metadata,
)
from backend.app.models.communication import CommunicationThread
from backend.app.models.communication_thread_result_link import (
    LINK_STATUS_CONFIRMED,
    CommunicationThreadResultLink,
)
from backend.app.models.lead import Lead
from backend.app.models.sales_inquiry import SalesInquiry
from backend.app.modules.sales.communication.policy_adapter import POLICY_VERSION
from backend.app.modules.sales.services.sales_inquiry_service import (
    SalesInquiryTransportConflictError,
    ensure_sales_inquiry_for_transport_lead,
)

PURPOSE_GDPR_NOTICE = "gdpr_notice"
PURPOSE_SUBMISSION_ACK = "submission_acknowledgement"
PURPOSE_INTAKE_REJECTION = "intake_rejection_notice"
PURPOSE_MOVING_FORWARD = "moving_forward_notice"

TEMPLATE_GDPR = ("tpl_sales_gdpr_notice_v1", "1")
TEMPLATE_SUBMISSION_ACK = ("tpl_sales_submission_acknowledgement_v1", "1")
TEMPLATE_REJECTION = ("tpl_sales_intake_rejection_notice_v1", "1")
TEMPLATE_MOVING_FORWARD = ("tpl_sales_moving_forward_notice_v1", "1")

CompliancePurpose = Literal[
    "gdpr_notice",
    "submission_acknowledgement",
    "intake_rejection_notice",
    "moving_forward_notice",
]


class SalesCompliancePipelineError(Exception):
    code = "sales_compliance_pipeline_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class SalesCompliancePipelineBinding:
    thread_id: str
    sales_inquiry_id: str
    communication_purpose: str
    template: CommunicationTemplateMetadata
    locale: str | None


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def lead_is_sales_destination(lead: Lead) -> bool:
    """True when transport Lead is Sales-bound (not Recruitment Application)."""
    link = _record(_record(getattr(lead, "normalized", None)).get("intake_result_link_v1"))
    if link.get("application_id") or str(link.get("result_type") or "") == "application":
        return False
    if link.get("sales_inquiry_id") or str(link.get("result_type") or "") == "sales_inquiry":
        return True
    stamp = read_acquisition_routing_stamp(lead)
    route = str(stamp.get("route_intent") or "").strip().lower()
    if route in {"sales_inquiry", "client_inquiry", "inquiry"}:
        return True
    return False


async def resolve_lead_uses_sales_compliance_pipeline(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> bool:
    """Sales compliance/ops path: stamp/link OR existing SalesInquiry (never Application)."""
    if lead_is_sales_destination(lead):
        return True
    link = _record(_record(getattr(lead, "normalized", None)).get("intake_result_link_v1"))
    if link.get("application_id") or str(link.get("result_type") or "") == "application":
        return False
    tid = str(tenant_id).strip()
    lid = str(getattr(lead, "id", "") or "").strip()
    if not lid:
        return False
    existing = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.tenant_id == tid, SalesInquiry.lead_id == lid)
        .limit(1)
    )
    return existing is not None


def _template_for_purpose(purpose: CompliancePurpose) -> CommunicationTemplateMetadata:
    mapping: dict[str, tuple[str, str]] = {
        PURPOSE_GDPR_NOTICE: TEMPLATE_GDPR,
        PURPOSE_SUBMISSION_ACK: TEMPLATE_SUBMISSION_ACK,
        PURPOSE_INTAKE_REJECTION: TEMPLATE_REJECTION,
        PURPOSE_MOVING_FORWARD: TEMPLATE_MOVING_FORWARD,
    }
    tid, ver = mapping[purpose]
    return build_template_metadata(
        template_id=tid,
        template_version=ver,
        module_owner="sales",
        communication_domain="sales",
        communication_purpose=purpose,
        supported_channels=["email"],
        supported_locales=["pl", "en", "ru", "uk", "de"],
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
    )


def purpose_for_ops_event(event_type: str) -> CompliancePurpose | None:
    ev = str(event_type or "").strip().lower()
    if ev == "application_received":
        return PURPOSE_SUBMISSION_ACK
    if ev == "lead_rejected":
        return PURPOSE_INTAKE_REJECTION
    if ev == "moving_forward":
        return PURPOSE_MOVING_FORWARD
    return None


async def _load_sales_inquiry_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    source: str,
) -> SalesInquiry:
    tid = str(tenant_id).strip()
    lid = str(getattr(lead, "id", "") or "").strip()
    link = _record(_record(getattr(lead, "normalized", None)).get("intake_result_link_v1"))
    if link.get("application_id") or str(link.get("result_type") or "") == "application":
        raise SalesCompliancePipelineError(
            "transport lead is bound to Recruitment Application; Sales compliance mail unavailable",
            details={
                "lead_id": lid,
                "reason": "recruitment_result_bound",
                "application_id": link.get("application_id"),
            },
        )

    existing_id = str(link.get("sales_inquiry_id") or "").strip()
    if existing_id:
        row = await db.get(SalesInquiry, existing_id)
        if row is not None and str(row.tenant_id) == tid:
            return row

    by_lead = await db.scalar(
        select(SalesInquiry)
        .where(SalesInquiry.tenant_id == tid, SalesInquiry.lead_id == lid)
        .limit(1)
    )
    if by_lead is not None:
        return by_lead

    if not lead_is_sales_destination(lead):
        raise SalesCompliancePipelineError(
            "transport lead is not a Sales destination; refuse to invent SalesInquiry",
            details={"lead_id": lid, "reason": "not_sales_destination"},
        )

    try:
        return await ensure_sales_inquiry_for_transport_lead(
            db,
            tenant_id=tid,
            lead=lead,
            source=source,
        )
    except SalesInquiryTransportConflictError as exc:
        raise SalesCompliancePipelineError(
            exc.message,
            details={**dict(exc.details), "reason": "sales_inquiry_transport_conflict"},
        ) from exc


async def _find_bound_email_thread_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    sales_inquiry_id: str,
) -> str | None:
    stmt = (
        select(CommunicationThreadResultLink.thread_id)
        .join(
            CommunicationThread,
            CommunicationThread.id == CommunicationThreadResultLink.thread_id,
        )
        .where(
            CommunicationThreadResultLink.tenant_id == tenant_id,
            CommunicationThreadResultLink.module_owner == "sales",
            CommunicationThreadResultLink.result_type == "sales_inquiry",
            CommunicationThreadResultLink.result_id == sales_inquiry_id,
            CommunicationThreadResultLink.status == LINK_STATUS_CONFIRMED,
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel == "email",
        )
        .order_by(CommunicationThreadResultLink.created_at.asc())
        .limit(1)
    )
    return await db.scalar(stmt)


async def ensure_sales_compliance_pipeline_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    purpose: CompliancePurpose,
    locale: str | None = None,
    actor_user_id: str | None = None,
    source: str = "sales.compliance_pipeline",
) -> SalesCompliancePipelineBinding:
    """Ensure Thread Result Link + return pipeline inputs for Sales compliance/ops email."""
    inquiry = await _load_sales_inquiry_for_lead(
        db, tenant_id=tenant_id, lead=lead, source=source
    )
    inquiry_id = str(inquiry.id)
    tid = str(tenant_id).strip()

    found = await _find_bound_email_thread_id(
        db, tenant_id=tid, sales_inquiry_id=inquiry_id
    )
    if found:
        resolved_thread_id = str(found)
    else:
        thread = CommunicationThread(
            id=str(uuid4()),
            tenant_id=tid,
            own_company_id=str(getattr(lead, "own_company_id", None) or "") or None,
            channel="email",
            subject=f"Sales · {purpose} · {inquiry_id[:8]}",
            status="open",
            direction_hint="outbound",
            entity_type="sales_inquiry",
            entity_id=inquiry_id,
            owner_id=str(actor_user_id).strip() if actor_user_id else None,
            thread_meta={
                "source": source,
                "sales_inquiry_id": inquiry_id,
                "transport_lead_id": str(lead.id),
                "communication_purpose": purpose,
            },
        )
        db.add(thread)
        await db.flush()
        opaque = OpaqueResultRef(
            module_owner="sales",
            result_type="sales_inquiry",
            result_id=inquiry_id,
        )
        try:
            await attach_thread_result_link(
                db,
                tenant_id=tid,
                thread_id=str(thread.id),
                opaque=opaque,
                meta={"source": source},
            )
        except ThreadResultLinkError as exc:
            raise SalesCompliancePipelineError(
                str(getattr(exc, "message", None) or exc),
                details={
                    **dict(getattr(exc, "details", None) or {}),
                    "reason": getattr(exc, "code", "thread_result_link_error"),
                },
            ) from exc
        resolved_thread_id = str(thread.id)

    await ensure_thread_entity_link(
        db,
        tenant_id=tid,
        thread_id=resolved_thread_id,
        entity_type="sales_inquiry",
        entity_id=inquiry_id,
        is_immutable=True,
    )
    await ensure_thread_entity_link(
        db,
        tenant_id=tid,
        thread_id=resolved_thread_id,
        entity_type="lead",
        entity_id=str(lead.id),
        is_immutable=True,
    )

    loc = str(locale or "").strip().lower()[:2] or None
    return SalesCompliancePipelineBinding(
        thread_id=resolved_thread_id,
        sales_inquiry_id=inquiry_id,
        communication_purpose=purpose,
        template=_template_for_purpose(purpose),
        locale=loc,
    )
