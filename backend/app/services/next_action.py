"""Primary "what to do next" resolver for entities.

Closes G-8 from `docs/specs/operations-loop.md`. Stage 1a shipped the
candidate variant; stage 2 begins extending the same DTO + reason-code
shape to additional entities so the frontend component renders uniformly:

* `compute_candidate_next_action` — stage 1a (DONE).
* `compute_lead_next_action`      — stage 2.0 (DONE).
* `compute_vacancy_next_action`   — stage 2.1 (DONE).
* `compute_document_next_action`  — stage 2.2 (DONE).
* `compute_thread_next_action`    — stage 2.3 (this file).

## Why a separate service

Up to now the candidate detail page assembled "what to do" from scratch in
the UI: read reminders, infer a header label, hope the recruiter understands.
The resulting CTA was inconsistent across pages and silently empty when a
candidate sat between signals (no reminder + no NBA + agency waiting on a
client). Operators read "no CTA" as "I broke something" — see G-8 in the
operations loop spec for the full rationale.

This service computes ONE primary CTA per entity with explicit precedence,
explicit reason code (for G-10 explainability later), and a deterministic
fallback ("Wait — nothing to do right now") so the empty state is never a
mystery.

## Precedence (highest priority wins)

For a candidate the order is:

1. `deleted_at IS NOT NULL`          → kind=done       (terminal_deleted)
2. stage **or** row status ∈ PIPELINE_COMPLETED  → kind=done       (terminal_stage_<code>)
3. pending `CandidateHandoff` exists → kind=handoff_*  (await on agency / decide on client)
4. active reminder with min due_at   → kind=reminder
5. zero contact attempts logged      → kind=contact    (operator hasn't reached out yet)
6. otherwise                         → kind=idle       (explicit "no action needed")

The shape of the response is stable across all six branches so the frontend
renders the same component regardless of which branch fired.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.spa_paths import TASKS, spa_candidate, spa_inbox_thread, spa_lead, spa_vacancy
from backend.app.constants.stages import PIPELINE_COMPLETED_STAGE_CODES, is_candidate_operationally_terminal
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_handoff import CandidateHandoff
from backend.app.models.communication import CommunicationThread
from backend.app.models.document import Document
from backend.app.models.enums import DocumentStatus
from backend.app.models.lead import Lead
from backend.app.models.reminder import Reminder, ReminderStatus
from backend.app.models.vacancy import Vacancy
from backend.app.models.vacancy_recruiter import VacancyRecruiter
from backend.app.services.contact_attempts import count_contact_attempts

logger = logging.getLogger(__name__)


class NextActionKind(str, Enum):
    """Coarse-grained "what kind of CTA do we render?" tag.

    Frontend uses this to pick the icon/colour and to decide whether the CTA
    is clickable (DONE/IDLE → no primary button, just a status line).
    """

    REMINDER = "reminder"
    CONTACT = "contact"
    HANDOFF_AWAIT = "handoff_await"
    HANDOFF_DECISION = "handoff_decision"
    DONE = "done"
    IDLE = "idle"


class NextActionPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    IDLE = "idle"


class NextActionDTO(BaseModel):
    """Single canonical "next action" payload for an entity card.

    Fields are deliberately split into machine-readable (`kind`,
    `reason_code`, `priority`) and human-readable (`title`, `hint`,
    `title_key`, `hint_key`) so the frontend can either render the bundled
    English string or look up an i18n key. The frontend is the source of
    truth for translation; backend strings are safe defaults only.
    """

    entity_type: str = Field(
        description=(
            "The entity this DTO describes — 'candidate', 'lead', 'vacancy', "
            "'document', or 'thread'. The frontend keys reason-code translations "
            "off both `entity_type` and `reason_code` so the same code can mean "
            "different things on different entities (e.g. `terminal_stage_lost` "
            "is lead-only; `terminal_stage_employed` is candidate-only)."
        )
    )
    entity_id: str
    kind: NextActionKind
    priority: NextActionPriority
    reason_code: str = Field(
        description=(
            "Machine-readable explanation, e.g. 'reminder_overdue', "
            "'no_contact_attempt', 'terminal_stage_rejected'. Used by the "
            "G-10 explainability popover."
        )
    )
    title: str
    title_key: Optional[str] = None
    hint: Optional[str] = None
    hint_key: Optional[str] = None
    due_at: Optional[datetime] = None
    href: Optional[str] = Field(
        default=None,
        description=(
            "Optional deep-link the primary CTA navigates to. None when the "
            "kind is DONE/IDLE — there is intentionally nothing to click."
        ),
    )


# Reminder statuses the cleanup hooks (G-1) treat as "still active". We mirror
# the same set so the next-action surface and the cleanup surface agree on
# what counts as "open".
_ACTIVE_REMINDER_STATUSES: tuple[str, ...] = (
    ReminderStatus.new,
    ReminderStatus.pending,
    ReminderStatus.sent,
    ReminderStatus.overdue,
)


# Stage codes where "no contact attempts logged" is genuinely a problem.
# Past `contacted` we assume the recruiter has at least dialled once even if
# they forgot to log it; nagging at that point is noise, not signal.
_PRE_CONTACT_STAGE_CODES: frozenset[str] = frozenset(
    {"", "new", "no_answer", "to_call", "to_contact"}
)


async def compute_candidate_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    is_client_tenant: bool = False,
) -> NextActionDTO:
    """Resolve the single primary next action for a candidate.

    `is_client_tenant` flips the handoff branch: an agency operator sees
    "waiting on client decision" while the client operator sees "decide on
    handoff". The candidate row is the same row; only the framing differs.

    The function is read-only and deterministic — calling it twice in a row
    with no DB changes returns the same DTO. Callers can cache the result
    safely until any of (Reminder | ContactAttempt | CandidateHandoff |
    Candidate.stage) for this candidate changes.
    """
    tenant_id_str = str(tenant_id or "").strip()
    candidate_id_str = str(candidate_id or "").strip()
    if not tenant_id_str or not candidate_id_str:
        # Defensive — callers should validate inputs before reaching the
        # service, but if they slip through we'd rather return a benign
        # "nothing to do" than blow up the candidate detail page.
        return _idle_dto(entity_id=candidate_id_str, reason="invalid_input")

    candidate = await db.scalar(
        select(Candidate).where(
            Candidate.id == candidate_id_str,
            Candidate.tenant_id == tenant_id_str,
        )
    )
    if candidate is None:
        # Returning a placeholder DTO instead of raising lets the calling
        # endpoint own the 404. The service is single-purpose: compute, never
        # decide HTTP semantics.
        return _idle_dto(entity_id=candidate_id_str, reason="candidate_not_found")

    stage_code = str(candidate.stage or "").strip().lower()

    # 1. Soft-deleted: terminal forever.
    if candidate.deleted_at is not None:
        return NextActionDTO(
            entity_type="candidate",
            entity_id=candidate_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code="terminal_deleted",
            title="Candidate is deleted",
            title_key="app.next_action.done.deleted",
            hint=None,
            hint_key=None,
        )

    # 2. Pipeline completed: canonical **stage** or row-level **status** (e.g. auto-reject without stage move).
    if is_candidate_operationally_terminal(stage=candidate.stage, status=candidate.status):
        st = (candidate.stage or "").strip().lower()
        row = (candidate.status or "").strip().lower()
        marker = st if st in PIPELINE_COMPLETED_STAGE_CODES else row
        return NextActionDTO(
            entity_type="candidate",
            entity_id=candidate_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code=f"terminal_stage_{marker}",
            title=f"Closed: {marker}",
            title_key=f"app.next_action.done.stage_{marker}",
            hint="No action needed — pipeline outcome recorded.",
            hint_key="app.next_action.done.hint",
        )

    # 3. Pending handoff: surface the right side of the conversation.
    pending_handoff = await db.scalar(
        select(CandidateHandoff)
        .where(
            CandidateHandoff.candidate_id == candidate_id_str,
            CandidateHandoff.status == "pending_review",
        )
        .limit(1)
    )
    if pending_handoff is not None:
        if is_client_tenant:
            # Client viewer: THEY are the blocker. CTA = "Decide on handoff".
            return NextActionDTO(
                entity_type="candidate",
                entity_id=candidate_id_str,
                kind=NextActionKind.HANDOFF_DECISION,
                priority=NextActionPriority.HIGH,
                reason_code="handoff_pending_client_decision",
                title="Decide on this handoff",
                title_key="app.next_action.handoff.client_decide.title",
                hint="The agency is waiting for accept / reject.",
                hint_key="app.next_action.handoff.client_decide.hint",
                href=f"{spa_candidate(candidate_id_str)}?focus=handoff",
            )
        # Agency viewer: nothing for them to do until the client responds.
        return NextActionDTO(
            entity_type="candidate",
            entity_id=candidate_id_str,
            kind=NextActionKind.HANDOFF_AWAIT,
            priority=NextActionPriority.NORMAL,
            reason_code="handoff_pending_client_decision",
            title="Awaiting client decision on handoff",
            title_key="app.next_action.handoff.agency_wait.title",
            hint="The candidate has been handed over — wait for the client.",
            hint_key="app.next_action.handoff.agency_wait.hint",
        )

    # 4. Earliest active reminder.
    reminder = await db.scalar(
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id_str,
            Reminder.entity_type == "candidate",
            Reminder.entity_id == candidate_id_str,
            Reminder.status.in_(_ACTIVE_REMINDER_STATUSES),
        )
        .order_by(Reminder.due_at.asc())
        .limit(1)
    )
    if reminder is not None:
        priority = _priority_from_due(reminder.due_at)
        is_overdue = priority == NextActionPriority.CRITICAL
        return NextActionDTO(
            entity_type="candidate",
            entity_id=candidate_id_str,
            kind=NextActionKind.REMINDER,
            priority=priority,
            reason_code="reminder_overdue" if is_overdue else "reminder_due",
            title=reminder.title or "Pending task",
            title_key=None,  # reminder titles are user-authored, not i18n keys
            hint=_format_reminder_hint(reminder.due_at),
            hint_key=None,
            due_at=reminder.due_at,
            href=f"{TASKS}?focus={reminder.id}",
        )

    # 5. No contact attempts yet on a pre-contact stage.
    if stage_code in _PRE_CONTACT_STAGE_CODES:
        attempts = await count_contact_attempts(db, candidate_id_str)
        if attempts == 0:
            return NextActionDTO(
                entity_type="candidate",
                entity_id=candidate_id_str,
                kind=NextActionKind.CONTACT,
                priority=NextActionPriority.HIGH,
                reason_code="no_contact_attempt",
                title="Make first contact",
                title_key="app.next_action.contact.first.title",
                hint="No call or message logged yet.",
                hint_key="app.next_action.contact.first.hint",
                href=f"{spa_candidate(candidate_id_str)}?action=log_contact",
            )

    # 6. Active candidate with no signal — say so explicitly.
    return _idle_dto(entity_id=candidate_id_str, reason="no_signal")


# ---------------------------------------------------------------------------
# Leads — G-8 stage 2.0
#
# Lead lifecycle differs from candidates: there is no handoff concept, no
# contact_attempts table linkage, but there ARE two SLA reminder types
# (`leads_no_next_action` / `leads_stuck_stage`) auto-scheduled by the
# communications scheduler. We therefore lean heavily on the "earliest active
# reminder" branch and add a couple of lead-specific terminal/raw-state
# branches around it.
# ---------------------------------------------------------------------------

# Stage codes that close a lead. `Lead.stage` literal is
# `new | contacted | qualified | converted | lost` — see
# `backend/app/modules/leads/schemas.py::LeadStage`.
_LEAD_TERMINAL_STAGE_CODES: frozenset[str] = frozenset({"converted", "lost"})

# Status codes that close a lead operationally even before stage moves.
# `processed` is fine (the active state); `new | needs_routing` are
# pre-processing states that the operator is supposed to act on.
_LEAD_TERMINAL_STATUS_CODES: frozenset[str] = frozenset({"failed", "duplicated"})

# `Lead.status == "new"` means the auto-pipeline hasn't picked it up yet —
# operator should manually qualify / route it. We surface that as a
# CONTACT-class CTA because it's the same shape ("act on this row").
_LEAD_RAW_STATUS_CODES: frozenset[str] = frozenset({"new", "needs_routing"})


async def compute_lead_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead_id: str,
) -> NextActionDTO:
    """Resolve the single primary next action for a lead.

    Precedence (highest priority wins):

    1. `lead.candidate_id IS NOT NULL`           → DONE  (lead_converted_to_candidate)
    2. `lead.stage in {converted, lost}`         → DONE  (terminal_stage_*)
    3. `lead.status in {failed, duplicated}`     → DONE  (terminal_status_*)
    4. `lead.status == 'needs_routing'`          → CONTACT (lead_needs_routing)
    5. earliest active reminder for entity=lead  → REMINDER
    6. `lead.status == 'new'`                    → CONTACT (lead_unqualified)
    7. otherwise                                 → IDLE (no_signal)

    Read-only and deterministic: same DB state → same DTO.
    """
    tenant_id_str = str(tenant_id or "").strip()
    lead_id_str = str(lead_id or "").strip()
    if not tenant_id_str or not lead_id_str:
        return _idle_dto(entity_id=lead_id_str, reason="invalid_input", entity_type="lead")

    lead = await db.scalar(
        select(Lead).where(
            Lead.id == lead_id_str,
            Lead.tenant_id == tenant_id_str,
        )
    )
    if lead is None:
        return _idle_dto(entity_id=lead_id_str, reason="lead_not_found", entity_type="lead")

    href_detail = spa_lead(lead_id_str)

    # 1. Converted to candidate: lead workstream is complete.
    if getattr(lead, "candidate_id", None):
        return NextActionDTO(
            entity_type="lead",
            entity_id=lead_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code="lead_converted_to_candidate",
            title="Candidate created",
            title_key="app.next_action.lead.done.candidate_created",
            hint="No action needed — this lead already created a candidate.",
            hint_key="app.next_action.done.hint",
        )

    # 2. Terminal stage — pipeline outcome recorded.
    stage_code = (lead.stage or "").strip().lower()
    if stage_code in _LEAD_TERMINAL_STAGE_CODES:
        return NextActionDTO(
            entity_type="lead",
            entity_id=lead_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code=f"terminal_stage_{stage_code}",
            title=f"Closed: {stage_code}",
            title_key=f"app.next_action.lead.done.stage_{stage_code}",
            hint="No action needed — lead outcome recorded.",
            hint_key="app.next_action.done.hint",
        )

    # 3. Terminal status — pipeline never started or de-duped.
    status_code = (lead.status or "").strip().lower()
    if status_code in _LEAD_TERMINAL_STATUS_CODES:
        return NextActionDTO(
            entity_type="lead",
            entity_id=lead_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code=f"terminal_status_{status_code}",
            title=f"Closed: {status_code}",
            title_key=f"app.next_action.lead.done.status_{status_code}",
            hint="No action needed — lead is not active.",
            hint_key="app.next_action.done.hint",
        )

    # 4. Needs routing: ops must pick a recipient before anything else can fire.
    if status_code == "needs_routing":
        return NextActionDTO(
            entity_type="lead",
            entity_id=lead_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.HIGH,
            reason_code="lead_needs_routing",
            title="Route this lead",
            title_key="app.next_action.lead.route.title",
            hint="Pipeline is waiting for a manual routing decision.",
            hint_key="app.next_action.lead.route.hint",
            href=href_detail,
        )

    # 5. Earliest active reminder (covers both SLA-generated and manual).
    reminder = await db.scalar(
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id_str,
            Reminder.entity_type == "lead",
            Reminder.entity_id == lead_id_str,
            Reminder.status.in_(_ACTIVE_REMINDER_STATUSES),
        )
        .order_by(Reminder.due_at.asc())
        .limit(1)
    )
    if reminder is not None:
        priority = _priority_from_due(reminder.due_at)
        is_overdue = priority == NextActionPriority.CRITICAL
        return NextActionDTO(
            entity_type="lead",
            entity_id=lead_id_str,
            kind=NextActionKind.REMINDER,
            priority=priority,
            reason_code="reminder_overdue" if is_overdue else "reminder_due",
            title=reminder.title or "Pending task",
            title_key=None,
            hint=_format_reminder_hint(reminder.due_at),
            hint_key=None,
            due_at=reminder.due_at,
            href=f"{TASKS}?focus={reminder.id}",
        )

    # 6. Raw / unqualified lead: operator should engage.
    #    `processed` (the auto-pipeline succeeded) skips this branch and
    #    falls through to IDLE — by then SLA reminders cover the rest.
    if status_code == "new":
        return NextActionDTO(
            entity_type="lead",
            entity_id=lead_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.HIGH,
            reason_code="lead_unqualified",
            title="Qualify this lead",
            title_key="app.next_action.lead.qualify.title",
            hint="Lead is fresh — confirm intent and contact info.",
            hint_key="app.next_action.lead.qualify.hint",
            href=href_detail,
        )

    # 7. Active processed lead with no signal — say so explicitly.
    return _idle_dto(entity_id=lead_id_str, reason="no_signal", entity_type="lead")


# ---------------------------------------------------------------------------
# Vacancies — G-8 stage 2.1
#
# A vacancy has a much smaller surface than candidates / leads: there is no
# auto-SLA scheduler today (`communications_scheduler.py` only fires for
# leads), no contact-attempt log, no handoff. The actionable signals reduce
# to (a) lifecycle state — archived / closed / paused, (b) any manually
# scheduled reminder against the vacancy, and (c) the structural problem of
# an open vacancy with zero recruiters assigned (it cannot progress).
# ---------------------------------------------------------------------------

# Vacancy.status is a free-string column (see migration
# `202512090002_vacancies_status_text.py`) but the API layer normalizes
# every write through `normalize_vacancy_status` (`models/vacancy.py`),
# so the canonical set `{open, on_hold, closed, filled, cancelled}` is
# the only thing this branch ladder needs to handle. The legacy
# `paused` alias is recognised here for backward compat with rows the
# Phase 2.6.D Stage B alembic migration has not yet rewritten.
#
# See `docs/specs/vacancy-statuses.md` §5.2 for the meaning of each
# terminal code (`closed`, `filled`, `cancelled`).
_VACANCY_TERMINAL_STATUS_CODES: frozenset[str] = frozenset(
    {"closed", "filled", "cancelled"}
)
_VACANCY_PAUSED_STATUS_CODES: frozenset[str] = frozenset({"on_hold", "paused"})


async def compute_vacancy_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: str,
) -> NextActionDTO:
    """Resolve the single primary next action for a vacancy.

    Precedence (highest priority wins):

    1. `vacancy.is_archived`                     → DONE  (terminal_archived)
    2. `vacancy.status` in `{closed, filled, cancelled}` → DONE  (terminal_status_*)
    3. earliest active reminder for entity=vacancy → REMINDER
    4. `vacancy.status == 'on_hold'`             → IDLE  (vacancy_paused — intentional)
    5. `vacancy.status == 'open'` + zero active recruiters → CONTACT (vacancy_no_recruiter)
    6. otherwise                                 → IDLE  (no_signal)

    Stage F of `docs/specs/vacancy-statuses.md` extended branch 2 to
    cover the new terminal codes `filled` (successful hire) and
    `cancelled` (vacancy cancelled before work started). Branch 4 was
    rewritten to expect canonical `on_hold`; the legacy `paused` alias
    is still recognised so rows the Stage B migration has not yet
    rewritten don't suddenly start nagging operators.

    Read-only and deterministic: same DB state → same DTO.
    """
    tenant_id_str = str(tenant_id or "").strip()
    vacancy_id_str = str(vacancy_id or "").strip()
    if not tenant_id_str or not vacancy_id_str:
        return _idle_dto(entity_id=vacancy_id_str, reason="invalid_input", entity_type="vacancy")

    # Load by id only: caller (HTTP layer) enforces tenant / client link scope. Using the
    # session tenant_id here would 404 for client tenants viewing an agency-owned vacancy.
    vacancy = await db.scalar(select(Vacancy).where(Vacancy.id == vacancy_id_str))
    if vacancy is None:
        return _idle_dto(entity_id=vacancy_id_str, reason="vacancy_not_found", entity_type="vacancy")

    owner_tid = str(vacancy.tenant_id or "").strip() or tenant_id_str

    href_detail = spa_vacancy(vacancy_id_str)

    # 1. Archived: terminal forever (operator filed it away).
    if bool(vacancy.is_archived):
        return NextActionDTO(
            entity_type="vacancy",
            entity_id=vacancy_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code="terminal_archived",
            title="Archived",
            title_key="app.next_action.vacancy.done.archived",
            hint="No action needed — vacancy is archived.",
            hint_key="app.next_action.done.hint",
        )

    status_code = (vacancy.status or "").strip().lower()

    # 2. Closed: pipeline outcome recorded (filled or cancelled).
    if status_code in _VACANCY_TERMINAL_STATUS_CODES:
        return NextActionDTO(
            entity_type="vacancy",
            entity_id=vacancy_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code=f"terminal_status_{status_code}",
            title=f"Closed: {status_code}",
            title_key=f"app.next_action.vacancy.done.status_{status_code}",
            hint="No action needed — vacancy is closed.",
            hint_key="app.next_action.done.hint",
        )

    # 3. Earliest active reminder. Today only manual reminders + UOS auto
    #    activities target vacancies (no `vacancies_*_sla` scheduler) but the
    #    branch is identical so future SLA types ride for free.
    reminder = await db.scalar(
        select(Reminder)
        .where(
            Reminder.tenant_id == owner_tid,
            Reminder.entity_type == "vacancy",
            Reminder.entity_id == vacancy_id_str,
            Reminder.status.in_(_ACTIVE_REMINDER_STATUSES),
        )
        .order_by(Reminder.due_at.asc())
        .limit(1)
    )
    if reminder is not None:
        priority = _priority_from_due(reminder.due_at)
        is_overdue = priority == NextActionPriority.CRITICAL
        return NextActionDTO(
            entity_type="vacancy",
            entity_id=vacancy_id_str,
            kind=NextActionKind.REMINDER,
            priority=priority,
            reason_code="reminder_overdue" if is_overdue else "reminder_due",
            title=reminder.title or "Pending task",
            title_key=None,
            hint=_format_reminder_hint(reminder.due_at),
            hint_key=None,
            due_at=reminder.due_at,
            href=f"{TASKS}?focus={reminder.id}",
        )

    # 4. Paused: explicit operator decision — we should NOT nag with a CTA.
    #    Render IDLE with a distinct reason so the popover can explain why.
    if status_code in _VACANCY_PAUSED_STATUS_CODES:
        return NextActionDTO(
            entity_type="vacancy",
            entity_id=vacancy_id_str,
            kind=NextActionKind.IDLE,
            priority=NextActionPriority.IDLE,
            reason_code="vacancy_paused",
            title="Paused — no action needed",
            title_key="app.next_action.vacancy.paused.title",
            hint="Resume the vacancy when you're ready to continue sourcing.",
            hint_key="app.next_action.vacancy.paused.hint",
        )

    # 5. Open vacancy with zero active recruiter assignments.
    #    Without recruiters the lead-distribution scheduler can't route any
    #    candidates to this vacancy — it's a structural blocker, surface it
    #    as a HIGH-priority CONTACT-class CTA.
    has_recruiter = await db.scalar(
        select(VacancyRecruiter.user_id)
        .where(
            VacancyRecruiter.vacancy_id == vacancy_id_str,
            VacancyRecruiter.tenant_id == owner_tid,
            VacancyRecruiter.is_active.is_(True),
        )
        .limit(1)
    )
    if has_recruiter is None:
        return NextActionDTO(
            entity_type="vacancy",
            entity_id=vacancy_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.HIGH,
            reason_code="vacancy_no_recruiter",
            title="Assign a recruiter",
            title_key="app.next_action.vacancy.no_recruiter.title",
            hint="No active recruiters — lead distribution will skip this vacancy.",
            hint_key="app.next_action.vacancy.no_recruiter.hint",
            href=href_detail,
        )

    # 6. Active vacancy with no signal — say so explicitly.
    return _idle_dto(entity_id=vacancy_id_str, reason="no_signal", entity_type="vacancy")


# ---------------------------------------------------------------------------
# Documents — G-8 stage 2.2
#
# Document lifecycle is the richest of the entities (20 statuses in
# `DocumentStatus`), so the ladder explicitly buckets them. Two bits of
# subtlety to call out:
#
#   * Reminders for documents come from TWO `entity_type` values today:
#     plain `"document"` (from `services/reminders.py:schedule_document_*`)
#     and `"document_step"` for workflow-step nudges with `entity_id`
#     `"{document_id}:{step_code}"`. Both should surface here, otherwise
#     step nudges get hidden behind the doc itself going IDLE.
#
#   * `expire_date < today` MUST be checked even when status is in the
#     "resolved" bucket (verified / approved / issued / etc.), because the
#     system does not auto-flip status from `verified` → `expired`. A
#     stale "verified" doc whose expire_date has passed is an action item
#     ("renew"), not a DONE state.
#
# Documents do not have their own SPA detail route — they live inside the
# candidate detail page. We point `href` at `/app/candidates/{candidate_id}`
# so the badge click still goes somewhere useful.
# ---------------------------------------------------------------------------

# Mirrors `hostflow-frontend/src/modules/documents/constants.EXPIRING_SOON_THRESHOLD_DAYS`.
# Keep the two in sync — see `docs/specs/operations-loop.md` §G-8 stage 2.2.
_DOCUMENT_EXPIRING_SOON_DAYS = 30

# Operator explicitly said "we're not pursuing this" — pure terminal.
_DOCUMENT_TERMINAL_DONE_STATUSES: frozenset[DocumentStatus] = frozenset({
    DocumentStatus.cancelled,
    DocumentStatus.not_required,
})

# Successful resolved states. Still need an expire_date sanity check before
# we declare DONE — see ladder step 6.
_DOCUMENT_RESOLVED_DONE_STATUSES: frozenset[DocumentStatus] = frozenset({
    DocumentStatus.completed,
    DocumentStatus.verified,
    DocumentStatus.approved,
    DocumentStatus.received,
    DocumentStatus.delivered,
    DocumentStatus.registered,
    DocumentStatus.active,
    DocumentStatus.issued,
})

# Operator must act NOW. Each maps to a distinct reason_code so the
# explainability popover can render targeted copy.
_DOCUMENT_HIGH_PRIORITY_STATUS_REASONS: dict[DocumentStatus, str] = {
    DocumentStatus.missing: "document_missing",
    DocumentStatus.rejected: "document_rejected",
    DocumentStatus.to_prepare: "document_to_prepare",
    DocumentStatus.to_register: "document_to_register",
    DocumentStatus.submitted: "document_needs_verification",
    DocumentStatus.uploaded: "document_needs_verification",
}

# Active but waiting on someone external — IDLE with context, not a CTA.
# A reminder firing on top of this will still surface (step 4 above).
_DOCUMENT_AWAITING_STATUSES: frozenset[DocumentStatus] = frozenset({
    DocumentStatus.requested,
    DocumentStatus.in_progress,
})


def _coerce_doc_status(raw: Any) -> Optional[DocumentStatus]:
    """Be liberal in what we accept — DB rows may carry the enum, a string,
    or NULL depending on call site. Returns None for unknown values so the
    ladder falls through to the no_signal IDLE branch."""
    if raw is None:
        return None
    if isinstance(raw, DocumentStatus):
        return raw
    try:
        return DocumentStatus(str(raw).strip().lower())
    except ValueError:
        return None


async def compute_document_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    document_id: str,
    today: Optional[date] = None,
) -> NextActionDTO:
    """Resolve the single primary next action for a document.

    Precedence (highest priority wins):

    1. `deleted_at IS NOT NULL`                  → DONE  (terminal_deleted)
    2. status ∈ {cancelled, not_required}        → DONE  (terminal_status_*)
    3. status == overdue                         → CONTACT/CRITICAL (document_overdue)
    4. status == expired                         → CONTACT/HIGH (document_expired)
    5. earliest active reminder                  → REMINDER
       (entity_type='document' OR 'document_step:{doc_id}:%')
    6. status ∈ HIGH_PRIORITY map                → CONTACT/HIGH (per-status reason)
    7. status ∈ RESOLVED_DONE bucket and `expire_date < today` → CONTACT/HIGH
       (`document_expired_by_date` — system did not auto-flip status)
    8. status ∈ RESOLVED_DONE bucket and within EXPIRING_SOON window
       → CONTACT/NORMAL (`document_expiring_soon`)
    9. status ∈ RESOLVED_DONE bucket             → DONE (terminal_status_*)
   10. status ∈ AWAITING bucket                  → IDLE (`document_awaiting_party`)
   11. otherwise                                 → IDLE (`no_signal`)

    `today` is injectable for deterministic tests; production callers MUST
    leave it None.
    """
    tenant_id_str = str(tenant_id or "").strip()
    doc_id_str = str(document_id or "").strip()
    if not tenant_id_str or not doc_id_str:
        return _idle_dto(entity_id=doc_id_str, reason="invalid_input", entity_type="document")

    # Checklist placeholders (no DB row) — same UX as ``DocumentStatus.missing``.
    if doc_id_str.startswith("synthetic::"):
        parts = doc_id_str.split("::")
        if len(parts) == 3 and parts[0] == "synthetic":
            _, _syn_type, candidate_id = parts
            cid = (candidate_id or "").strip()
            href_detail = spa_candidate(cid) if cid else None
            reason_code = "document_missing"
            return NextActionDTO(
                entity_type="document",
                entity_id=doc_id_str,
                kind=NextActionKind.CONTACT,
                priority=NextActionPriority.HIGH,
                reason_code=reason_code,
                title="Action required: missing",
                title_key=f"app.next_action.document.{reason_code}.title",
                hint="Open the candidate's documents tab to handle this.",
                hint_key=f"app.next_action.document.{reason_code}.hint",
                href=href_detail,
            )

    doc = await db.scalar(
        select(Document).where(
            Document.id == doc_id_str,
            Document.tenant_id == tenant_id_str,
        )
    )
    if doc is None:
        return _idle_dto(entity_id=doc_id_str, reason="document_not_found", entity_type="document")

    # `Document.candidate_id` is non-null on the model, but defensive read
    # in case migration history or a fixture left it blank.
    candidate_id = (getattr(doc, "candidate_id", None) or "").strip()
    href_detail = spa_candidate(candidate_id) if candidate_id else None

    # 1. Soft-deleted: respect the cleanup contract from G-1.
    if doc.deleted_at is not None:
        return NextActionDTO(
            entity_type="document",
            entity_id=doc_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code="terminal_deleted",
            title="Deleted",
            title_key="app.next_action.document.done.deleted",
            hint="No action needed — document has been deleted.",
            hint_key="app.next_action.done.hint",
        )

    status = _coerce_doc_status(doc.status)

    # 2. Operator opt-out: cancelled / not_required.
    if status in _DOCUMENT_TERMINAL_DONE_STATUSES:
        return NextActionDTO(
            entity_type="document",
            entity_id=doc_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code=f"terminal_status_{status.value}",
            title=f"Closed: {status.value}",
            title_key=f"app.next_action.document.done.status_{status.value}",
            hint="No action needed — document is not active.",
            hint_key="app.next_action.done.hint",
        )

    # 3. SLA breach already declared by the system.
    if status == DocumentStatus.overdue:
        return NextActionDTO(
            entity_type="document",
            entity_id=doc_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.CRITICAL,
            reason_code="document_overdue",
            title="Document overdue",
            title_key="app.next_action.document.overdue.title",
            hint="The SLA on this document has been breached.",
            hint_key="app.next_action.document.overdue.hint",
            href=href_detail,
        )

    # 4. Validity window already expired (status flipped explicitly).
    if status == DocumentStatus.expired:
        return NextActionDTO(
            entity_type="document",
            entity_id=doc_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.HIGH,
            reason_code="document_expired",
            title="Document expired — renew",
            title_key="app.next_action.document.expired.title",
            hint="The document is past its validity date and must be renewed.",
            hint_key="app.next_action.document.expired.hint",
            href=href_detail,
        )

    # 5. Earliest active reminder — covers both row-level reminders and
    #    workflow step nudges (`document_step` with `entity_id={id}:{step}`).
    reminder = await db.scalar(
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id_str,
            Reminder.status.in_(_ACTIVE_REMINDER_STATUSES),
            or_(
                and_(
                    Reminder.entity_type == "document",
                    Reminder.entity_id == doc_id_str,
                ),
                and_(
                    Reminder.entity_type == "document_step",
                    Reminder.entity_id.like(f"{doc_id_str}:%"),
                ),
            ),
        )
        .order_by(Reminder.due_at.asc())
        .limit(1)
    )
    if reminder is not None:
        priority = _priority_from_due(reminder.due_at)
        is_overdue = priority == NextActionPriority.CRITICAL
        return NextActionDTO(
            entity_type="document",
            entity_id=doc_id_str,
            kind=NextActionKind.REMINDER,
            priority=priority,
            reason_code="reminder_overdue" if is_overdue else "reminder_due",
            title=reminder.title or "Pending task",
            title_key=None,
            hint=_format_reminder_hint(reminder.due_at),
            hint_key=None,
            due_at=reminder.due_at,
            href=f"{TASKS}?focus={reminder.id}",
        )

    # 6. Statuses that mean "act now" without ambiguity.
    if status in _DOCUMENT_HIGH_PRIORITY_STATUS_REASONS:
        reason_code = _DOCUMENT_HIGH_PRIORITY_STATUS_REASONS[status]
        return NextActionDTO(
            entity_type="document",
            entity_id=doc_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.HIGH,
            reason_code=reason_code,
            title=f"Action required: {status.value}",
            title_key=f"app.next_action.document.{reason_code}.title",
            hint="Open the candidate's documents tab to handle this.",
            hint_key=f"app.next_action.document.{reason_code}.hint",
            href=href_detail,
        )

    # 7-9. Resolved bucket: still need to validate expiry before declaring DONE.
    if status in _DOCUMENT_RESOLVED_DONE_STATUSES:
        expire_date = doc.expire_date
        ref_date = today or _date_today_utc()
        if expire_date is not None:
            if expire_date < ref_date:
                # 7. Status says "verified" but the date says otherwise.
                return NextActionDTO(
                    entity_type="document",
                    entity_id=doc_id_str,
                    kind=NextActionKind.CONTACT,
                    priority=NextActionPriority.HIGH,
                    reason_code="document_expired_by_date",
                    title="Document expired — renew",
                    title_key="app.next_action.document.expired_by_date.title",
                    hint=(
                        f"Status is '{status.value}' but the validity date passed "
                        f"on {expire_date.isoformat()}."
                    ),
                    hint_key="app.next_action.document.expired_by_date.hint",
                    href=href_detail,
                )
            days_left = (expire_date - ref_date).days
            if 0 <= days_left <= _DOCUMENT_EXPIRING_SOON_DAYS:
                # 8. Same threshold the UI uses for the amber "expiring" pill.
                return NextActionDTO(
                    entity_type="document",
                    entity_id=doc_id_str,
                    kind=NextActionKind.CONTACT,
                    priority=NextActionPriority.NORMAL,
                    reason_code="document_expiring_soon",
                    title="Document expiring soon",
                    title_key="app.next_action.document.expiring_soon.title",
                    hint=(
                        f"Validity ends on {expire_date.isoformat()} "
                        f"({days_left} day(s) left)."
                    ),
                    hint_key="app.next_action.document.expiring_soon.hint",
                    href=href_detail,
                )
        # 9. Resolved + valid (or no expiry) → DONE.
        return NextActionDTO(
            entity_type="document",
            entity_id=doc_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code=f"terminal_status_{status.value}",
            title=f"Resolved: {status.value}",
            title_key=f"app.next_action.document.done.status_{status.value}",
            hint="No action needed — document is in a resolved state.",
            hint_key="app.next_action.done.hint",
        )

    # 10. Awaiting external party — keep quiet, surface only via SLA reminder.
    if status in _DOCUMENT_AWAITING_STATUSES:
        return NextActionDTO(
            entity_type="document",
            entity_id=doc_id_str,
            kind=NextActionKind.IDLE,
            priority=NextActionPriority.IDLE,
            reason_code="document_awaiting_party",
            title="Awaiting external party",
            title_key="app.next_action.document.awaiting_party.title",
            hint="The document is in flight — operator action surfaces only via reminders.",
            hint_key="app.next_action.document.awaiting_party.hint",
        )

    # 11. Anything else (unknown / NULL status) — explicit no_signal.
    return _idle_dto(entity_id=doc_id_str, reason="no_signal", entity_type="document")


# ---------------------------------------------------------------------------
# Threads (communication_threads) — G-8 stage 2.3
#
# Threads carry the most operator-facing surface in HostFlow today:
# inbound messages from candidates / clients via WhatsApp, Telegram, email,
# SMS, etc. They already have a per-channel SLA mechanism
# (`services/communications/_helpers/sla.py`) that sets `sla_due_at` on
# inbound, clears it on outbound, and is escalated by
# `communications_scheduler._run_sla_escalations_for_tenant` into reminders
# of `entity_type='communication_thread'` and `type='communications_sla_overdue'`.
#
# Three subtleties to call out:
#
#   * Status is a **free string column** (`String(32)`, default `"open"`),
#     not an Enum. The frontend treats `status.lower() == "deleted"` as a
#     terminal "remove from inbox" state. We also defensively recognise
#     `closed` and `resolved` even though they aren't in the live data
#     today — adding a row with those values is safe (it's a free column).
#
#   * `sla_due_at` is the **single source of truth** for "operator owes a
#     reply" timing. We don't recompute it from message rows — that's the
#     scheduler's job. We just check whether it's past now() (overdue) or
#     within a near-term window (due-soon).
#
#   * `unread_count > 0` means at least one inbound message hasn't been
#     opened in the inbox UI. This is a **stronger** signal than
#     `last_inbound_at > last_outbound_at` because the latter can stay
#     true even after the operator hits "mark as read" without replying.
#     Both surface in the ladder (HIGH vs NORMAL respectively) so an
#     "acknowledged but not replied" thread doesn't go silent.
# ---------------------------------------------------------------------------

# Threshold for "SLA due soon" CTA — half the typical channel SLA window.
# Most tenants configure 60-180 minute SLAs (per
# `services/communications/_helpers/sla.py`); 30 minutes gives operators a
# "you should reply now" nudge without spamming.
_THREAD_SLA_DUE_SOON_MINUTES = 30

# `String(32)` free column — these match `status.lower()`.
_THREAD_DELETED_STATUSES: frozenset[str] = frozenset({"deleted"})
# Defensive — not in live data today, but the column accepts arbitrary
# strings. If ops start using these the surface should already DTRT.
_THREAD_CLOSED_STATUSES: frozenset[str] = frozenset({"closed", "resolved"})
# Operator-paused states — keep quiet, do not nag.
_THREAD_IDLE_STATUSES: frozenset[str] = frozenset({"snoozed", "pending"})


async def compute_thread_next_action(
    db: AsyncSession,
    *,
    tenant_id: str,
    thread_id: str,
    now: Optional[datetime] = None,
) -> NextActionDTO:
    """Resolve the single primary next action for a communication thread.

    Precedence (highest priority wins):

    1.  is_archived                                   → DONE  (terminal_archived)
    2.  status.lower() == 'deleted'                   → DONE  (terminal_status_deleted)
    3.  status.lower() ∈ {closed, resolved}           → DONE  (terminal_status_*)
    4.  sla_due_at < now                              → CONTACT/CRITICAL (thread_sla_overdue)
    5.  earliest active reminder
        (entity_type='communication_thread')          → REMINDER
    6.  unread_count > 0                              → CONTACT/HIGH (thread_unread_inbound)
    7.  last_inbound_at > last_outbound_at            → CONTACT/NORMAL (thread_awaiting_reply)
    8.  sla_due_at within next 30 min                 → CONTACT/NORMAL (thread_sla_due_soon)
    9.  status.lower() ∈ {snoozed, pending}           → IDLE (thread_<status>)
   10.  fallback                                      → IDLE (no_signal)

    `now` is injectable for deterministic tests; production callers MUST
    leave it None.
    """
    tenant_id_str = str(tenant_id or "").strip()
    thread_id_str = str(thread_id or "").strip()
    if not tenant_id_str or not thread_id_str:
        return _idle_dto(entity_id=thread_id_str, reason="invalid_input", entity_type="thread")

    thread = await db.scalar(
        select(CommunicationThread).where(
            CommunicationThread.id == thread_id_str,
            CommunicationThread.tenant_id == tenant_id_str,
        )
    )
    if thread is None:
        return _idle_dto(entity_id=thread_id_str, reason="thread_not_found", entity_type="thread")

    href_detail = spa_inbox_thread(thread_id_str)
    ref_now = now or datetime.now(timezone.utc)

    # 1. Archived — operator filed it away. Terminal.
    if bool(thread.is_archived):
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code="terminal_archived",
            title="Archived",
            title_key="app.next_action.thread.done.archived",
            hint="No action needed — thread is archived.",
            hint_key="app.next_action.done.hint",
        )

    status_code = (thread.status or "").strip().lower()

    # 2. Deleted — frontend already hides these (`status === 'deleted'`).
    if status_code in _THREAD_DELETED_STATUSES:
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code="terminal_status_deleted",
            title="Deleted",
            title_key="app.next_action.thread.done.status_deleted",
            hint="No action needed — thread has been deleted.",
            hint_key="app.next_action.done.hint",
        )

    # 3. Operator-declared resolution. Defensive — column is free-form so
    #    these aren't in live data today; the surface needs to handle them
    #    the moment ops start using them.
    if status_code in _THREAD_CLOSED_STATUSES:
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.DONE,
            priority=NextActionPriority.IDLE,
            reason_code=f"terminal_status_{status_code}",
            title=f"Closed: {status_code}",
            title_key=f"app.next_action.thread.done.status_{status_code}",
            hint="No action needed — thread is closed.",
            hint_key="app.next_action.done.hint",
        )

    sla_due_at = thread.sla_due_at

    # 4. SLA breach — direct read of `sla_due_at`. Doesn't depend on the
    #    scheduler having fired a reminder yet (race-free).
    if sla_due_at is not None and sla_due_at < ref_now:
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.CRITICAL,
            reason_code="thread_sla_overdue",
            title="Reply overdue (SLA breached)",
            title_key="app.next_action.thread.sla_overdue.title",
            hint=_format_reminder_hint(sla_due_at),
            hint_key="app.next_action.thread.sla_overdue.hint",
            due_at=sla_due_at,
            href=href_detail,
        )

    # 5. Earliest active reminder. The scheduler emits these for SLA
    #    overdue (entity_type='communication_thread'); manual reminders
    #    against threads ride the same path.
    reminder = await db.scalar(
        select(Reminder)
        .where(
            Reminder.tenant_id == tenant_id_str,
            Reminder.entity_type == "communication_thread",
            Reminder.entity_id == thread_id_str,
            Reminder.status.in_(_ACTIVE_REMINDER_STATUSES),
        )
        .order_by(Reminder.due_at.asc())
        .limit(1)
    )
    if reminder is not None:
        priority = _priority_from_due(reminder.due_at)
        is_overdue = priority == NextActionPriority.CRITICAL
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.REMINDER,
            priority=priority,
            reason_code="reminder_overdue" if is_overdue else "reminder_due",
            title=reminder.title or "Pending task",
            title_key=None,
            hint=_format_reminder_hint(reminder.due_at),
            hint_key=None,
            due_at=reminder.due_at,
            href=f"{TASKS}?focus={reminder.id}",
        )

    # 6. Unread inbound — strongest "needs reply" signal. Operator hasn't
    #    even opened the message yet.
    unread_count = int(thread.unread_count or 0)
    if unread_count > 0:
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.HIGH,
            reason_code="thread_unread_inbound",
            title=(
                "1 unread message"
                if unread_count == 1
                else f"{unread_count} unread messages"
            ),
            title_key="app.next_action.thread.unread_inbound.title",
            hint="Open the thread and reply.",
            hint_key="app.next_action.thread.unread_inbound.hint",
            href=href_detail,
        )

    # 7. Read but not replied — operator acknowledged but the ball is
    #    still in their court. Lower priority than unread.
    last_inbound_at = thread.last_inbound_at
    last_outbound_at = thread.last_outbound_at
    if last_inbound_at is not None and (
        last_outbound_at is None or last_inbound_at > last_outbound_at
    ):
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.NORMAL,
            reason_code="thread_awaiting_reply",
            title="Reply pending",
            title_key="app.next_action.thread.awaiting_reply.title",
            hint="The last message was inbound — write a reply to close the loop.",
            hint_key="app.next_action.thread.awaiting_reply.hint",
            href=href_detail,
        )

    # 8. SLA approaching breach — heads-up while there's still time.
    if sla_due_at is not None and (
        sla_due_at <= ref_now + timedelta(minutes=_THREAD_SLA_DUE_SOON_MINUTES)
    ):
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.CONTACT,
            priority=NextActionPriority.NORMAL,
            reason_code="thread_sla_due_soon",
            title="SLA due soon",
            title_key="app.next_action.thread.sla_due_soon.title",
            hint=_format_reminder_hint(sla_due_at),
            hint_key="app.next_action.thread.sla_due_soon.hint",
            due_at=sla_due_at,
            href=href_detail,
        )

    # 9. Operator-paused states — explicit "don't nudge me".
    if status_code in _THREAD_IDLE_STATUSES:
        return NextActionDTO(
            entity_type="thread",
            entity_id=thread_id_str,
            kind=NextActionKind.IDLE,
            priority=NextActionPriority.IDLE,
            reason_code=f"thread_{status_code}",
            title=f"Thread {status_code}",
            title_key=f"app.next_action.thread.{status_code}.title",
            hint="The thread is paused — no operator action expected.",
            hint_key=f"app.next_action.thread.{status_code}.hint",
        )

    # 10. Open thread, no signal — say so explicitly.
    return _idle_dto(entity_id=thread_id_str, reason="no_signal", entity_type="thread")


def _date_today_utc() -> date:
    """Indirection over `datetime.utcnow().date()` so tests can override
    via the explicit `today` kwarg without monkey-patching the module."""
    return datetime.now(timezone.utc).date()


def _idle_dto(*, entity_id: str, reason: str, entity_type: str = "candidate") -> NextActionDTO:
    """Standard "nothing to do right now" DTO.

    Critical: we always return SOMETHING. An empty CTA on a card reads as
    "broken UI" to operators. An explicit "no action needed (reason)" reads
    as "the system actually checked".
    """
    return NextActionDTO(
        entity_type=entity_type,
        entity_id=entity_id,
        kind=NextActionKind.IDLE,
        priority=NextActionPriority.IDLE,
        reason_code=reason,
        title="Nothing to do right now",
        title_key="app.next_action.idle.title",
        hint="No reminders, no pending handoff, no contact gap.",
        hint_key="app.next_action.idle.hint",
    )


def _priority_from_due(due_at: Optional[datetime]) -> NextActionPriority:
    """Map a reminder's `due_at` to a priority bucket the UI can colour-code.

    Comparisons are timezone-naive when the input is naive, otherwise
    timezone-aware. Reminder rows in this codebase are inconsistent on this
    front; we normalise both sides to naive UTC to avoid TypeError on `<`.
    """
    if due_at is None:
        return NextActionPriority.NORMAL
    now = datetime.now(timezone.utc)
    cmp_now = now if due_at.tzinfo is not None else now.replace(tzinfo=None)
    if due_at < cmp_now:
        return NextActionPriority.CRITICAL
    delta = due_at - cmp_now
    if delta.total_seconds() < 24 * 3600:
        return NextActionPriority.HIGH
    return NextActionPriority.NORMAL


def _format_reminder_hint(due_at: Optional[datetime]) -> Optional[str]:
    if due_at is None:
        return None
    now = datetime.now(timezone.utc)
    cmp_now = now if due_at.tzinfo is not None else now.replace(tzinfo=None)
    delta = due_at - cmp_now
    seconds = int(delta.total_seconds())
    if seconds < 0:
        # Don't bother humanising — frontend will render a richer "X hours
        # overdue" using its own i18n. We just signal it's overdue.
        return "Overdue"
    if seconds < 3600:
        return f"Due in {max(1, seconds // 60)} minutes"
    if seconds < 24 * 3600:
        return f"Due in {seconds // 3600} hours"
    return f"Due in {seconds // 86400} days"


__all__ = [
    "NextActionDTO",
    "NextActionKind",
    "NextActionPriority",
    "compute_candidate_next_action",
    "compute_lead_next_action",
    "compute_vacancy_next_action",
    "compute_document_next_action",
    "compute_thread_next_action",
]
