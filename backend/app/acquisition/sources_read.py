"""Marketing Sources read model (Acquisition UI Cutover C-3).

Aggregates existing IntakeSourceProfile + bindings + Flight links + Meta
webhook/OAuth signals + mapping_rules into a list projection.
No new persistent health entities and no write paths.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from urllib.parse import quote, urlencode

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.endpoint_activity import intake_source_endpoint_id
from backend.app.constants.spa_paths import (
    MARKETING_NEW,
    MARKETING_SOURCES,
    SETTINGS_INTEGRATIONS_META,
)
from backend.app.models.acquisition_activity_event import AcquisitionActivityEvent
from backend.app.models.campaign import Campaign, CampaignRun, CampaignRunIntakeSource
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import Lead, MetaLeadCredential, MetaLeadFormMapping, MetaLeadSettings
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.modules.intake_routing.meta_bridge import meta_external_key

CONNECTION_CONNECTED = "connected"
CONNECTION_ATTENTION = "attention"
CONNECTION_DISCONNECTED = "disconnected"

HEALTH_READY = "ready"
HEALTH_NEEDS_REVIEW = "needs_review"
HEALTH_BROKEN = "broken"

# Operator-facing routing issue (C-3 visibility). Runtime stop of profile_default = next PR.
ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT = "missing_campaign_flight"
ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT_MESSAGE = (
    "Campaign/Flight for this Ad ID are not configured."
)

_WAITING_LEAD_STATUSES = frozenset({"needs_routing"})
_WAITING_LEADS_CAP = 5000

_SUBMISSION_EVENT_TYPES = frozenset({"SubmissionReceived", "LeadCreated"})
_ERROR_EVENT_TYPES = frozenset(
    {
        "RoutingFailed",
        "SubmissionRejected",
        "DeliveryErrorOccurred",
        "ProviderSubmissionRejected",
    }
)
_FAILED_SIGNATURE = frozenset({"fail", "failed", "invalid", "error", "mismatch"})


@dataclass(frozen=True)
class SourceSummary:
    source_id: str
    provider: str
    display_name: str
    connection_status: str
    mapping_health: str
    last_submission_at: Optional[datetime]
    last_error_at: Optional[datetime]
    last_error_code: Optional[str]
    campaign_count: int
    flight_count: int
    mapping_path: str
    test_lead_path: str
    settings_path: str
    code: str
    is_active: bool
    mapping_rules_count: int
    active_binding_count: int
    waiting_submissions: int = 0
    last_problematic_ad_id: Optional[str] = None
    routing_issue_code: Optional[str] = None
    routing_issue_message: Optional[str] = None
    setup_campaign_flight_path: Optional[str] = None
    # C-3.1 — operator-facing inventory columns (errata deferred set minus account/portfolio).
    page_id: Optional[str] = None
    page_name: Optional[str] = None
    provider_form: Optional[str] = None
    destination: Optional[str] = None
    destination_label: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "connection_status": self.connection_status,
            "mapping_health": self.mapping_health,
            "last_submission_at": self.last_submission_at,
            "last_error_at": self.last_error_at,
            "last_error_code": self.last_error_code,
            "campaign_count": self.campaign_count,
            "flight_count": self.flight_count,
            "mapping_path": self.mapping_path,
            "test_lead_path": self.test_lead_path,
            "settings_path": self.settings_path,
            "code": self.code,
            "is_active": self.is_active,
            "mapping_rules_count": self.mapping_rules_count,
            "active_binding_count": self.active_binding_count,
            "waiting_submissions": self.waiting_submissions,
            "last_problematic_ad_id": self.last_problematic_ad_id,
            "routing_issue_code": self.routing_issue_code,
            "routing_issue_message": self.routing_issue_message,
            "setup_campaign_flight_path": self.setup_campaign_flight_path,
            "page_id": self.page_id,
            "page_name": self.page_name,
            "provider_form": self.provider_form,
            "destination": self.destination,
            "destination_label": self.destination_label,
        }


def parse_meta_form_id(external_key: str) -> Optional[str]:
    key = str(external_key or "").strip()
    prefix = "form_id:"
    if key.startswith(prefix):
        fid = key[len(prefix) :].strip()
        return fid or None
    return None


def compute_connection_status(
    *,
    is_active: bool,
    provider: str,
    active_binding_count: int,
    last_signature_status: Optional[str],
    has_meta_credential: bool,
) -> str:
    if not is_active:
        return CONNECTION_DISCONNECTED
    provider_l = str(provider or "").strip().lower()
    sig = str(last_signature_status or "").strip().lower()
    if provider_l == "meta":
        if sig in _FAILED_SIGNATURE:
            return CONNECTION_DISCONNECTED
        if not has_meta_credential:
            return CONNECTION_ATTENTION
        if active_binding_count <= 0:
            return CONNECTION_ATTENTION
        return CONNECTION_CONNECTED
    if active_binding_count <= 0 and provider_l not in {"public_intake", "manual", "unknown", ""}:
        return CONNECTION_ATTENTION
    return CONNECTION_CONNECTED


def compute_mapping_health(
    *,
    connection_status: str,
    mapping_rules_count: int,
    last_error_code: Optional[str],
) -> str:
    if connection_status == CONNECTION_DISCONNECTED:
        return HEALTH_BROKEN
    err = str(last_error_code or "").strip().lower()
    if err and err not in {"", "none", "ok"}:
        # Recent ingest/routing failure → operator must fix before trusting Ready.
        if any(token in err for token in ("routing", "mapping", "normalize", "reject", "webhook", "signature")):
            return HEALTH_BROKEN
    if mapping_rules_count <= 0:
        return HEALTH_NEEDS_REVIEW
    if connection_status == CONNECTION_ATTENTION:
        return HEALTH_NEEDS_REVIEW
    return HEALTH_READY


def build_source_paths(
    *,
    source_id: str,
    provider: str,
    meta_form_id: Optional[str],
    lead_form_id: Optional[str],
) -> tuple[str, str, str]:
    """Return (mapping_path, test_lead_path, settings_path).

    C-4: ``test_lead_path`` is Marketing-native (``/app/marketing/sources/{id}/test-lead``).
    C-5: ``mapping_path`` is Marketing-native (``/app/marketing/sources/{id}/mapping``).
    Settings integrations remain the Connection deep-link.
    """
    _ = (provider, meta_form_id, lead_form_id)  # retained for call-site compatibility
    sid = quote(str(source_id), safe="")
    mapping_path = f"{MARKETING_SOURCES}/{sid}/mapping"
    test_path = f"{MARKETING_SOURCES}/{sid}/test-lead"
    return mapping_path, test_path, SETTINGS_INTEGRATIONS_META


def compute_destination(
    *,
    route_intent: Optional[str],
    lead_target_type: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Simple destination SoT for Sources list (C-3.1) — no parallel registry.

    Returns ``(destination_code, destination_label)``.
    """
    intent = str(route_intent or "").strip().lower()
    target = str(lead_target_type or "").strip().lower()
    if intent == "candidate_application" or target in {"candidate", "vacancy"}:
        return "candidate_application", "Recruitment / Candidate"
    if intent == "sales_inquiry" or target in {"client", "company", "sales"}:
        return "sales_inquiry", "Sales inquiry"
    if intent == "service_request":
        return "service_request", "Service request"
    if intent == "partner_inquiry":
        return "partner_inquiry", "Partner inquiry"
    if intent and intent != "unknown":
        return intent, intent.replace("_", " ").strip().title()
    if target:
        return target, target.replace("_", " ").strip().title()
    return None, None


