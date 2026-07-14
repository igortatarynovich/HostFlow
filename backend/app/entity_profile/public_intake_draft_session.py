"""Lead-first public intake draft session (P5C).

Public apply flow stores draft state on a Lead intake record. Candidate rows are
created only when Decision Layer + Outcome Executor return ``create_candidate``.
Legacy Candidate-backed draft tokens remain supported for in-flight sessions.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite

from backend.app.entity_profile.decision_layer import (
    DecisionInput,
    DecisionResult,
    IngestDecisionContext,
    IngestDisposition,
    evaluate_ingest_decision,
    stamp_decision_blocks,
)
from backend.app.entity_profile.ingest_runtime import (
    prepare_public_intake_runtime,
    resolve_public_intake_source_profile_id,
)
from backend.app.entity_profile.outcome_executor import execute_outcome_decision
from backend.app.models import Candidate, Lead
from backend.app.modules.leads import crud as leads_crud
from backend.app.services.intake_channel_candidate import public_intake_stable_contact_key

PUBLIC_INTAKE_DRAFT_V1 = "public_intake_draft_v1"
PUBLIC_INTAKE_SOURCE = "public_intake"
INTAKE_TOKEN_TTL_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_token() -> str:
    return secrets.token_urlsafe(24)


def _record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def draft_external_id(*, email: Optional[str], phone: Optional[str], phone_country_code: Optional[str]) -> str:
    stable = public_intake_stable_contact_key(
        email=email,
        phone=phone,
        phone_country_code=phone_country_code,
    )
    return f"public-intake-draft:{stable}"


def get_public_intake_draft_block(lead: Lead) -> dict[str, Any]:
    normalized = lead.normalized if isinstance(getattr(lead, "normalized", None), dict) else {}
    block = normalized.get(PUBLIC_INTAKE_DRAFT_V1)
    return dict(block) if isinstance(block, dict) else {}


def set_public_intake_draft_block(lead: Lead, block: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(lead.normalized) if isinstance(getattr(lead, "normalized", None), dict) else {}
    normalized[PUBLIC_INTAKE_DRAFT_V1] = dict(block)
    lead.normalized = normalized
    return normalized


def is_public_intake_draft_lead(lead: Lead) -> bool:
    block = get_public_intake_draft_block(lead)
    return bool(block.get("intake_token"))


@dataclass
class PublicIntakeSession:
    kind: Literal["lead_draft", "legacy_candidate", "questionnaire_invite"]
    tenant_id: str
    token: str
    lead: Optional[Lead] = None
    candidate: Optional[Candidate] = None
    invite: Optional["LeadQuestionnaireInvite"] = None

    @property
    def lead_id(self) -> Optional[str]:
        return str(self.lead.id) if self.lead is not None else None

    @property
    def candidate_id(self) -> Optional[str]:
        if self.candidate is not None:
            return str(self.candidate.id)
        if self.lead is not None and getattr(self.lead, "candidate_id", None):
            return str(self.lead.candidate_id)
        return None

    @property
    def vacancy_id(self) -> Optional[str]:
        if self.candidate is not None and getattr(self.candidate, "vacancy_id", None):
            return str(self.candidate.vacancy_id)
        block = get_public_intake_draft_block(self.lead) if self.lead is not None else {}
        vid = block.get("vacancy_id")
        if vid:
            return str(vid)
        if self.lead is not None and getattr(self.lead, "vacancy_id", None):
            return str(self.lead.vacancy_id)
        return None


async def _find_lead_by_questionnaire_invite_token(
    db: AsyncSession,
    *,
    tenant_id: str,
    token: str,
) -> tuple[Optional[Lead], Optional["LeadQuestionnaireInvite"]]:
    from backend.app.modules.leads.lead_questionnaire_invite import find_questionnaire_invite_by_token

    invite = await find_questionnaire_invite_by_token(db, token=token)
    if invite is None or str(invite.tenant_id) != str(tenant_id):
        return None, None
    lead = await db.get(Lead, str(invite.lead_id))
    if lead is None or str(lead.tenant_id) != str(tenant_id):
        return None, None
    return lead, invite


async def find_lead_draft_by_intake_token(
    db: AsyncSession,
    *,
    tenant_id: str,
    token: str,
) -> Optional[Lead]:
    lead, _invite = await _find_lead_by_questionnaire_invite_token(
        db,
        tenant_id=str(tenant_id),
        token=token,
    )
    if lead is not None:
        return lead

    stmt = select(Lead).where(
        Lead.tenant_id == str(tenant_id),
        Lead.source == PUBLIC_INTAKE_SOURCE,
        Lead.stage == "intake_draft",
    )
    result = await db.execute(stmt)
    for lead in result.scalars().all():
        block = get_public_intake_draft_block(lead)
        if str(block.get("intake_token") or "") == str(token):
            return lead
    return None


async def find_lead_draft_by_contact(
    db: AsyncSession,
    *,
    tenant_id: str,
    email: Optional[str],
    phone: Optional[str],
    phone_country_code: Optional[str],
) -> Optional[Lead]:
    external_id = draft_external_id(email=email, phone=phone, phone_country_code=phone_country_code)
    lead = await leads_crud.get_lead_by_external_id(
        db,
        tenant_id=str(tenant_id),
        source=PUBLIC_INTAKE_SOURCE,
        external_id=external_id,
    )
    if lead is None:
        return None
    if str(getattr(lead, "stage", "") or "") != "intake_draft":
        return None
    return lead


async def resolve_public_intake_lead_draft_tenant_id(db: AsyncSession, token: str) -> Optional[str]:
    from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite

    invite_tid = await db.scalar(
        select(LeadQuestionnaireInvite.tenant_id)
        .where(LeadQuestionnaireInvite.token == str(token))
        .limit(1)
    )
    if invite_tid:
        return str(invite_tid)

    stmt = select(Lead.tenant_id, Lead.normalized).where(
        Lead.source == PUBLIC_INTAKE_SOURCE,
        Lead.stage == "intake_draft",
    )
    result = await db.execute(stmt)
    for tenant_id, normalized in result.all():
        if not isinstance(normalized, dict):
            continue
        block = normalized.get(PUBLIC_INTAKE_DRAFT_V1)
        if isinstance(block, dict) and str(block.get("intake_token") or "") == str(token):
            return str(tenant_id)
    return None


async def find_lead_draft_by_status_share_token(
    db: AsyncSession,
    *,
    tenant_id: str,
    share_token: str,
) -> Optional[Lead]:
    stmt = select(Lead).where(
        Lead.tenant_id == str(tenant_id),
        Lead.source == PUBLIC_INTAKE_SOURCE,
        Lead.stage == "intake_draft",
    )
    result = await db.execute(stmt)
    for lead in result.scalars().all():
        block = get_public_intake_draft_block(lead)
        if str(block.get("status_share_token") or "") == str(share_token):
            return lead
    return None


async def resolve_public_intake_lead_draft_status_tenant_id(
    db: AsyncSession,
    share_token: str,
) -> Optional[str]:
    stmt = select(Lead.tenant_id, Lead.normalized).where(
        Lead.source == PUBLIC_INTAKE_SOURCE,
        Lead.stage == "intake_draft",
    )
    result = await db.execute(stmt)
    for tenant_id, normalized in result.all():
        if not isinstance(normalized, dict):
            continue
        block = normalized.get(PUBLIC_INTAKE_DRAFT_V1)
        if isinstance(block, dict) and str(block.get("status_share_token") or "") == str(share_token):
            return str(tenant_id)
    return None


async def resolve_public_intake_session(
    db: AsyncSession,
    *,
    tenant_id: str,
    token: str,
    legacy_loader,
) -> PublicIntakeSession:
    """Load questionnaire invite, lead-first draft session, or legacy candidate draft."""
    from backend.app.modules.leads.lead_questionnaire_invite import INVITE_STATUS_SUBMITTED

    invite_lead, invite = await _find_lead_by_questionnaire_invite_token(
        db,
        tenant_id=str(tenant_id),
        token=token,
    )
    if invite is not None and invite_lead is not None:
        if invite.expires_at and invite.expires_at < _now() and invite.status != INVITE_STATUS_SUBMITTED:
            raise HTTPException(status_code=410, detail="Intake link expired")
        return PublicIntakeSession(
            kind="questionnaire_invite",
            tenant_id=str(tenant_id),
            token=token,
            lead=invite_lead,
            invite=invite,
        )

    stmt = select(Lead).where(
        Lead.tenant_id == str(tenant_id),
        Lead.source == PUBLIC_INTAKE_SOURCE,
        Lead.stage == "intake_draft",
    )
    result = await db.execute(stmt)
    for lead in result.scalars().all():
        block = get_public_intake_draft_block(lead)
        if str(block.get("intake_token") or "") != str(token):
            continue
        expires_at = block.get("intake_token_expires_at")
        if expires_at:
            try:
                exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                if exp < _now():
                    raise HTTPException(status_code=410, detail="Intake link expired")
            except ValueError:
                pass
        return PublicIntakeSession(
            kind="lead_draft",
            tenant_id=str(tenant_id),
            token=token,
            lead=lead,
        )

    candidate = await legacy_loader(db, UUID(str(tenant_id)), token)
    return PublicIntakeSession(
        kind="legacy_candidate",
        tenant_id=str(tenant_id),
        token=token,
        candidate=candidate,
    )


async def _resolve_company_context(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: Optional[str],
    application_kind: str,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    own_company_id: Optional[str] = None
    company_id: Optional[str] = None
    if vacancy_id:
        from backend.app.models.vacancy import Vacancy

        vacancy = await db.get(Vacancy, vacancy_id)
        if vacancy is not None:
            company_id = str(getattr(vacancy, "company_id", None) or "").strip() or None
            own_company_id = str(getattr(vacancy, "own_company_id", None) or "").strip() or None
    if not company_id:
        company_id = await leads_crud.get_default_company_id(db, str(tenant_id))
    if application_kind == "client" and not own_company_id:
        from backend.app.models.own_company import OwnCompany

        row = await db.execute(
            select(OwnCompany.id)
            .where(OwnCompany.tenant_id == str(tenant_id), OwnCompany.is_archived.is_(False))
            .order_by(OwnCompany.created_at.asc())
            .limit(1)
        )
        own_company_id = str(row.scalar_one_or_none() or "").strip() or None
    return own_company_id, company_id, vacancy_id


async def create_or_reuse_public_intake_lead_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    contacts: dict[str, Any],
    intake_source: str,
    vacancy_id: Optional[str],
    application_kind: str,
    lead_form_meta: Optional[dict[str, Any]],
    client_company: Optional[dict[str, Any]],
) -> tuple[Lead, str, datetime]:
    """Create or refresh a Lead draft session — no Candidate INSERT."""
    email = contacts.get("email")
    phone = contacts.get("phone")
    phone_country_code = contacts.get("phone_country_code")
    external_id = draft_external_id(email=email, phone=phone, phone_country_code=phone_country_code)
    now = _now()
    expires_at = now + timedelta(days=INTAKE_TOKEN_TTL_DAYS)

    existing = await find_lead_draft_by_contact(
        db,
        tenant_id=str(tenant_id),
        email=str(email) if email else None,
        phone=str(phone) if phone else None,
        phone_country_code=str(phone_country_code) if phone_country_code else None,
    )
    intake_state: dict[str, Any] = {
        "contacts": dict(contacts),
        "personal": {},
        "experience": {},
        "agreements": {},
        "application_kind": application_kind,
    }
    if client_company:
        intake_state["client_company"] = dict(client_company)
    if lead_form_meta:
        intake_state["lead_form"] = dict(lead_form_meta)

    if existing is not None:
        block = get_public_intake_draft_block(existing)
        token = str(block.get("intake_token") or "") or _generate_token()
        state = _record(block.get("intake_state")) or intake_state
        state["contacts"] = {**dict(state.get("contacts") or {}), **dict(contacts)}
        if client_company:
            state["client_company"] = {**dict(state.get("client_company") or {}), **dict(client_company)}
        if lead_form_meta:
            state["lead_form"] = dict(lead_form_meta)
        state["application_kind"] = application_kind
        block.update(
            {
                "intake_token": token,
                "intake_token_created_at": now.isoformat(),
                "intake_token_expires_at": expires_at.isoformat(),
                "intake_status": "draft",
                "intake_state": state,
                "vacancy_id": vacancy_id,
                "source_channel": intake_source,
            }
        )
        if not block.get("status_share_token"):
            block["status_share_token"] = _generate_token()
        existing.vacancy_id = vacancy_id
        normalized = set_public_intake_draft_block(existing, block)
        normalized.setdefault("email", email)
        normalized.setdefault("phone", phone)
        existing.normalized = normalized
        existing.payload = {
            **(_record(existing.payload)),
            "intake_state": state,
            "public_intake_draft": True,
        }
        await db.flush()
        return existing, token, expires_at

    own_company_id, company_id, vacancy_id = await _resolve_company_context(
        db,
        tenant_id=str(tenant_id),
        vacancy_id=vacancy_id,
        application_kind=application_kind,
    )
    is_client = application_kind == "client"
    if is_client and not own_company_id:
        raise ValueError("own_company_id is required for client intake draft")

    if not is_client and company_id:
        from backend.app.services.launch_search_vacancy_setup import ensure_recruitment_funnels_for_company

        try:
            await ensure_recruitment_funnels_for_company(
                db,
                tenant_id=str(tenant_id),
                company_id=str(company_id),
            )
        except Exception:
            pass

    token = _generate_token()
    block = {
        "intake_token": token,
        "intake_token_created_at": now.isoformat(),
        "intake_token_expires_at": expires_at.isoformat(),
        "intake_status": "draft",
        "intake_submitted_at": None,
        "intake_state": intake_state,
        "status_share_token": _generate_token(),
        "vacancy_id": vacancy_id,
        "source_channel": intake_source,
        "pending_documents": [],
    }
    normalized: dict[str, Any] = {
        PUBLIC_INTAKE_DRAFT_V1: block,
        "email": email,
        "phone": phone,
    }
    lead = await leads_crud.create_lead(
        db,
        tenant_id=str(tenant_id),
        own_company_id=own_company_id if is_client else None,
        company_id=None if is_client else company_id,
        vacancy_id=None if is_client else vacancy_id,
        payload={"intake_state": intake_state, "public_intake_draft": True, "source": intake_source},
        normalized=normalized,
        source=PUBLIC_INTAKE_SOURCE,
        external_id=external_id,
        lead_type="client" if is_client else "candidate",
        lead_target_type="client_lead" if is_client else "candidate",
    )
    lead.stage = "intake_draft"
    lead.status = "new"
    await db.flush()
    return lead, token, expires_at


def session_intake_state(session: PublicIntakeSession) -> dict[str, Any]:
    if session.kind == "questionnaire_invite" and session.invite is not None:
        from backend.app.modules.leads.lead_questionnaire_invite import invite_intake_state

        return invite_intake_state(session.invite)
    if session.kind == "legacy_candidate" and session.candidate is not None:
        state = session.candidate.intake_state
        return dict(state) if isinstance(state, dict) else {}
    if session.lead is not None:
        block = get_public_intake_draft_block(session.lead)
        state = block.get("intake_state")
        return dict(state) if isinstance(state, dict) else {}
    return {}


def write_session_intake_state(session: PublicIntakeSession, state: dict[str, Any]) -> None:
    if session.kind == "questionnaire_invite" and session.invite is not None:
        from backend.app.modules.leads.lead_questionnaire_invite import write_invite_intake_state

        write_invite_intake_state(session.invite, state)
        return
    if session.kind == "legacy_candidate" and session.candidate is not None:
        session.candidate.intake_state = dict(state)
        return
    if session.lead is not None:
        block = get_public_intake_draft_block(session.lead)
        block["intake_state"] = dict(state)
        set_public_intake_draft_block(session.lead, block)


def session_intake_status(session: PublicIntakeSession) -> str:
    if session.kind == "questionnaire_invite" and session.invite is not None:
        from backend.app.modules.leads.lead_questionnaire_invite import INVITE_STATUS_SUBMITTED

        if session.invite.status == INVITE_STATUS_SUBMITTED:
            return "submitted"
        return "draft"
    if session.kind == "legacy_candidate" and session.candidate is not None:
        if session.candidate.intake_submitted_at:
            return "submitted"
        return str(session.candidate.intake_status or "draft")
    block = get_public_intake_draft_block(session.lead) if session.lead else {}
    return str(block.get("intake_status") or "draft")


def session_created_at(session: PublicIntakeSession) -> Optional[datetime]:
    if session.kind == "questionnaire_invite" and session.invite is not None:
        return session.invite.created_at
    if session.kind == "legacy_candidate" and session.candidate is not None:
        return getattr(session.candidate, "intake_token_created_at", None)
    block = get_public_intake_draft_block(session.lead) if session.lead else {}
    raw = block.get("intake_token_created_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def session_expires_at(session: PublicIntakeSession) -> Optional[datetime]:
    if session.kind == "questionnaire_invite" and session.invite is not None:
        return session.invite.expires_at
    if session.kind == "legacy_candidate" and session.candidate is not None:
        return getattr(session.candidate, "intake_token_expires_at", None)
    block = get_public_intake_draft_block(session.lead) if session.lead else {}
    raw = block.get("intake_token_expires_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def session_submitted_at(session: PublicIntakeSession) -> Optional[datetime]:
    if session.kind == "questionnaire_invite" and session.invite is not None:
        return session.invite.submitted_at
    if session.kind == "legacy_candidate" and session.candidate is not None:
        return getattr(session.candidate, "intake_submitted_at", None)
    block = get_public_intake_draft_block(session.lead) if session.lead else {}
    raw = block.get("intake_submitted_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def session_status_share_token(session: PublicIntakeSession) -> Optional[str]:
    if session.kind == "legacy_candidate" and session.candidate is not None:
        return getattr(session.candidate, "status_share_token", None)
    block = get_public_intake_draft_block(session.lead) if session.lead else {}
    return str(block.get("status_share_token") or "") or None


def mark_session_submitted(session: PublicIntakeSession) -> None:
    now = _now()
    if session.kind == "questionnaire_invite" and session.invite is not None:
        session.invite.submitted_at = now
        return
    if session.kind == "legacy_candidate" and session.candidate is not None:
        session.candidate.intake_status = "submitted"
        session.candidate.intake_submitted_at = now
        session.candidate.stage = "questionnaire_submitted"
        return
    if session.lead is not None:
        block = get_public_intake_draft_block(session.lead)
        block["intake_status"] = "submitted"
        block["intake_submitted_at"] = now.isoformat()
        set_public_intake_draft_block(session.lead, block)
        session.lead.stage = "questionnaire_submitted"


def build_candidate_payload_from_intake_state(
    *,
    tenant_id: str,
    intake_state: dict[str, Any],
    vacancy_id: Optional[str],
    source: str,
) -> dict[str, Any]:
    contacts = _record(intake_state.get("contacts"))
    personal = _record(intake_state.get("personal"))
    experience = _record(intake_state.get("experience"))
    full_name = str(personal.get("full_name") or "").strip()
    first_name = "Candidate"
    last_name = "Draft"
    if full_name:
        parts = [p for p in full_name.split() if p]
        if parts:
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else parts[0]
    payload: dict[str, Any] = {
        "first_name": first_name,
        "last_name": last_name,
        "phone": contacts.get("phone"),
        "phone_country_code": contacts.get("phone_country_code"),
        "email": contacts.get("email"),
        "vacancy_id": vacancy_id,
        "source": source,
        "stage": "docs_wait",
        "origin": {source: intake_state},
    }
    personal_fields = {
        k: v
        for k, v in {
            "citizenship": personal.get("citizenship"),
            "residency_status": personal.get("residency_status"),
            "in_poland": personal.get("in_poland"),
            "birth_date": personal.get("birth_date"),
            "current_location": personal.get("current_location"),
            "frigo_experience": personal.get("frigo_experience"),
            "has_adr": personal.get("has_adr"),
        }.items()
        if v is not None
    }
    if personal_fields:
        payload["personal_data"] = personal_fields
    extra: dict[str, Any] = {}
    if experience:
        extra["experience"] = experience
    if extra:
        payload["extra"] = extra
    if contacts:
        payload["contacts"] = contacts
    return payload


async def submit_public_intake_lead_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    intake_state: dict[str, Any],
    source: str = PUBLIC_INTAKE_SOURCE,
) -> tuple[DecisionResult, Optional[str]]:
    """Run Decision Layer + Outcome Executor for lead-first public submit."""
    _lf_meta = intake_state.get("lead_form") if isinstance(intake_state.get("lead_form"), dict) else {}
    lead_form_id = str(_lf_meta.get("id") or "").strip() or None
    public_slug = str(_lf_meta.get("public_slug") or "").strip() or None
    vacancy_id = str(getattr(lead, "vacancy_id", None) or "").strip() or None
    if not vacancy_id:
        block = get_public_intake_draft_block(lead)
        vacancy_id = str(block.get("vacancy_id") or "").strip() or None

    intake_source_profile_id = await resolve_public_intake_source_profile_id(
        db,
        tenant_id=str(tenant_id),
        lead_form_id=lead_form_id,
        public_slug=public_slug,
    )
    envelope, _profile_view, _validation = await prepare_public_intake_runtime(
        db,
        tenant_id=str(tenant_id),
        intake_state=intake_state,
        intake_source_profile_id=intake_source_profile_id,
        candidate_profile_id=None,
        vacancy_id=vacancy_id,
    )
    intake_state["ingest_envelope_v1"] = envelope.to_dict()
    if envelope.entity_profile_code:
        intake_state["entity_profile_code"] = envelope.entity_profile_code

    flat_normalized = dict(envelope.normalized_payload or {})
    flat_normalized["ingest_envelope_v1"] = envelope.to_dict()
    if envelope.entity_profile_code:
        flat_normalized["entity_profile_code"] = envelope.entity_profile_code

    company_id = str(getattr(lead, "company_id", None) or "").strip() or None
    if not company_id and vacancy_id:
        from backend.app.models.vacancy import Vacancy

        vacancy = await db.get(Vacancy, vacancy_id)
        if vacancy is not None:
            company_id = str(getattr(vacancy, "company_id", None) or "").strip() or None
    if not company_id:
        company_id = await leads_crud.get_default_company_id(db, str(tenant_id))

    contacts = _record(intake_state.get("contacts"))
    decision_input = DecisionInput.from_normalized(
        tenant_id=str(tenant_id),
        source=source,
        normalized=flat_normalized,
        vacancy_id=vacancy_id,
        company_id=company_id,
    )
    application_kind = str(intake_state.get("application_kind") or "candidate").strip().lower()
    is_client = application_kind == "client"
    decision = await evaluate_ingest_decision(
        db,
        decision_input,
        ctx=IngestDecisionContext(
            may_auto_convert=not is_client,
            triage_gate_bypass=not is_client,
            vacancy_resolved=bool(vacancy_id),
            pool_manual_convert_ready=not is_client,
            sales_lead_without_candidate=is_client,
        ),
        email=contacts.get("email"),
        phone=contacts.get("phone"),
    )
    stamp_decision_blocks(flat_normalized, decision_input, decision)
    intake_state["decision_input_v1"] = decision_input.to_dict()
    intake_state["decision_result_v1"] = decision.to_dict()
    intake_state["decision_result_v1"]["entity_profile_code"] = decision_input.entity_profile_code

    lead.normalized = {**flat_normalized, PUBLIC_INTAKE_DRAFT_V1: get_public_intake_draft_block(lead)}
    block = get_public_intake_draft_block(lead)
    block["intake_state"] = intake_state
    block["decision_result_v1"] = intake_state["decision_result_v1"]
    set_public_intake_draft_block(lead, block)

    created_candidate_id: Optional[str] = None
    if (
        not is_client
        and decision.disposition == IngestDisposition.create_candidate.value
        and decision.may_create_candidate
    ):
        candidate_payload = build_candidate_payload_from_intake_state(
            tenant_id=str(tenant_id),
            intake_state=intake_state,
            vacancy_id=vacancy_id,
            source=source,
        )
        outcome = await execute_outcome_decision(
            db,
            tenant_id=str(tenant_id),
            lead=lead,
            normalized=flat_normalized,
            source=source,
            decision=decision,
            candidate_payload=candidate_payload,
        )
        if outcome is not None:
            created_candidate_id = outcome.entity_id
            lead.candidate_id = created_candidate_id
            lead.status = "processed"
    elif decision.disposition == IngestDisposition.blocked_duplicate.value:
        attach_id = decision.attach_candidate_id
        if attach_id:
            lead.candidate_id = str(attach_id)
            lead.status = "duplicated"
    elif is_client:
        lead.status = "processed"
    else:
        lead.status = "new"

    lead.stage = "questionnaire_submitted"
    lead.error = None
    await db.flush()
    return decision, created_candidate_id
