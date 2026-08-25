"""Recruitment-owned binder: GDPR notice → Communication Pipeline inputs.

Ensures Application (via §2.4 ensure) + email Thread Result Link + G13.
Does not send mail. Must not invent SalesInquiry context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
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
from backend.app.models.recruitment_application import RecruitmentApplication
from backend.app.modules.recruitment.communication.policy_adapter import POLICY_VERSION
from backend.app.modules.recruitment.services.application_result_service import (
    ApplicationTransportConflictError,
)
from backend.app.modules.recruitment.services.compliance_outbound_ensure import (
    ComplianceOutboundEnsureError,
    ensure_candidate_shell_and_application_for_compliance_outbound,
    lead_is_recruitment_destination_for_compliance,
    lead_is_sales_bound_for_recruitment_ensure,
)

PURPOSE_GDPR_NOTICE = "gdpr_notice"
PURPOSE_SUBMISSION_ACK = "submission_acknowledgement"
PURPOSE_INTAKE_REJECTION = "intake_rejection_notice"
PURPOSE_MOVING_FORWARD = "moving_forward_notice"

TEMPLATE_GDPR = ("tpl_recruitment_gdpr_notice_v1", "1")
TEMPLATE_SUBMISSION_ACK = ("tpl_recruitment_submission_acknowledgement_v1", "1")
TEMPLATE_REJECTION = ("tpl_recruitment_intake_rejection_notice_v1", "1")
TEMPLATE_MOVING_FORWARD = ("tpl_recruitment_moving_forward_notice_v1", "1")

CompliancePurpose = Literal[
    "gdpr_notice",
    "submission_acknowledgement",
    "intake_rejection_notice",
    "moving_forward_notice",
]


class RecruitmentCompliancePipelineError(Exception):
    code = "recruitment_compliance_pipeline_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


@dataclass(frozen=True, slots=True)
class RecruitmentCompliancePipelineBinding:
    thread_id: str
    application_id: str
    candidate_id: str
    communication_purpose: str
    template: CommunicationTemplateMetadata
    locale: str | None


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


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
        module_owner="recruitment",
        communication_domain="recruitment",
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


async def resolve_lead_uses_recruitment_compliance_pipeline(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> bool:
    """True when Lead should send RODO via Recruitment Pipeline (Application opaque)."""
    _ = (db, tenant_id)
    if lead_is_sales_bound_for_recruitment_ensure(lead):
        return False
    link = _record(_record(getattr(lead, "normalized", None)).get("intake_result_link_v1"))
    if link.get("application_id") or str(link.get("result_type") or "") == "application":
        return True
    return lead_is_recruitment_destination_for_compliance(lead)


async def _load_application_for_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    source: str,
) -> RecruitmentApplication:
    tid = str(tenant_id).strip()
    lid = str(getattr(lead, "id", "") or "").strip()
    if lead_is_sales_bound_for_recruitment_ensure(lead):
        raise RecruitmentCompliancePipelineError(
            "transport lead is Sales-bound; Recruitment compliance mail unavailable",
            details={"lead_id": lid, "reason": "sales_bound"},
        )

    link = _record(_record(getattr(lead, "normalized", None)).get("intake_result_link_v1"))
    existing_id = str(link.get("application_id") or "").strip()
    if existing_id:
        row = await db.get(RecruitmentApplication, existing_id)
        if row is not None and str(row.tenant_id) == tid:
            return row

    by_lead = await db.scalar(
        select(RecruitmentApplication)
        .where(RecruitmentApplication.tenant_id == tid, RecruitmentApplication.lead_id == lid)
        .limit(1)
    )
    if by_lead is not None:
        return by_lead

    try:
        ensured = await ensure_candidate_shell_and_application_for_compliance_outbound(
            db,
            tenant_id=tid,
            lead=lead,
            source=source,
        )
    except ApplicationTransportConflictError as exc:
        raise RecruitmentCompliancePipelineError(
            exc.message,
            details={**dict(exc.details), "reason": "sales_bound"},
        ) from exc
    except ComplianceOutboundEnsureError as exc:
        raise RecruitmentCompliancePipelineError(
            exc.message,
            details=dict(exc.details or {}),
        ) from exc

    row = await db.get(RecruitmentApplication, ensured.application_id)
    if row is None or str(row.tenant_id) != tid:
        raise RecruitmentCompliancePipelineError(
            "Application missing after compliance ensure",
            details={"lead_id": lid, "application_id": ensured.application_id},
        )
    return row


async def _find_bound_email_thread_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
) -> str | None:
    stmt = (
        select(CommunicationThreadResultLink.thread_id)
        .join(
            CommunicationThread,
            CommunicationThread.id == CommunicationThreadResultLink.thread_id,
        )
        .where(
            CommunicationThreadResultLink.tenant_id == tenant_id,
            CommunicationThreadResultLink.module_owner == "recruitment",
            CommunicationThreadResultLink.result_type == "application",
            CommunicationThreadResultLink.result_id == application_id,
            CommunicationThreadResultLink.status == LINK_STATUS_CONFIRMED,
            CommunicationThread.tenant_id == tenant_id,
            CommunicationThread.channel == "email",
        )
        .order_by(CommunicationThreadResultLink.created_at.asc())
        .limit(1)
    )
    return await db.scalar(stmt)


async def ensure_recruitment_compliance_pipeline_binding(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    purpose: CompliancePurpose = PURPOSE_GDPR_NOTICE,
    locale: str | None = None,
    actor_user_id: str | None = None,
    source: str = "recruitment.compliance_pipeline",
) -> RecruitmentCompliancePipelineBinding:
    """Ensure Thread Result Link + return pipeline inputs for Recruitment RODO email."""
    app = await _load_application_for_lead(
        db, tenant_id=tenant_id, lead=lead, source=source
    )
    application_id = str(app.id)
    candidate_id = str(app.candidate_id)
    tid = str(tenant_id).strip()

    found = await _find_bound_email_thread_id(
        db, tenant_id=tid, application_id=application_id
    )
    if found:
        resolved_thread_id = str(found)
    else:
        thread = CommunicationThread(
            id=str(uuid4()),
            tenant_id=tid,
            own_company_id=str(getattr(lead, "own_company_id", None) or "") or None,
            channel="email",
            subject=f"Recruitment · {purpose} · {application_id[:8]}",
            status="open",
            direction_hint="outbound",
            entity_type="application",
            entity_id=application_id,
            owner_id=str(actor_user_id).strip() if actor_user_id else None,
            thread_meta={
                "source": source,
                "application_id": application_id,
                "candidate_id": candidate_id,
                "transport_lead_id": str(lead.id),
                "communication_purpose": purpose,
            },
        )
        db.add(thread)
        await db.flush()
        opaque = OpaqueResultRef(
            module_owner="recruitment",
            result_type="application",
            result_id=application_id,
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
            raise RecruitmentCompliancePipelineError(
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
        entity_type="application",
        entity_id=application_id,
        is_immutable=True,
    )
    await ensure_thread_entity_link(
        db,
        tenant_id=tid,
        thread_id=resolved_thread_id,
        entity_type="candidate",
        entity_id=candidate_id,
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
    return RecruitmentCompliancePipelineBinding(
        thread_id=resolved_thread_id,
        application_id=application_id,
        candidate_id=candidate_id,
        communication_purpose=purpose,
        template=_template_for_purpose(purpose),
        locale=loc,
    )