def build_setup_campaign_flight_path(
    *,
    intake_source_profile_id: str,
    meta_form_id: Optional[str] = None,
    ad_id: Optional[str] = None,
) -> str:
    """Deep-link Marketing setup for operator to configure Campaign/Flight."""
    q: dict[str, str] = {"intake_source_profile_id": str(intake_source_profile_id)}
    if meta_form_id:
        q["meta_form_id"] = str(meta_form_id)
    if ad_id:
        q["ad_id"] = str(ad_id)
    return f"{MARKETING_NEW}?{urlencode(q)}"


def _as_record(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def extract_lead_ad_id(
    *,
    ad_id: Any,
    normalized: Any,
    payload: Any,
) -> Optional[str]:
    if ad_id is not None and str(ad_id).strip():
        return str(ad_id).strip()
    for blob in (_as_record(normalized), _as_record(payload), _as_record(_as_record(payload).get("value"))):
        raw = blob.get("ad_id")
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def extract_lead_form_id(*, normalized: Any, payload: Any) -> Optional[str]:
    for blob in (_as_record(normalized), _as_record(payload), _as_record(_as_record(payload).get("value"))):
        raw = blob.get("form_id")
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


def extract_lead_profile_id(
    *,
    normalized: Any,
    form_id: Optional[str],
    form_id_to_profile: dict[str, str],
) -> Optional[str]:
    stamp = _as_record(_as_record(normalized).get("acquisition_routing_v1"))
    pid = stamp.get("intake_source_profile_id")
    if pid is not None and str(pid).strip():
        return str(pid).strip()
    if form_id and form_id in form_id_to_profile:
        return form_id_to_profile[form_id]
    return None


async def list_marketing_source_summaries(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> list[SourceSummary]:
    tid = str(tenant_id)
    profiles = list(
        (
            await db.execute(
                select(IntakeSourceProfile)
                .where(IntakeSourceProfile.tenant_id == tid)
                .order_by(IntakeSourceProfile.name.asc(), IntakeSourceProfile.code.asc())
            )
        )
        .scalars()
        .all()
    )
    if not profiles:
        return []

    profile_ids = [str(p.id) for p in profiles]

    bindings = list(
        (
            await db.execute(
                select(IntakeSourceBinding).where(
                    IntakeSourceBinding.tenant_id == tid,
                    IntakeSourceBinding.intake_source_profile_id.in_(profile_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    bindings_by_profile: dict[str, list[IntakeSourceBinding]] = {pid: [] for pid in profile_ids}
    for b in bindings:
        bindings_by_profile.setdefault(str(b.intake_source_profile_id), []).append(b)

    link_rows = (
        await db.execute(
            select(
                CampaignRunIntakeSource.intake_source_profile_id,
                CampaignRun.campaign_id,
                CampaignRunIntakeSource.campaign_run_id,
            )
            .join(CampaignRun, CampaignRun.id == CampaignRunIntakeSource.campaign_run_id)
            .join(Campaign, Campaign.id == CampaignRun.campaign_id)
            .where(
                CampaignRunIntakeSource.tenant_id == tid,
                CampaignRunIntakeSource.intake_source_profile_id.in_(profile_ids),
                CampaignRunIntakeSource.is_active.is_(True),
                Campaign.status != "archived",
            )
        )
    ).all()
    campaigns_by_profile: dict[str, set[str]] = {pid: set() for pid in profile_ids}
    flights_by_profile: dict[str, set[str]] = {pid: set() for pid in profile_ids}
    for profile_id, campaign_id, flight_id in link_rows:
        pid = str(profile_id)
        campaigns_by_profile.setdefault(pid, set()).add(str(campaign_id))
        flights_by_profile.setdefault(pid, set()).add(str(flight_id))

    meta_settings = (
        await db.execute(select(MetaLeadSettings).where(MetaLeadSettings.tenant_id == tid))
    ).scalar_one_or_none()
    has_meta_credential = (
        await db.execute(
            select(func.count())
            .select_from(MetaLeadCredential)
            .where(MetaLeadCredential.tenant_id == tid)
        )
    ).scalar_one()
    has_meta_credential_bool = int(has_meta_credential or 0) > 0

    # Meta form mappings keyed by form_id
    meta_maps = list(
        (
            await db.execute(select(MetaLeadFormMapping).where(MetaLeadFormMapping.tenant_id == tid))
        )
        .scalars()
        .all()
    )
    meta_map_by_form = {str(m.form_id): m for m in meta_maps}

    # HostFlow lead forms by public_slug → (id, title) for public_intake profiles
    lead_forms = list(
        (
            await db.execute(
                select(TenantLeadForm.id, TenantLeadForm.public_slug, TenantLeadForm.title).where(
                    TenantLeadForm.tenant_id == tid,
                    TenantLeadForm.public_slug.is_not(None),
                )
            )
        ).all()
    )
    lead_form_by_slug: dict[str, str] = {}
    lead_form_name_by_slug: dict[str, str] = {}
    for fid, slug, ftitle in lead_forms:
        if not slug or not str(slug).strip():
            continue
        key = str(slug).strip()
        lead_form_by_slug[key] = str(fid)
        if ftitle and str(ftitle).strip():
            lead_form_name_by_slug[key] = str(ftitle).strip()

    # Activity: latest submission / error per intake_source endpoint
    endpoint_ids = [intake_source_endpoint_id(pid) for pid in profile_ids]
    activity_rows = (
        await db.execute(
            select(
                AcquisitionActivityEvent.endpoint_id,
                AcquisitionActivityEvent.event_type,
                AcquisitionActivityEvent.occurred_at,
                AcquisitionActivityEvent.payload,
            )
            .where(
                AcquisitionActivityEvent.tenant_id == tid,
                AcquisitionActivityEvent.endpoint_id.in_(endpoint_ids),
                AcquisitionActivityEvent.event_type.in_(
                    list(_SUBMISSION_EVENT_TYPES | _ERROR_EVENT_TYPES)
                ),
            )
            .order_by(AcquisitionActivityEvent.occurred_at.desc())
        )
    ).all()

    last_sub_at: dict[str, datetime] = {}
    last_err_at: dict[str, datetime] = {}
    last_err_code: dict[str, str] = {}
    for endpoint_id, event_type, occurred_at, payload in activity_rows:
        if not endpoint_id or not occurred_at:
            continue
        # endpoint_id = intake_source:{uuid}
        parts = str(endpoint_id).split(":", 1)
        if len(parts) != 2 or parts[0] != "intake_source":
            continue
        pid = parts[1]
        et = str(event_type)
        if et in _SUBMISSION_EVENT_TYPES and pid not in last_sub_at:
            last_sub_at[pid] = occurred_at
        if et in _ERROR_EVENT_TYPES and pid not in last_err_at:
            last_err_at[pid] = occurred_at
            code = None
            if isinstance(payload, dict):
                code = (
                    payload.get("error_code")
                    or payload.get("reason_code")
                    or payload.get("code")
                    or payload.get("reason")
                )
            last_err_code[pid] = str(code or et)

    # Fallback last submission from MetaLeadFormMapping.last_sample_lead_id
    sample_lead_ids = [
        str(m.last_sample_lead_id) for m in meta_maps if m.last_sample_lead_id
    ]
    lead_created: dict[str, datetime] = {}
    lead_errors: dict[str, tuple[datetime, str]] = {}
    if sample_lead_ids:
        lead_rows = (
            await db.execute(
                select(Lead.id, Lead.created_at, Lead.error, Lead.status).where(
                    Lead.tenant_id == tid,
                    Lead.id.in_(sample_lead_ids),
                )
            )
        ).all()
        for lid, created_at, error, status in lead_rows:
            if created_at:
                lead_created[str(lid)] = created_at
            if error and created_at:
                lead_errors[str(lid)] = (created_at, str(error)[:120])
            elif status == "error" and created_at:
                lead_errors[str(lid)] = (created_at, "lead_error")

    # Waiting submissions (needs_routing): visibility only — runtime stop of profile_default = next PR.
    form_id_to_profile: dict[str, str] = {}
    for b in bindings:
        if not bool(b.is_active):
            continue
        pid_b = str(b.intake_source_profile_id)
        fid = parse_meta_form_id(b.external_key)
        if fid:
            form_id_to_profile.setdefault(fid, pid_b)
            continue
        key = str(b.external_key or "").strip()
        if key.startswith("lead_form_id:"):
            lf = key.split(":", 1)[1].strip()
            if lf:
                form_id_to_profile.setdefault(lf, pid_b)

    waiting_count: dict[str, int] = {pid: 0 for pid in profile_ids}
    waiting_last_at: dict[str, datetime] = {}
    # profile_id -> (created_at, ad_id) for most recent waiting lead that has an Ad ID
    last_problem_ad: dict[str, tuple[datetime, str]] = {}

    waiting_rows = (
        await db.execute(
            select(
                Lead.ad_id,
                Lead.created_at,
                Lead.normalized,
                Lead.payload,
            )
            .where(
                Lead.tenant_id == tid,
                Lead.status.in_(list(_WAITING_LEAD_STATUSES)),
            )
            .order_by(Lead.created_at.desc())
            .limit(_WAITING_LEADS_CAP)
        )
    ).all()
    for ad_id_raw, created_at, normalized, payload in waiting_rows:
        form_id = extract_lead_form_id(normalized=normalized, payload=payload)
        pid = extract_lead_profile_id(
            normalized=normalized,
            form_id=form_id,
            form_id_to_profile=form_id_to_profile,
        )
        if not pid or pid not in waiting_count:
            continue
        waiting_count[pid] += 1
        if created_at is not None:
            prev_at = waiting_last_at.get(pid)
            if prev_at is None or created_at > prev_at:
                waiting_last_at[pid] = created_at
        ad_id = extract_lead_ad_id(ad_id=ad_id_raw, normalized=normalized, payload=payload)
        if ad_id and created_at is not None:
            prev = last_problem_ad.get(pid)
            if prev is None or created_at > prev[0]:
                last_problem_ad[pid] = (created_at, ad_id)

    summaries: list[SourceSummary] = []
    for profile in profiles:
        pid = str(profile.id)
        provider = str(profile.provider or "unknown")
        profile_bindings = bindings_by_profile.get(pid, [])
        active_bindings = [b for b in profile_bindings if bool(b.is_active)]
        active_binding_count = len(active_bindings)

        meta_form_id: Optional[str] = None
        for b in active_bindings or profile_bindings:
            if str(b.provider).lower() == "meta" or provider.lower() == "meta":
                meta_form_id = parse_meta_form_id(b.external_key)
                if meta_form_id:
                    break
        if not meta_form_id and provider.lower() == "meta":
            # code meta-form-{fid}
            code = str(profile.code or "")
            if code.startswith("meta-form-"):
                meta_form_id = code[len("meta-form-") :] or None

        meta_form_rules_count = 0
        sample_lead_id = None
        if meta_form_id and meta_form_id in meta_map_by_form:
            mm = meta_map_by_form[meta_form_id]
            rules = mm.mapping_rules if isinstance(mm.mapping_rules, list) else []
            meta_form_rules_count = len(rules)
            sample_lead_id = str(mm.last_sample_lead_id) if mm.last_sample_lead_id else None

        profile_rules = profile.mapping_rules if isinstance(profile.mapping_rules, list) else []
        profile_rules_count = len(profile_rules)
        # Prefer profile rules, else per-form Meta mapping. Tenant-only fallback ≠ configured.
        mapping_rules_count = profile_rules_count or meta_form_rules_count

        lead_form_id = None
        slug = str(profile.public_slug or "").strip()
        if slug and slug in lead_form_by_slug:
            lead_form_id = lead_form_by_slug[slug]

        connection_status = compute_connection_status(
            is_active=bool(profile.is_active),
            provider=provider,
            active_binding_count=active_binding_count,
            last_signature_status=getattr(meta_settings, "last_signature_status", None)
            if provider.lower() == "meta"
            else None,
            has_meta_credential=has_meta_credential_bool if provider.lower() == "meta" else True,
        )

        last_submission = last_sub_at.get(pid)
        if last_submission is None and sample_lead_id and sample_lead_id in lead_created:
            last_submission = lead_created[sample_lead_id]
        wait_at = waiting_last_at.get(pid)
        if wait_at is not None and (last_submission is None or wait_at > last_submission):
            last_submission = wait_at

        last_error = last_err_at.get(pid)
        error_code = last_err_code.get(pid)
        if last_error is None and sample_lead_id and sample_lead_id in lead_errors:
            last_error, error_code = lead_errors[sample_lead_id]

        mapping_health = compute_mapping_health(
            connection_status=connection_status,
            mapping_rules_count=mapping_rules_count,
            last_error_code=error_code,
        )

        waiting_submissions = int(waiting_count.get(pid, 0))
        problem_ad = last_problem_ad.get(pid)
        last_problematic_ad_id = problem_ad[1] if problem_ad else None
        routing_issue_code: Optional[str] = None
        routing_issue_message: Optional[str] = None
        setup_campaign_flight_path: Optional[str] = None
        if waiting_submissions > 0 and last_problematic_ad_id:
            routing_issue_code = ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT
            routing_issue_message = ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT_MESSAGE
            setup_campaign_flight_path = build_setup_campaign_flight_path(
                intake_source_profile_id=pid,
                meta_form_id=meta_form_id,
                ad_id=last_problematic_ad_id,
            )
            if mapping_health == HEALTH_READY:
                mapping_health = HEALTH_NEEDS_REVIEW
        elif waiting_submissions > 0:
            # Waiting without Ad ID — still surface setup CTA for Meta/source binding.
            routing_issue_code = ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT
            routing_issue_message = ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT_MESSAGE
            setup_campaign_flight_path = build_setup_campaign_flight_path(
                intake_source_profile_id=pid,
                meta_form_id=meta_form_id,
            )
            if mapping_health == HEALTH_READY:
                mapping_health = HEALTH_NEEDS_REVIEW

        mapping_path, test_lead_path, settings_path = build_source_paths(
            source_id=pid,
            provider=provider,
            meta_form_id=meta_form_id,
            lead_form_id=lead_form_id,
        )

        # C-3.1: reuse campaign_source_cards helpers (donor) — avoid circular import at module top.
        from backend.app.acquisition.campaign_source_cards import (
            humanize_meta_profile_name,
            parse_meta_page_id,
        )

        page_id: Optional[str] = None
        for b in active_bindings or profile_bindings:
            page_id = parse_meta_page_id(getattr(b, "external_key_secondary", "") or "")
            if page_id:
                break
        meta_map = meta_map_by_form.get(meta_form_id) if meta_form_id else None
        if not page_id and meta_map is not None:
            page_id = str(meta_map.page_id or "").strip() or None
        page_name: Optional[str] = None  # not persisted without Graph sync (same as cards)

        provider_form: Optional[str] = None
        if meta_map is not None:
            provider_form = str(meta_map.form_name or "").strip() or None
        if not provider_form:
            for b in active_bindings or profile_bindings:
                provider_form = humanize_meta_profile_name(
                    getattr(b, "label", None), form_id=meta_form_id
                )
                if provider_form:
                    break
        if not provider_form and slug and slug in lead_form_name_by_slug:
            provider_form = lead_form_name_by_slug[slug]
        if not provider_form:
            provider_form = humanize_meta_profile_name(profile.name, form_id=meta_form_id)

        destination, destination_label = compute_destination(
            route_intent=str(getattr(profile, "route_intent", None) or ""),
            lead_target_type=str(getattr(profile, "lead_target_type", None) or "") or None,
        )

        display_name = (
            provider_form
            or str(profile.name or "").strip()
            or str(profile.code or "").strip()
            or pid
        )

        summaries.append(
            SourceSummary(
                source_id=pid,
                provider=provider,
                display_name=display_name,
                connection_status=connection_status,
                mapping_health=mapping_health,
                last_submission_at=last_submission,
                last_error_at=last_error,
                last_error_code=error_code,
                campaign_count=len(campaigns_by_profile.get(pid, set())),
                flight_count=len(flights_by_profile.get(pid, set())),
                mapping_path=mapping_path,
                test_lead_path=test_lead_path,
                settings_path=settings_path,
                code=str(profile.code or ""),
                is_active=bool(profile.is_active),
                mapping_rules_count=mapping_rules_count,
                active_binding_count=active_binding_count,
                waiting_submissions=waiting_submissions,
                last_problematic_ad_id=last_problematic_ad_id,
                routing_issue_code=routing_issue_code,
                routing_issue_message=routing_issue_message,
                setup_campaign_flight_path=setup_campaign_flight_path,
                page_id=page_id,
                page_name=page_name,
                provider_form=provider_form,
                destination=destination,
                destination_label=destination_label,
            )
        )

    return summaries


__all__ = [
    "CONNECTION_ATTENTION",
    "CONNECTION_CONNECTED",
    "CONNECTION_DISCONNECTED",
    "HEALTH_BROKEN",
    "HEALTH_NEEDS_REVIEW",
    "HEALTH_READY",
    "ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT",
    "ROUTING_ISSUE_MISSING_CAMPAIGN_FLIGHT_MESSAGE",
    "SourceSummary",
    "build_setup_campaign_flight_path",
    "build_source_paths",
    "compute_connection_status",
    "compute_destination",
    "compute_mapping_health",
    "extract_lead_ad_id",
    "extract_lead_form_id",
    "extract_lead_profile_id",
    "list_marketing_source_summaries",
    "parse_meta_form_id",
    "meta_external_key",
]
