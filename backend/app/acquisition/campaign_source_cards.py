"""Compose human-readable Source card fields for Campaign/Flight bindings.

Read-only: joins existing Forms / Intake / Meta mapping SoT + activity timestamps.
Does not persist Acquisition copies of provider metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.endpoint_activity import form_endpoint_id, intake_source_endpoint_id
from backend.app.acquisition.sources_read import parse_meta_form_id
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import MetaLeadFormMapping
from backend.app.models.tenant_lead_form import TenantLeadForm

_SUBMISSION_EVENT_TYPES = frozenset({"SubmissionReceived", "LeadCreated"})


def parse_meta_page_id(external_key_secondary: str) -> Optional[str]:
    raw = str(external_key_secondary or "").strip()
    prefix = "page_id:"
    if raw.startswith(prefix):
        pid = raw[len(prefix) :].strip()
        return pid or None
    return None


def humanize_meta_profile_name(name: Optional[str], *, form_id: Optional[str] = None) -> Optional[str]:
    """Drop technical 'Meta form {id}' placeholders when a real label is unavailable."""
    n = str(name or "").strip()
    if not n:
        return None
    if form_id and n == f"Meta form {form_id}":
        return None
    if n.lower().startswith("meta form ") and n[10:].strip().isdigit():
        return None
    return n


def form_publication_status(
    *,
    is_active: bool,
    public_slug: Optional[str],
    published_at: Optional[datetime] = None,
) -> str:
    if not is_active:
        return "inactive"
    if public_slug and str(public_slug).strip():
        return "published"
    # published_at without slug still counts as unpublished public surface
    _ = published_at
    return "draft"


@dataclass(frozen=True)
class FormCardEnrichment:
    form_is_active: bool
    publication_status: str
    is_public: bool
    last_submission_at: Optional[datetime]


@dataclass(frozen=True)
class IntakeSourceCardEnrichment:
    profile_is_active: bool
    lead_form_name: Optional[str]
    page_id: Optional[str]
    page_name: Optional[str]
    meta_form_id: Optional[str]
    binding_status: str
    active_binding_count: int
    last_submission_at: Optional[datetime]
    display_title: str


async def load_last_submission_by_endpoint(
    db: AsyncSession,
    *,
    tenant_id: str,
    endpoint_ids: list[str],
) -> dict[str, datetime]:
    if not endpoint_ids:
        return {}
    rows = (
        await db.execute(
            select(
                AcquisitionActivityEvent.endpoint_id,
                AcquisitionActivityEvent.occurred_at,
            )
            .where(
                AcquisitionActivityEvent.tenant_id == str(tenant_id),
                AcquisitionActivityEvent.endpoint_id.in_(endpoint_ids),
                AcquisitionActivityEvent.event_type.in_(list(_SUBMISSION_EVENT_TYPES)),
            )
            .order_by(AcquisitionActivityEvent.occurred_at.desc())
        )
    ).all()
    out: dict[str, datetime] = {}
    for endpoint_id, occurred_at in rows:
        eid = str(endpoint_id or "").strip()
        if not eid or occurred_at is None or eid in out:
            continue
        out[eid] = occurred_at
    return out


async def load_meta_form_mappings_by_form_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_ids: set[str],
) -> dict[str, MetaLeadFormMapping]:
    if not form_ids:
        return {}
    rows = (
        await db.execute(
            select(MetaLeadFormMapping).where(
                MetaLeadFormMapping.tenant_id == str(tenant_id),
                MetaLeadFormMapping.form_id.in_(list(form_ids)),
            )
        )
    ).scalars().all()
    return {str(m.form_id): m for m in rows}


def enrich_form_card(
    form: Optional[TenantLeadForm],
    *,
    last_submission_at: Optional[datetime],
) -> FormCardEnrichment:
    if form is None:
        return FormCardEnrichment(
            form_is_active=False,
            publication_status="inactive",
            is_public=False,
            last_submission_at=last_submission_at,
        )
    slug = str(form.public_slug or "").strip() or None
    return FormCardEnrichment(
        form_is_active=bool(form.is_active),
        publication_status=form_publication_status(
            is_active=bool(form.is_active),
            public_slug=slug,
            published_at=getattr(form, "published_at", None),
        ),
        is_public=bool(slug),
        last_submission_at=last_submission_at,
    )


def enrich_intake_source_card(
    profile: Optional[IntakeSourceProfile],
    bindings: list[IntakeSourceBinding],
    *,
    meta_map: Optional[MetaLeadFormMapping],
    last_submission_at: Optional[datetime],
) -> IntakeSourceCardEnrichment:
    active_bindings = [b for b in bindings if bool(b.is_active)]
    active_count = len(active_bindings)
    pick = (active_bindings or bindings or [None])[0]

    meta_form_id: Optional[str] = None
    page_id: Optional[str] = None
    if pick is not None:
        meta_form_id = parse_meta_form_id(pick.external_key)
        page_id = parse_meta_page_id(pick.external_key_secondary or "")
    if not meta_form_id and profile is not None:
        code = str(profile.code or "")
        if code.startswith("meta-form-"):
            meta_form_id = code[len("meta-form-") :] or None
    if meta_map is not None:
        if not meta_form_id:
            meta_form_id = str(meta_map.form_id or "").strip() or None
        if not page_id:
            page_id = str(meta_map.page_id or "").strip() or None

    lead_form_name = None
    if meta_map is not None:
        lead_form_name = str(meta_map.form_name or "").strip() or None
    if not lead_form_name and pick is not None:
        lead_form_name = humanize_meta_profile_name(pick.label, form_id=meta_form_id)
    if not lead_form_name and profile is not None:
        lead_form_name = humanize_meta_profile_name(profile.name, form_id=meta_form_id)

    # Page display name is not persisted in SoT without a Graph sync — leave null.
    page_name: Optional[str] = None

    profile_active = bool(profile.is_active) if profile else False
    if active_count > 0 and profile_active:
        binding_status = "bound"
    elif active_count > 0:
        binding_status = "bound_inactive_profile"
    else:
        binding_status = "unbound"

    display_title = (
        lead_form_name
        or (str(profile.name).strip() if profile and profile.name else None)
        or (str(profile.code).strip() if profile and profile.code else None)
        or "Источник"
    )

    return IntakeSourceCardEnrichment(
        profile_is_active=profile_active,
        lead_form_name=lead_form_name,
        page_id=page_id,
        page_name=page_name,
        meta_form_id=meta_form_id,
        binding_status=binding_status,
        active_binding_count=active_count,
        last_submission_at=last_submission_at,
        display_title=display_title,
    )


def form_card_as_dict(e: FormCardEnrichment) -> dict[str, Any]:
    return {
        "form_is_active": e.form_is_active,
        "publication_status": e.publication_status,
        "is_public": e.is_public,
        "last_submission_at": e.last_submission_at,
    }


def intake_card_as_dict(e: IntakeSourceCardEnrichment) -> dict[str, Any]:
    return {
        "profile_is_active": e.profile_is_active,
        "lead_form_name": e.lead_form_name,
        "page_id": e.page_id,
        "page_name": e.page_name,
        "meta_form_id": e.meta_form_id,
        "binding_status": e.binding_status,
        "active_binding_count": e.active_binding_count,
        "last_submission_at": e.last_submission_at,
        "display_title": e.display_title,
    }
