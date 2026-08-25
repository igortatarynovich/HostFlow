"""Sales-owned binder: questionnaire email → Communication Pipeline inputs.

Resolves SalesInquiry from the transport Lead, ensures an email Thread with a
confirmed Thread Result Link, and returns purpose + template metadata.

Does not send mail and does not invent Recruitment context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

PURPOSE_QUALIFICATION_QUESTIONNAIRE = "qualification_questionnaire_request"
TEMPLATE_ID = "tpl_sales_qualification_questionnaire_request_v1"
TEMPLATE_VERSION = "1"


class SalesQuestionnairePipelineError(Exception):
    code = "sales_questionnaire_pipeline_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class SalesQuestionnairePipelineBinding:
    thread_id: str
    sales_inquiry_id: str
    communication_purpose: str
    template: CommunicationTemplateMetadata
    locale: str | None


def sales_questionnaire_template_metadata() -> CommunicationTemplateMetadata:
    return build_template_metadata(
        template_id=TEMPLATE_ID,
        template_version=TEMPLATE_VERSION,
        module_owner="sales",
        communication_domain="sales",
        communication_purpose=PURPOSE_QUALIFICATION_QUESTIONNAIRE,
        supported_channels=["email"],
        supported_locales=["pl", "en", "ru", "uk", "de"],
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
    )


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


async def _load_sales_inquiry_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> SalesInquiry:
    tid = str(tenant_id).strip()
    lid = str(getattr(lead, "id", "") or "").strip()
    link = _record(_record(getattr(lead, "normalized", None)).get("intake_result_link_v1"))
    if link.get("application_id") or str(link.get("result_type") or "") == "application":
        raise SalesQuestionnairePipelineError(
            "transport lead is bound to Recruitment Application; Sales questionnaire unavailable",
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

    try:
        return await ensure_sales_inquiry_for_transport_lead(
            db,
            tenant_id=tid,
            lead=lead,
            source="questionnaire_email",
        )
    except SalesInquiryTransportConflictError as exc:
        raise SalesQuestionnairePipelineError(
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


async def ensure_sales_questionnaire_pipeline_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    locale: str | None = None,
    actor_user_id: str | None = None,
    thread_id: str | None = None,
) -> SalesQuestionnairePipelineBinding:
    """Ensure Thread Result Link + return pipeline inputs for questionnaire email."""
    inquiry = await _load_sales_inquiry_for_lead(db, tenant_id=tenant_id, lead=lead)
    inquiry_id = str(inquiry.id)
    tid = str(tenant_id).strip()

    resolved_thread_id = str(thread_id or "").strip() or None
    if resolved_thread_id:
        # Caller-supplied thread must already resolve as SalesInquiry via C1 link
        # (authorize step will enforce). We still attach if missing/compatible.
        opaque = OpaqueResultRef(
            module_owner="sales",
            result_type="sales_inquiry",
            result_id=inquiry_id,
        )
        try:
            await attach_thread_result_link(
                db,
                tenant_id=tid,
                thread_id=resolved_thread_id,
                opaque=opaque,
                meta={"source": "sales.questionnaire_pipeline"},
            )
        except ThreadResultLinkError as exc:
            raise SalesQuestionnairePipelineError(
                str(getattr(exc, "message", None) or exc),
                details={
                    **dict(getattr(exc, "details", None) or {}),
                    "reason": getattr(exc, "code", "thread_result_link_error"),
                },
            ) from exc
    else:
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
                subject=f"Sales questionnaire · {inquiry_id[:8]}",
                status="open",
                direction_hint="outbound",
                entity_type="sales_inquiry",
                entity_id=inquiry_id,
                owner_id=str(actor_user_id).strip() if actor_user_id else None,
                thread_meta={
                    "source": "sales.questionnaire_pipeline",
                    "sales_inquiry_id": inquiry_id,
                    "transport_lead_id": str(lead.id),
                },
            )
            db.add(thread)
            await db.flush()
            opaque = OpaqueResultRef(
                module_owner="sales",
                result_type="sales_inquiry",
                result_id=inquiry_id,
            )
            await attach_thread_result_link(
                db,
                tenant_id=tid,
                thread_id=str(thread.id),
                opaque=opaque,
                meta={"source": "sales.questionnaire_pipeline"},
            )
            resolved_thread_id = str(thread.id)

    assert resolved_thread_id is not None

    # G13: durable entity links (C1 result link is not a substitute).
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
    return SalesQuestionnairePipelineBinding(
        thread_id=resolved_thread_id,
        sales_inquiry_id=inquiry_id,
        communication_purpose=PURPOSE_QUALIFICATION_QUESTIONNAIRE,
        template=sales_questionnaire_template_metadata(),
        locale=loc,
    )
