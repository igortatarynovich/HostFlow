"""Operational projection of open Lead RODO obligations.

Not a second state-machine. Reads canonical ``compliance_state`` (open only),
exposes queue / aging / SLA / retry eligibility / SMTP-exhaustion alerts.
Never writes ``compliant`` / ``delivered`` / ``exempt`` and never offers
mark-resolved. Tenant cannot disable fulfillment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Mapping, Optional, Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.lead import Lead
from backend.app.services.lead_rodo import (
    lead_normalized_rodo_block,
    lead_rodo_satisfied,
)
from backend.app.services.lead_rodo_obligation import (
    COMPLIANCE_OPEN_STATES,
    ComplianceTransitionError,
    current_compliance_state,
)

OperatorAction = Literal["send", "retry", "covered_at_source", "exempt"]

ART14_SLA = timedelta(days=30)
_FIRST_CONTACT_STAGES = frozenset({"contacted", "qualified", "converted"})
_SMTP_VIA = frozenset({"tenant_smtp", "platform_smtp"})
_TERMINAL_LEAD_STATUSES = frozenset({"processed", "rejected", "lost", "archived"})
_OPEN_STATUS_ALIASES = frozenset(
    {
        "delivery_required",
        "review_required",
        "delivery_failed",
        "failed",
        "deferred",
        "undelivered",
        "pending_channel",
        "pending_policy",
    }
)
RETRYABLE_COMPLIANCE_STATES: frozenset[str] = frozenset({"delivery_failed", "delivery_required"})
ESCALATION_EVENT_TYPE = "lead_rodo_delivery_escalated"
ESCALATION_DEDUPE_MINUTES = 24 * 60


@dataclass(frozen=True, slots=True)
class ObligationOpsItem:
    lead_id: str
    compliance_state: str
    article: Optional[str]
    evaluated_at: Optional[str]
    aging_hours: Optional[float]
    sla_due_at: Optional[str]
    sla_breached: bool
    last_attempt_at: Optional[str]
    last_failure: Optional[str]
    attempt_count: int
    tenant_smtp_exhausted: bool
    platform_smtp_exhausted: bool
    escalated: bool
    operator_actions: tuple[OperatorAction, ...]
    email: Optional[str] = None
    source: Optional[str] = None
    lead_status: Optional[str] = None
    lead_stage: Optional[str] = None
    display_name: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "compliance_state": self.compliance_state,
            "article": self.article,
            "evaluated_at": self.evaluated_at,
            "aging_hours": self.aging_hours,
            "sla_due_at": self.sla_due_at,
            "sla_breached": self.sla_breached,
            "last_attempt_at": self.last_attempt_at,
            "last_failure": self.last_failure,
            "attempt_count": self.attempt_count,
            "tenant_smtp_exhausted": self.tenant_smtp_exhausted,
            "platform_smtp_exhausted": self.platform_smtp_exhausted,
            "escalated": self.escalated,
            "operator_actions": list(self.operator_actions),
            "email": self.email,
            "source": self.source,
            "lead_status": self.lead_status,
            "lead_stage": self.lead_stage,
            "display_name": self.display_name,
        }


@dataclass(frozen=True, slots=True)
class ObligationOpsQueue:
    items: list[ObligationOpsItem]
    total: int
    counts: dict[str, int]
    sla_breached: int
    escalated: int
    limit: int
    offset: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.to_dict() for i in self.items],
            "total": self.total,
            "counts": dict(self.counts),
            "sla_breached": self.sla_breached,
            "escalated": self.escalated,
            "limit": self.limit,
            "offset": self.offset,
        }


def _parse_dt(raw: Any) -> Optional[datetime]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt is not None else None


def _attempts(block: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    evidence = block.get("delivery_evidence")
    if not isinstance(evidence, Mapping):
        return []
    raw = evidence.get("attempts")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, Mapping)]


def last_attempt_at(block: Optional[Mapping[str, Any]]) -> Optional[datetime]:
    if not isinstance(block, Mapping):
        return None
    stamps: list[datetime] = []
    evidence = block.get("delivery_evidence")
    if isinstance(evidence, Mapping):
        for key in ("recorded_at", "sent_at"):
            parsed = _parse_dt(evidence.get(key))
            if parsed is not None:
                stamps.append(parsed)
        for item in _attempts(block):
            parsed = _parse_dt(item.get("recorded_at") or item.get("at") or item.get("sent_at"))
            if parsed is not None:
                stamps.append(parsed)
    for key in ("undelivered_at", "sent_at"):
        parsed = _parse_dt(block.get(key))
        if parsed is not None:
            stamps.append(parsed)
    return max(stamps) if stamps else None


def last_failure_message(block: Optional[Mapping[str, Any]]) -> Optional[str]:
    if not isinstance(block, Mapping):
        return None
    for key in ("failure_reason", "pending_reason"):
        text = str(block.get(key) or "").strip()
        if text:
            return text[:2000]
    evidence = block.get("delivery_evidence")
    if isinstance(evidence, Mapping):
        text = str(evidence.get("failure_reason") or "").strip()
        if text:
            return text[:2000]
        attempts = _attempts(block)
        for item in reversed(attempts):
            if item.get("ok") is True:
                continue
            err = str(item.get("error") or "").strip()
            if err:
                return err[:2000]
    return None


def smtp_exhaustion(block: Optional[Mapping[str, Any]]) -> tuple[bool, bool, bool]:
    """Return ``(tenant_exhausted, platform_exhausted, escalated)``.

    Escalated only when SMTP paths were tried and none succeeded. Webhook is
    ignored. Platform fallback success is not an escalation.
    """
    if not isinstance(block, Mapping):
        return False, False, False
    attempts = _attempts(block)
    tenant_ok = any(
        str(item.get("via") or "").strip().lower() == "tenant_smtp" and item.get("ok") is True
        for item in attempts
    )
    platform_ok = any(
        str(item.get("via") or "").strip().lower() == "platform_smtp" and item.get("ok") is True
        for item in attempts
    )
    tenant_tried = any(str(item.get("via") or "").strip().lower() == "tenant_smtp" for item in attempts)
    platform_tried = any(
        str(item.get("via") or "").strip().lower() == "platform_smtp" for item in attempts
    )
    tenant_exhausted = tenant_tried and not tenant_ok
    platform_exhausted = platform_tried and not platform_ok
    if tenant_ok or platform_ok:
        return tenant_exhausted, platform_exhausted, False
    smtp_tried = any(str(item.get("via") or "").strip().lower() in _SMTP_VIA for item in attempts)
    evidence = block.get("delivery_evidence")
    reason_raw = ""
    if isinstance(evidence, Mapping):
        reason_raw = str(evidence.get("failure_reason") or "")
    if not reason_raw:
        reason_raw = str(block.get("failure_reason") or "")
    reason = reason_raw.strip().lower()
    exhausted_reason = "gdpr_notice_delivery_exhausted" in reason or "delivery exhausted" in reason
    escalated = bool(smtp_tried and not tenant_ok and not platform_ok)
    if not escalated and exhausted_reason and current_compliance_state(block) == "delivery_failed":
        escalated = True
        platform_exhausted = True
    return tenant_exhausted, platform_exhausted, escalated


def is_retryable_open_state(state: str) -> bool:
    """Bulk / ops retry may re-send only these open states — never review_required."""
    return str(state or "").strip().lower() in RETRYABLE_COMPLIANCE_STATES


def operator_actions_for(state: str) -> tuple[OperatorAction, ...]:
    cs = str(state or "").strip().lower()
    if cs == "delivery_failed":
        return ("retry", "covered_at_source", "exempt")
    if cs == "delivery_required":
        return ("send", "covered_at_source", "exempt")
    if cs == "review_required":
        return ("send", "covered_at_source", "exempt")
    return ()


def sla_due_at(
    block: Optional[Mapping[str, Any]],
    *,
    article: Optional[str],
    lead_stage: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Optional[datetime]:
    """Clock: ``evaluated_at`` (art.13 immediate; art.14 one month / first contact)."""
    if not isinstance(block, Mapping):
        return None
    evaluated = _parse_dt(block.get("evaluated_at"))
    if evaluated is None:
        assessment = block.get("assessment")
        if isinstance(assessment, Mapping):
            evaluated = _parse_dt(assessment.get("evaluated_at"))
    if evaluated is None:
        return None
    art = str(article or block.get("article") or "").strip()
    stage = str(lead_stage or "").strip().lower()
    if art == "14":
        month = evaluated + ART14_SLA
        if stage in _FIRST_CONTACT_STAGES:
            return evaluated
        return month
    return evaluated


def project_open_obligation(
    lead: Any,
    *,
    now: Optional[datetime] = None,
) -> Optional[ObligationOpsItem]:
    """Projection of one lead. Closed obligations are invisible."""
    if lead_rodo_satisfied(lead):
        return None
    norm = lead.normalized if isinstance(getattr(lead, "normalized", None), dict) else {}
    block = lead_normalized_rodo_block(norm if isinstance(norm, dict) else None)
    cs = current_compliance_state(block)
    if cs not in COMPLIANCE_OPEN_STATES:
        return None
    clock = now or datetime.now(timezone.utc)
    article = str(block.get("article") or "").strip() or None
    evaluated = _parse_dt(block.get("evaluated_at"))
    if evaluated is None:
        assessment = block.get("assessment")
        if isinstance(assessment, Mapping):
            evaluated = _parse_dt(assessment.get("evaluated_at"))
    attempt_dt = last_attempt_at(block)
    anchor = attempt_dt or evaluated
    aging_hours = None
    if anchor is not None:
        aging_hours = round((clock - anchor).total_seconds() / 3600.0, 2)
    due = sla_due_at(block, article=article, lead_stage=getattr(lead, "stage", None), now=clock)
    tenant_ex, platform_ex, escalated = smtp_exhaustion(block)
    ops = block.get("ops") if isinstance(block.get("ops"), Mapping) else {}
    if ops.get("escalated_at"):
        escalated = True
    email = str(norm.get("email") or block.get("recipient") or "").strip() or None
    name = str(norm.get("full_name") or "").strip()
    if not name:
        first = str(norm.get("first_name") or "").strip()
        last = str(norm.get("last_name") or "").strip()
        name = " ".join(part for part in (first, last) if part)
    return ObligationOpsItem(
        lead_id=str(getattr(lead, "id", "") or ""),
        compliance_state=cs,
        article=article,
        evaluated_at=_iso(evaluated),
        aging_hours=aging_hours,
        sla_due_at=_iso(due),
        sla_breached=bool(due is not None and due <= clock),
        last_attempt_at=_iso(attempt_dt),
        last_failure=last_failure_message(block),
        attempt_count=len(_attempts(block)),
        tenant_smtp_exhausted=tenant_ex,
        platform_smtp_exhausted=platform_ex,
        escalated=escalated,
        operator_actions=operator_actions_for(cs),
        email=email,
        source=str(getattr(lead, "source", "") or "").strip() or None,
        lead_status=str(getattr(lead, "status", "") or "").strip() or None,
        lead_stage=str(getattr(lead, "stage", "") or "").strip() or None,
        display_name=name or None,
    )


def _open_state_clause(states: Sequence[str]):
    wanted = {str(s).strip().lower() for s in states if str(s).strip().lower() in COMPLIANCE_OPEN_STATES}
    if not wanted:
        wanted = set(COMPLIANCE_OPEN_STATES)
    status_aliases = set(_OPEN_STATUS_ALIASES)
    if wanted != set(COMPLIANCE_OPEN_STATES):
        status_aliases = set(wanted)
        if "delivery_failed" in wanted:
            status_aliases.update(
                {"failed", "deferred", "undelivered", "pending_channel", "pending_policy", "delivery_failed"}
            )
    cs_col = Lead.normalized["rodo"]["compliance_state"].as_string()
    st_col = Lead.normalized["rodo"]["status"].as_string()
    return or_(cs_col.in_(sorted(wanted)), st_col.in_(sorted(status_aliases)))


async def list_open_obligations(
    db: AsyncSession,
    *,
    tenant_id: str,
    states: Optional[Sequence[str]] = None,
    include_terminal: bool = False,
    sla_breached_only: bool = False,
    escalated_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    now: Optional[datetime] = None,
) -> ObligationOpsQueue:
    """Filter/count by open ``compliance_state`` + aging. Does not write state."""
    tid = str(tenant_id).strip()
    cap = max(1, min(int(limit or 50), 200))
    skip = max(0, int(offset or 0))
    clock = now or datetime.now(timezone.utc)
    wanted = tuple(
        s
        for s in (states or [])
        if str(s).strip().lower() in COMPLIANCE_OPEN_STATES
    ) or tuple(sorted(COMPLIANCE_OPEN_STATES))

    q = select(Lead).where(Lead.tenant_id == tid)
    if not include_terminal:
        q = q.where(~Lead.status.in_(sorted(_TERMINAL_LEAD_STATUSES)))
    q = q.where(_open_state_clause(wanted))
    q = q.order_by(Lead.created_at.asc()).limit(max(cap + skip, 1) * 4)
    rows = list((await db.execute(q)).scalars().all())

    projected: list[ObligationOpsItem] = []
    for lead in rows:
        item = project_open_obligation(lead, now=clock)
        if item is None:
            continue
        if item.compliance_state not in wanted:
            continue
        if sla_breached_only and not item.sla_breached:
            continue
        if escalated_only and not item.escalated:
            continue
        projected.append(item)

    projected.sort(
        key=lambda i: (
            not i.sla_breached,
            not i.escalated,
            -(i.aging_hours or 0.0),
        )
    )
    counts: dict[str, int] = {state: 0 for state in sorted(COMPLIANCE_OPEN_STATES)}
    sla_n = 0
    esc_n = 0
    for item in projected:
        counts[item.compliance_state] = counts.get(item.compliance_state, 0) + 1
        if item.sla_breached:
            sla_n += 1
        if item.escalated:
            esc_n += 1
    page = projected[skip : skip + cap]
    return ObligationOpsQueue(
        items=page,
        total=len(projected),
        counts=counts,
        sla_breached=sla_n,
        escalated=esc_n,
        limit=cap,
        offset=skip,
    )


def stamp_ops_escalation(lead: Any, *, now: Optional[datetime] = None) -> bool:
    """Record observability only. Does not change ``compliance_state``. Returns True on first stamp."""
    from sqlalchemy.orm.attributes import flag_modified

    clock = now or datetime.now(timezone.utc)
    norm: dict[str, Any] = dict(lead.normalized or {}) if isinstance(lead.normalized, dict) else {}
    block: dict[str, Any] = {**lead_normalized_rodo_block(norm)}
    _, _, escalated = smtp_exhaustion(block)
    if not escalated and current_compliance_state(block) != "delivery_failed":
        return False
    if not escalated:
        return False
    ops = dict(block["ops"]) if isinstance(block.get("ops"), dict) else {}
    if str(ops.get("escalated_at") or "").strip():
        return False
    ops["escalated_at"] = clock.isoformat()
    ops["escalation_reason"] = "smtp_exhausted"
    block["ops"] = ops
    norm["rodo"] = block
    lead.normalized = norm
    flag_modified(lead, "normalized")
    return True


async def _escalation_recipient_ids(db: AsyncSession, *, tenant_id: str) -> list[str]:
    from backend.app.models.user import Role as UserRole
    from backend.app.models.user import User

    rows = await db.execute(
        select(User.id).where(
            User.tenant_id == str(tenant_id).strip(),
            User.role.in_((UserRole.administrator.value, UserRole.superadmin.value)),
            User.is_active.is_(True),
        )
    )
    return [str(x) for x in rows.scalars().all() if x]


async def maybe_escalate_delivery_exhaustion(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
    actor_id: Optional[str] = None,
) -> bool:
    """Alert operators after tenant SMTP then platform SMTP are exhausted.

    Does not close the obligation and does not treat webhook as fulfillment.
    """
    block = lead_normalized_rodo_block(
        lead.normalized if isinstance(getattr(lead, "normalized", None), dict) else None
    )
    if current_compliance_state(block) != "delivery_failed":
        return False
    _, _, escalated = smtp_exhaustion(block)
    if not escalated:
        return False
    first = stamp_ops_escalation(lead)
    if not first:
        return False

    from backend.app.core.audit_events import AuditEntityType, AuditEventType
    from backend.app.services.audit import log_audit_event
    from backend.app.services.user_notifications import create_notification

    await log_audit_event(
        db,
        tenant_id=str(tenant_id),
        event_type=AuditEventType.rodo_delivery_escalated,
        entity_type=AuditEntityType.lead,
        entity_id=str(lead.id),
        actor_id=actor_id,
        payload={
            "reason": "smtp_exhausted",
            "compliance_state": "delivery_failed",
            "last_failure": last_failure_message(block),
        },
    )
    recipients = await _escalation_recipient_ids(db, tenant_id=str(tenant_id))
    for user_id in recipients:
        await create_notification(
            db,
            tenant_id=str(tenant_id),
            user_id=user_id,
            event_type=ESCALATION_EVENT_TYPE,
            entity_type="lead",
            entity_id=str(lead.id),
            payload={
                "source": "lead_rodo_ops",
                "dedupe_key": f"lead_rodo_smtp_exhausted:{lead.id}",
                "compliance_state": "delivery_failed",
                "lead_id": str(lead.id),
            },
            dedupe_window_minutes=ESCALATION_DEDUPE_MINUTES,
            priority="critical",
        )
        await db.flush()
    return True


async def retry_open_obligation_send(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Any,
    actor_id: Optional[str] = None,
) -> tuple[bool, str]:
    """Re-send only for retryable open states. Failed retry keeps ``delivery_failed``."""
    from backend.app.services.lead_lifecycle_email_policy import (
        PURPOSE_GDPR_NOTICE,
        resolve_lifecycle_email_policy_for_lead,
    )
    from backend.app.services.lead_rodo import send_lead_rodo_email
    from backend.app.services.lead_rodo_settings import DEFAULT_LEAD_RODO_CHANNELS

    before = project_open_obligation(lead)
    if before is None:
        raise ComplianceTransitionError("RODO_NOT_OPEN", "Obligation is not open")
    if not is_retryable_open_state(before.compliance_state):
        raise ComplianceTransitionError(
            "RODO_RETRY_NOT_ALLOWED",
            "review_required is not retried; operator must send, cover at source, or exempt with proof",
        )
    decision = await resolve_lifecycle_email_policy_for_lead(
        db, tenant_id=str(tenant_id), lead=lead, purpose=PURPOSE_GDPR_NOTICE
    )
    ok, msg = await send_lead_rodo_email(
        db,
        lead=lead,
        tenant_id=str(tenant_id),
        actor_id=actor_id,
        channels=DEFAULT_LEAD_RODO_CHANNELS,
        template_id=None,
        message_template_id=decision.template_ref,
        auto_trigger="ops_retry",
        ingest_source="compliance_obligations_ops",
    )
    if not ok:
        await maybe_escalate_delivery_exhaustion(
            db, tenant_id=str(tenant_id), lead=lead, actor_id=actor_id
        )
        after = current_compliance_state(
            lead_normalized_rodo_block(
                lead.normalized if isinstance(getattr(lead, "normalized", None), dict) else None
            )
        )
        if before.compliance_state == "delivery_failed" and after not in ("delivery_failed", "delivered"):
            raise ComplianceTransitionError(
                "RODO_RETRY_CLOBBER",
                "Retry must not overwrite delivery_failed on unsuccessful send",
            )
    return ok, msg


__all__ = [
    "ART14_SLA",
    "ESCALATION_EVENT_TYPE",
    "ObligationOpsItem",
    "ObligationOpsQueue",
    "RETRYABLE_COMPLIANCE_STATES",
    "is_retryable_open_state",
    "last_attempt_at",
    "last_failure_message",
    "list_open_obligations",
    "maybe_escalate_delivery_exhaustion",
    "operator_actions_for",
    "project_open_obligation",
    "retry_open_obligation_send",
    "sla_due_at",
    "smtp_exhaustion",
    "stamp_ops_escalation",
]
