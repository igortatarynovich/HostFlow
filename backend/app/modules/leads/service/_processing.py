"""Lead-processing pipeline core (``process_normalized_lead``).

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
god-module split, step 6/N): the single public entry point that takes a
normalized lead payload and runs the full §2.10 ingest pipeline (settings
load, processing-mode resolution, vacancy routing, fit evaluation,
candidate creation/update, plan-gate enforcement, automation-rules trigger,
audit + event emission, license sync).

Re-exported via ``service/__init__.py`` so external callers
(``app/services/imports/leads.py``, router, scripts, tests) keep using the
historical ``service.process_normalized_lead`` access pattern.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.entity_profile.decision_layer import (
    DecisionInput,
    IngestDecisionContext,
    IngestDisposition,
    evaluate_ingest_decision,
    stamp_decision_blocks,
)
from backend.app.entity_profile.outcome_executor import (
    apply_blocked_duplicate_outcome,
    execute_create_candidate_outcome,
)
from backend.app.models import Candidate, Lead, OwnCompany, Tenant
from backend.app.models.tenant import TenantLicense
from backend.app.models.user import Role
from backend.app.modules.leads import crud, lead_custom_fields
from backend.app.modules.leads.lead_candidate_conversion import ensure_recruitment_application_for_converted_lead
from backend.app.modules.leads.lead_criteria_eval import lead_fit_evaluation_effective
from backend.app.services import billing_restrictions
from backend.app.services.automation_rules import run_rules as run_automation_rules
from backend.app.services.handoff import is_client_tenant
from backend.app.services.lead_lifecycle import apply_lead_terminal_cleanup
from backend.app.services.recruitment_handoff_write_guard import (
    is_recruitment_recruiter_write_locked_by_handoff,
)
from backend.app.services.recruiter_assignment import resolve_vacancy_primary_recruiter

from ._helpers import (
    LeadProcessingError,
    MetaLeadResult,
    _apply_leads_processing_mode_v1_to_normalized,
    _audit_lead_qualification_rule_match,
    _build_lead_outcome,
    _emit_lead_event,
    _load_settings,
    _load_supervisor_id,
    _load_tenant_business_type,
    _pick_lead_assignee_id,
    _rule_recruiter_id_from_normalized,
    _stamp_lead_qualification_preview_v1,
    _triage_bypass_from_vacancy_fallback,
    _vacancy_allows_auto_convert_on_fit,
    _validate_company_id,
    _validate_recruiter_id,
    resolve_vacancy_for_lead_processing,
)
from backend.app.modules.leads.schemas import intake_vacancy_confirm_triage_bypass
from backend.app.modules.leads.service.intake_decision import pool_intake_manual_convert_ready
from backend.app.modules.leads.intake_route import (
    is_sales_route_intent,
    lead_type_for_route_intent,
    lead_type_for_target,
    resolve_intake_route_for_ingest,
)
from backend.app.modules.outcome_rules.reference import OutcomeEvent, OutcomeRuleType
from backend.app.services.outcome_resolver import resolve_outcomes

_ingest_guard_log = logging.getLogger(__name__)


async def _agency_recruitment_lock_context_for_ingest(
    db: AsyncSession,
    *,
    agency_tenant_id: str,
    candidate_id: str,
) -> tuple[bool, Optional[str]]:
    """Return (locked, lock_reason) when ingest must not mutate an existing Candidate row."""
    if await is_client_tenant(db, agency_tenant_id):
        return False, None
    locked, reason = await is_recruitment_recruiter_write_locked_by_handoff(
        db, agency_tenant_id=agency_tenant_id, candidate_id=str(candidate_id)
    )
    if not locked:
        return False, None
    return True, (reason or "handoff")


async def process_normalized_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    payload: Dict[str, Any],
    normalized: Dict[str, Any],
    source: str,
    external_id: Optional[str] = None,
    on_lead_created: Optional[Callable[[Lead], Awaitable[None]]] = None,
    force_existing: bool = False,
    force_candidate_conversion: bool = False,
    target_lead_id: Optional[str] = None,
) -> MetaLeadResult:
    normalized = dict(normalized or {})
    business_type: Optional[str] = None
    lead_target_type: str = "candidate"
    route_intent: str = "unknown"
    route_default_assignee: Optional[str] = None
    settings_row = await _load_settings(db, tenant_id)
    tenant_entity_for_settings = await db.get(Tenant, tenant_id)
    tenant_settings_for_routing: Dict[str, Any] = {}
    if tenant_entity_for_settings is not None:
        ts = getattr(tenant_entity_for_settings, "settings", None)
        if isinstance(ts, dict):
            tenant_settings_for_routing = ts
    fallback_company_hint = settings_row.default_company_id
    fallback_recruiter_hint = settings_row.fallback_recruiter_id
    auto_create_enabled = bool(settings_row.auto_create_enabled)
    await _apply_leads_processing_mode_v1_to_normalized(
        db,
        tenant_id=tenant_id,
        normalized=normalized,
        settings_row=settings_row,
    )
    effective_processing_mode = str(normalized.get("leads_processing_mode_v1") or "assisted").strip().lower()
    # §2.10: only Automatic + auto_create may create candidates without operator (§2.4 tightens below).
    normalized_external_id: Optional[str] = None
    if external_id is not None:
        text = str(external_id).strip()
        normalized_external_id = text or None

    # Re-processing a known row (bulk/backfill/manual): must win over ``get_lead_by_external_id``,
    # otherwise duplicate Meta ``id`` values attach the pipeline to a different ``Lead`` row.
    lead: Optional[Lead] = None
    if target_lead_id:
        tl = str(target_lead_id).strip()
        row = await db.get(Lead, tl)
        if row is not None and str(row.tenant_id) == str(tenant_id):
            lead = row
    if lead is None and normalized_external_id:
        lead = await crud.get_lead_by_external_id(
            db,
            tenant_id=tenant_id,
            source=source,
            external_id=normalized_external_id,
        )
    created_new = False
    if lead:
        from backend.app.services.lead_communications import normalized_merging_lead_persisted_blocks

        lead.payload = payload
        lead.normalized = normalized_merging_lead_persisted_blocks(lead, normalized)
        lead.ad_id = normalized.get("ad_id")
        # If lead was already processed successfully we normally skip the whole pipeline.
        # However, when a lead is inconsistent (e.g. status=processed but candidate_id is missing)
        # we need to force re-processing.
        #
        # IMPORTANT:
        # - `status="new"` must NOT be treated as "already processed"; otherwise manual `POST /process`
        #   will never attach `candidate_id` nor update lead status.
        if not force_existing and lead.status in {"processed", "duplicated", "rejected"}:
            effective_own_company_id = own_company_id or getattr(lead, "own_company_id", None)
            business_type = await _load_tenant_business_type(db, tenant_id, effective_own_company_id)
            recruiter_id: Optional[str] = None
            candidate_id = lead.candidate_id
            if candidate_id:
                candidate = await db.get(Candidate, candidate_id)
                if candidate:
                    recruiter_id = getattr(candidate, "recruiter_id", None)
                    lead_own_company_id = getattr(lead, "own_company_id", None)
                    candidate_own_company_id = getattr(candidate, "own_company_id", None)
                    ingest_locked, ingest_lock_reason = await _agency_recruitment_lock_context_for_ingest(
                        db, agency_tenant_id=tenant_id, candidate_id=str(candidate_id)
                    )
                    if ingest_locked:
                        _ingest_guard_log.info(
                            "lead_ingest_skipped_candidate_mutation_recruitment_locked",
                            extra={
                                "event": "lead_ingest_skipped_candidate_mutation_recruitment_locked",
                                "operation": "ingest_skip",
                                "candidate_id": str(candidate_id),
                                "lead_id": str(lead.id),
                                "tenant_id": tenant_id,
                                "lock_reason": ingest_lock_reason or "handoff",
                                "source": source,
                                "ingest_skip_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                    if not ingest_locked:
                        # Candidates list is filtered by own_company_id (active OwnCompany in Topbar).
                        # Some lead->candidate flows can create candidates with own_company_id=None
                        # (e.g. when no vacancy was resolved). Fix it here so the candidate is visible.
                        if lead_own_company_id and not candidate_own_company_id:
                            candidate.own_company_id = str(lead_own_company_id)
                            await db.flush()
                        # Phase 2.6.G-5 Stage D — legacy shadow-write of
                        # ``candidate.manager = recruiter_id`` removed; the
                        # canonical writer ``record_candidate_reassignment``
                        # (invoked above in the lead-rule / vacancy / fallback
                        # branches) now mirrors into both columns.
                        # Обновляем extra поля из normalized данных, если они есть
                        extra = candidate._get_extra()
                        updated = False

                        # Обновляем preferred_contact
                        preferred_contact = normalized.get("preferred_contact") or normalized.get("preferred_contact_raw")
                        if isinstance(preferred_contact, str) and preferred_contact.strip():
                            contact_val = preferred_contact.strip()
                            if extra.get("preferred_contact") != contact_val:
                                extra["preferred_contact"] = contact_val
                                updated = True
                            contacts_bucket = extra.get("contacts")
                            if not isinstance(contacts_bucket, dict):
                                contacts_bucket = {}
                                extra["contacts"] = contacts_bucket
                            if contacts_bucket.get("preferred_messenger") != contact_val:
                                contacts_bucket["preferred_messenger"] = contact_val
                                updated = True

                        # Обновляем in_poland
                        in_poland_value = normalized.get("in_poland")
                        if isinstance(in_poland_value, bool):
                            if extra.get("in_poland") != in_poland_value:
                                extra["in_poland"] = in_poland_value
                                updated = True
                        elif isinstance(in_poland_value, str):
                            lowered = in_poland_value.strip().lower()
                            if lowered in {"true", "yes", "1"}:
                                if extra.get("in_poland") is not True:
                                    extra["in_poland"] = True
                                    updated = True
                            elif lowered in {"false", "no", "0"}:
                                if extra.get("in_poland") is not False:
                                    extra["in_poland"] = False
                                    updated = True

                        # Обновляем poland_stay_basis
                        poland_basis = normalized.get("poland_stay_basis") or normalized.get("poland_stay_basis_raw")
                        if isinstance(poland_basis, str) and poland_basis.strip():
                            basis_val = poland_basis.strip()
                            if extra.get("poland_stay_basis") != basis_val:
                                extra["poland_stay_basis"] = basis_val
                                updated = True
                            personal_bucket = extra.get("personal_data")
                            if not isinstance(personal_bucket, dict):
                                personal_bucket = {}
                                extra["personal_data"] = personal_bucket
                            if personal_bucket.get("residency_status") != basis_val:
                                personal_bucket["residency_status"] = basis_val
                                updated = True

                        # Обновляем driving_experience_in_europe
                        driving_experience = normalized.get("driving_experience_in_europe")
                        if isinstance(driving_experience, str) and driving_experience.strip():
                            if extra.get("driving_experience_in_europe") != driving_experience.strip():
                                extra["driving_experience_in_europe"] = driving_experience.strip()
                                updated = True

                        # Обновляем experience_eu_years (опыт по ЕС)
                        experience_eu_years = normalized.get("experience_eu_years")
                        if isinstance(experience_eu_years, int) and experience_eu_years >= 0:
                            if extra.get("experience_eu_years") != experience_eu_years:
                                extra["experience_eu_years"] = experience_eu_years
                                updated = True

                        if updated:
                            candidate.extra = json.dumps(extra, ensure_ascii=False, separators=(",", ":"))
                            await db.flush()
            outcome_entity_type, outcome_entity_id, outcome_entity_name = _build_lead_outcome(
                business_type=business_type,
                company_id=lead.company_id,
                company_name=None,
                candidate_id=candidate_id,
                candidate_name=None,
            )

            await lead_custom_fields.sync_lead_custom_fields_from_normalized(
                db,
                tenant_id=tenant_id,
                lead_id=str(lead.id),
                normalized=normalized,
            )
            await db.flush()

            return MetaLeadResult(
                lead_id=lead.id,
                status=lead.status,
                vacancy_id=lead.vacancy_id,
                candidate_id=candidate_id,
                recruiter_id=recruiter_id,
                business_type=business_type,
                outcome_entity_type=outcome_entity_type,
                outcome_entity_id=outcome_entity_id,
                outcome_entity_name=outcome_entity_name,
                error=lead.error,
                is_new=False,
            )

    intake_ctx = await resolve_intake_route_for_ingest(
        db,
        tenant_id=tenant_id,
        source=source,
        normalized=normalized,
        payload=payload,
        own_company_id_hint=str(own_company_id or "").strip() or None,
    )
    route_intent = intake_ctx.route_intent
    lead_target_type = intake_ctx.lead_target_type
    route_default_assignee = intake_ctx.default_assignee_id
    outcome_resolution = resolve_outcomes(route_intent, OutcomeEvent.ingest.value)
    outcome_actions = tuple(action.code for action in outcome_resolution.actions)
    creates_candidate = bool(
        force_candidate_conversion or OutcomeRuleType.create_candidate.value in outcome_actions
    )
    sales_lead_without_candidate = is_sales_route_intent(route_intent) and not creates_candidate
    normalized["intake_routing_v1"] = intake_ctx.to_intake_routing_v1()
    normalized["intake_route_v1"] = intake_ctx.to_normalized_block()
    normalized["outcome_resolution_v1"] = outcome_resolution.to_dict()
    if intake_ctx.pipeline_preset:
        normalized["intake_pipeline_preset_v1"] = intake_ctx.pipeline_preset
    if intake_ctx.own_company_id:
        own_company_id = intake_ctx.own_company_id

    req_oc = str(own_company_id or "").strip() or None
    lead_oc = (
        str(getattr(lead, "own_company_id", None) or "").strip() or None
        if lead is not None
        else None
    )
    scope_for_vacancy_routing = req_oc or lead_oc
    vacancy, routing_fit_status, routing_fit_reasons = await resolve_vacancy_for_lead_processing(
        db,
        tenant_id=tenant_id,
        normalized=normalized,
        tenant_settings=tenant_settings_for_routing,
        source=source,
        own_company_id=scope_for_vacancy_routing,
    )
    vacancy_for_confirm = vacancy
    pool_manual_convert_ready = False
    if lead is not None:
        pool_manual_convert_ready = pool_intake_manual_convert_ready(lead, normalized)
    if pool_manual_convert_ready:
        vacancy = None
    if sales_lead_without_candidate:
        vacancy = None
        vacancy_for_confirm = None

    triage_gate_bypass = bool(
        force_candidate_conversion
        or _triage_bypass_from_vacancy_fallback(normalized)
        or intake_vacancy_confirm_triage_bypass(normalized, vacancy_for_confirm)
    )

    tenant_autoconv = bool(getattr(settings_row, "leads_auto_convert_on_fit_v1", True))
    fit_evaluation_effective = lead_fit_evaluation_effective(getattr(vacancy, "extra", None) if vacancy else None)
    normalized["lead_fit_evaluation_effective_v1"] = bool(fit_evaluation_effective)
    # Mapping-only path: lead fit off (or legacy empty criteria) → do not gate on leads_auto_convert_on_fit_v1.
    # Fit-on path: require tenant_autoconv (and vacancy opt-out) for automatic conversion.
    may_auto_convert = (
        bool(auto_create_enabled)
        and effective_processing_mode == "automatic"
        and _vacancy_allows_auto_convert_on_fit(vacancy)
        and (not fit_evaluation_effective or tenant_autoconv)
        and creates_candidate
    )
    normalized["leads_auto_convert_on_fit_effective_v1"] = bool(may_auto_convert)

    resolved_company_id: Optional[str] = None
    if vacancy:
        resolved_company_id = vacancy.company_id
        normalized["resolved_vacancy_id"] = vacancy.id
    else:
        normalized["resolved_vacancy_id"] = None

    hinted_company_id = normalized.get("company_id")
    if hinted_company_id and not resolved_company_id:
        resolved_company_id = await _validate_company_id(db, tenant_id, hinted_company_id)

    company_name_hint = normalized.get("company_name_hint")
    company_hints: List[str] = []

    def _add_company_hint(value: Any) -> None:
        if not value:
            return
        text = str(value).strip()
        if not text:
            return
        if text not in company_hints:
            company_hints.append(text)

    _add_company_hint(company_name_hint)
    raw_company_hints = normalized.get("company_hints")
    if isinstance(raw_company_hints, list):
        for item in raw_company_hints:
            _add_company_hint(item)

    if not resolved_company_id and company_hints:
        for hint in company_hints:
            resolved = await crud.resolve_company_by_name(db, tenant_id, hint)
            if resolved:
                resolved_company_id = resolved
                break

    if not resolved_company_id and not sales_lead_without_candidate:
        resolved_company_id = await _validate_company_id(db, tenant_id, fallback_company_hint)

    if not resolved_company_id and not sales_lead_without_candidate:
        resolved_company_id = await crud.get_default_company_id(db, tenant_id)

    if not resolved_company_id and not sales_lead_without_candidate:
        raise LeadProcessingError("needs_routing", "COMPANY_NOT_RESOLVED")

    if resolved_company_id:
        normalized["resolved_company_id"] = resolved_company_id
    resolved_company_name = next((hint for hint in company_hints if hint), None)

    if lead is None:
        tenant_row = await db.get(Tenant, tenant_id)
        lic_row = (
            await db.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
        ).scalar_one_or_none()
        if tenant_row and billing_restrictions.tenant_billing_blocks_new_leads(tenant_row, lic_row):
            reason = billing_restrictions.billing_write_block_reason(tenant_row, lic_row)
            code = "BILLING_TRIAL_EXPIRED" if reason == "trial_expired" else "BILLING_PAST_DUE"
            raise LeadProcessingError("billing_blocked", code)
        # Always prefer the active OwnCompany (Topbar) so that:
        # - lead.own_company_id matches current scope
        # - candidates/clients remain visible in the UI after conversion
        own_company_id_for_lead = own_company_id
        if intake_ctx.own_company_id:
            own_company_id_for_lead = intake_ctx.own_company_id
        if not own_company_id_for_lead:
            own_company_id_for_lead = getattr(vacancy, "own_company_id", None) if vacancy else None
        if not own_company_id_for_lead:
            row = await db.execute(
                select(OwnCompany.id)
                .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
                .order_by(OwnCompany.created_at.asc())
                .limit(1)
            )
            own_company_id_for_lead = row.scalar_one_or_none()
        if not own_company_id_for_lead:
            raise LeadProcessingError("needs_routing", "OWN_COMPANY_REQUIRED")
        lead = await crud.create_lead(
            db,
            tenant_id=tenant_id,
            own_company_id=str(own_company_id_for_lead),
            company_id=None if sales_lead_without_candidate else resolved_company_id,
            vacancy_id=None if sales_lead_without_candidate else (vacancy.id if vacancy else None),
            payload=payload,
            normalized=normalized,
            ad_id=normalized.get("ad_id"),
            source=source,
            external_id=normalized_external_id,
            lead_type=lead_type_for_route_intent(route_intent),
            lead_target_type=lead_target_type,
        )
        created_new = True
        if on_lead_created is not None:
            try:
                await on_lead_created(lead)
            except Exception:  # pragma: no cover - best effort
                pass
    else:
        old_company_id = getattr(lead, "company_id", None)
        lead.company_id = None if sales_lead_without_candidate else resolved_company_id
        lead.vacancy_id = None if sales_lead_without_candidate else (vacancy.id if vacancy else None)
        if getattr(lead, "own_company_id", None) in (None, ""):
            # Prefer intake route / active OwnCompany; otherwise fall back to vacancy.
            lead.own_company_id = (
                intake_ctx.own_company_id
                if intake_ctx.own_company_id
                else (own_company_id or (getattr(vacancy, "own_company_id", None) if vacancy else None))
            )
        if intake_ctx.matched:
            lead.lead_target_type = lead_target_type
            lead.lead_type = lead_type_for_target(lead_target_type)
            if intake_ctx.own_company_id:
                lead.own_company_id = intake_ctx.own_company_id
        elif getattr(lead, "lead_target_type", None) in (None, ""):
            lead.lead_target_type = lead_target_type
            if lead_type_for_target(lead_target_type) != str(getattr(lead, "lead_type", "") or "candidate"):
                lead.lead_type = lead_type_for_target(lead_target_type)
        elif lead_type_for_target(lead_target_type) != str(getattr(lead, "lead_type", "") or "candidate"):
            lead.lead_type = lead_type_for_target(lead_target_type)
        lead.payload = payload
        from backend.app.services.lead_communications import normalized_merging_lead_persisted_blocks

        lead.normalized = normalized_merging_lead_persisted_blocks(lead, normalized)
        lead.ad_id = normalized.get("ad_id")
        await db.flush()
        from backend.app.services.recruitment_funnel_assignment import (
            reconcile_lead_funnel_on_company_change,
        )

        await reconcile_lead_funnel_on_company_change(
            db,
            tenant_id=tenant_id,
            lead=lead,
            old_company_id=old_company_id,
            new_company_id=lead.company_id,
        )

    await lead_custom_fields.sync_lead_custom_fields_from_normalized(
        db,
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        normalized=normalized,
    )
    await db.flush()

    if created_new:
        from backend.app.services.lead_rodo_auto import apply_lead_rodo_on_ingest

        await apply_lead_rodo_on_ingest(
            db,
            tenant_id=tenant_id,
            lead=lead,
            source=source,
            normalized=lead.normalized if isinstance(lead.normalized, dict) else normalized,
            is_new_lead=True,
        )
        await db.flush()

    # At this point `lead.own_company_id` is known (from vacancy or OwnCompany fallback),
    # so we can determine the scenario using OwnCompany settings.
    effective_own_company_id = own_company_id or getattr(lead, "own_company_id", None)
    business_type = await _load_tenant_business_type(db, tenant_id, effective_own_company_id)

    if intake_ctx.failed and not force_candidate_conversion:
        failed_error = (
            str(intake_ctx.warnings[0]).upper()
            if intake_ctx.warnings
            else "INTAKE_ROUTING_FAILED"
        )
        failed_lead_id = str(lead.id)
        now_marker = datetime.now(timezone.utc)
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=failed_error,
            last_routed_at=now_marker,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.needs_routing",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=failed_error,
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=failed_lead_id,
            normalized=normalized,
        )
        await db.flush()
        await db.commit()
        return MetaLeadResult(
            lead_id=failed_lead_id,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=failed_error,
            is_new=created_new,
        )

    email = normalized.get("email")
    phone = normalized.get("phone")
    if not email and not phone:
        fields = normalized.get("raw_field_names") or []
        graph_error = normalized.get("graph_error")
        diagnostic_base = graph_error or "NO_CONTACTS"
        if fields:
            suffix = f"(fields={'/'.join(fields)})"
            diagnostic = f"{diagnostic_base} {suffix}"
        else:
            diagnostic = diagnostic_base
        await crud.update_lead(
            db,
            lead,
            status="failed",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=diagnostic,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.failed",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=diagnostic,
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="failed",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=diagnostic,
            is_new=created_new,
        )

    if created_new:
        from backend.app.services.lead_communications import maybe_send_application_received_on_ingest

        await maybe_send_application_received_on_ingest(
            db,
            tenant_id=tenant_id,
            lead=lead,
            is_new_lead=True,
            pipeline_normalized=normalized,
        )
        await db.flush()

    decision_input = DecisionInput.from_normalized(
        tenant_id=tenant_id,
        source=source,
        normalized=normalized,
        force_candidate_conversion=force_candidate_conversion,
        vacancy_id=str(vacancy.id) if vacancy else None,
        company_id=resolved_company_id,
    )
    decision_ctx = IngestDecisionContext(
        effective_processing_mode=effective_processing_mode,
        auto_create_enabled=bool(auto_create_enabled),
        may_auto_convert=bool(may_auto_convert),
        triage_gate_bypass=bool(triage_gate_bypass),
        pool_manual_convert_ready=bool(pool_manual_convert_ready),
        routing_fit_status=str(routing_fit_status or "unknown"),
        sales_lead_without_candidate=bool(sales_lead_without_candidate),
        vacancy_resolved=vacancy is not None,
    )
    ingest_decision = await evaluate_ingest_decision(
        db,
        decision_input,
        ctx=decision_ctx,
        email=email,
        phone=phone,
    )
    stamp_decision_blocks(normalized, decision_input, ingest_decision)
    creates_candidate = bool(ingest_decision.may_create_candidate)

    if ingest_decision.disposition == IngestDisposition.blocked_duplicate.value:
        duplicate = ingest_decision.duplicate_match.candidate
        dup_id = await apply_blocked_duplicate_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized=normalized,
            decision=ingest_decision,
            resolved_company_id=resolved_company_id,
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        return MetaLeadResult(
            lead_id=lead.id,
            status="duplicated",
            vacancy_id=lead.vacancy_id or (getattr(duplicate, "vacancy_id", None) if duplicate else None),
            candidate_id=dup_id,
            recruiter_id=getattr(duplicate, "recruiter_id", None) if duplicate else None,
            business_type=business_type,
            outcome_entity_type="company" if is_sales_route_intent(route_intent) else "candidate",
            outcome_entity_id=resolved_company_id if is_sales_route_intent(route_intent) else dup_id,
            outcome_entity_name=resolved_company_name if is_sales_route_intent(route_intent) else None,
            error=None,
            is_new=created_new,
        )

    if ingest_decision.disposition == IngestDisposition.review_queue.value:
        review_error = "DUPLICATE_REVIEW_PENDING"
        now_marker = datetime.now(timezone.utc)
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=review_error,
            last_routed_at=now_marker,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.needs_routing",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=review_error,
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=review_error,
            is_new=created_new,
        )

    if (
        not triage_gate_bypass
        and may_auto_convert
        and creates_candidate
        and vacancy is not None
        and routing_fit_status in ("no_fit", "needs_info")
    ):
        err_code = "LEAD_FIT_NO_MATCH" if routing_fit_status == "no_fit" else "LEAD_FIT_NEEDS_INFO"
        _stamp_lead_qualification_preview_v1(
            normalized,
            vacancy=vacancy,
            fit_status=routing_fit_status,
            fit_reasons=list(routing_fit_reasons or []),
            blocked_auto_convert=True,
        )
        now_marker = datetime.now(timezone.utc)
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=err_code,
            last_routed_at=now_marker,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.needs_routing",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
        await _audit_lead_qualification_rule_match(
            db, tenant_id=tenant_id, lead_id=str(lead.id), normalized=normalized
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=err_code,
            is_new=created_new,
        )

    if not triage_gate_bypass and not may_auto_convert and not pool_manual_convert_ready:
        if creates_candidate:
            if effective_processing_mode == "assisted":
                _stamp_lead_qualification_preview_v1(
                    normalized,
                    vacancy=vacancy,
                    fit_status=routing_fit_status,
                    fit_reasons=list(routing_fit_reasons or []),
                    blocked_auto_convert=False,
                )
            elif effective_processing_mode == "automatic" and bool(auto_create_enabled):
                _stamp_lead_qualification_preview_v1(
                    normalized,
                    vacancy=vacancy,
                    fit_status=routing_fit_status,
                    fit_reasons=list(routing_fit_reasons or []),
                    blocked_auto_convert=True,
                )
        now_marker = datetime.now(timezone.utc)
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=None,
            last_routed_at=now_marker,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.needs_routing",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
        await _audit_lead_qualification_rule_match(
            db, tenant_id=tenant_id, lead_id=str(lead.id), normalized=normalized
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=None,
            is_new=created_new,
        )

    # --- Sales intake: lead stays in pipeline (no candidate creation) ---
    if is_sales_route_intent(route_intent) and not force_candidate_conversion:
        # After commits SQLAlchemy may expire ORM instances, so avoid accessing `lead.*`
        # after `await db.commit()` by capturing values upfront.
        services_lead_id = str(lead.id)
        services_lead_source = lead.source
        services_lead_vacancy_id = lead.vacancy_id
        await crud.update_lead(
            db,
            lead,
            status="processed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=None,
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.processed",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
        )
        if created_new:
            await _emit_lead_event(
                db,
                tenant_id=tenant_id,
                lead=lead,
                event_type="lead.new.telegram",
                roles=[Role.administrator, Role.supervisor],
                business_type=business_type,
                outcome_entity_type="company",
                outcome_entity_id=resolved_company_id,
                outcome_entity_name=resolved_company_name,
            )
        # Important: commit lead status update before running automation rules.
        # Automation failures previously caused `db.rollback()` to undo the lead update,
        # leaving the UI with stale status/error even though processing returned success.
        await _audit_lead_qualification_rule_match(
            db, tenant_id=tenant_id, lead_id=services_lead_id, normalized=normalized
        )
        await db.commit()
        # Minimal rules builder (R2.2): trigger lead.processed automation rules
        try:
            assignee_id = await _pick_lead_assignee_id(
                db,
                tenant_id=tenant_id,
                preferred_user_id=route_default_assignee or fallback_recruiter_hint,
                normalized=normalized,
                lead_id=str(services_lead_id),
            )
            rule_ctx_extras = await lead_custom_fields.automation_context_for_lead(
                db,
                tenant_id=tenant_id,
                lead_id=services_lead_id,
                normalized=normalized if isinstance(normalized, dict) else {},
            )
            await run_automation_rules(
                db,
                tenant_id=tenant_id,
                trigger="lead.processed",
                actor_id=assignee_id,
                context={
                    "entity_type": "lead",
                    "entity_id": services_lead_id,
                    "lead_id": services_lead_id,
                    "source": services_lead_source,
                    "status": "processed",
                    "business_type": business_type,
                    "company_id": resolved_company_id,
                    "vacancy_id": services_lead_vacancy_id,
                    "assignee_id": assignee_id,
                    **rule_ctx_extras,
                },
            )
            await db.commit()
        except Exception:
            await db.rollback()
        await db.commit()
        return MetaLeadResult(
            lead_id=services_lead_id,
            status="processed",
            vacancy_id=services_lead_vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=None,
            is_new=created_new,
        )

    if not vacancy and not pool_manual_convert_ready and creates_candidate:
        needs_routing_lead_id = str(lead.id)
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=None,
            normalized=normalized,
            error="VACANCY_NOT_RESOLVED",
            last_routed_at=datetime.now(timezone.utc),
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.needs_routing",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error="VACANCY_NOT_RESOLVED",
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=needs_routing_lead_id,
            normalized=normalized,
        )
        await db.flush()
        await _audit_lead_qualification_rule_match(
            db, tenant_id=tenant_id, lead_id=needs_routing_lead_id, normalized=normalized
        )
        await db.commit()
        return MetaLeadResult(
            lead_id=needs_routing_lead_id,
            status="needs_routing",
            vacancy_id=None,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error="VACANCY_NOT_RESOLVED",
            is_new=created_new,
        )

    if ingest_decision.disposition != IngestDisposition.create_candidate.value:
        now_marker = datetime.now(timezone.utc)
        await crud.update_lead(
            db,
            lead,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=None,
            last_routed_at=now_marker,
        )
        await _emit_lead_event(
            db,
            tenant_id=tenant_id,
            lead=lead,
            event_type="lead.needs_routing",
            roles=[Role.administrator, Role.supervisor],
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
        )
        await lead_custom_fields.sync_lead_custom_fields_from_normalized(
            db,
            tenant_id=tenant_id,
            lead_id=str(lead.id),
            normalized=normalized,
        )
        await db.flush()
        await db.commit()
        return MetaLeadResult(
            lead_id=lead.id,
            status="needs_routing",
            vacancy_id=lead.vacancy_id,
            candidate_id=None,
            recruiter_id=None,
            business_type=business_type,
            outcome_entity_type="company",
            outcome_entity_id=resolved_company_id,
            outcome_entity_name=resolved_company_name,
            error=None,
            is_new=created_new,
        )

    first_name = normalized.get("first_name") or "Meta"
    last_name = normalized.get("last_name") or normalized.get("full_name") or "Lead"
    if not last_name.strip():
        last_name = "Lead"

    extra_fields: Dict[str, Any] = {}
    personal_fields: Dict[str, Any] = {}
    preferred_contact = normalized.get("preferred_contact") or normalized.get("preferred_contact_raw")
    if isinstance(preferred_contact, str) and preferred_contact.strip():
        extra_fields["preferred_contact"] = preferred_contact.strip()
    in_poland_value = normalized.get("in_poland")
    if isinstance(in_poland_value, bool):
        extra_fields["in_poland"] = in_poland_value
        personal_fields["in_poland"] = in_poland_value
    elif isinstance(in_poland_value, str):
        lowered = in_poland_value.strip().lower()
        if lowered in {"true", "yes", "1"}:
            extra_fields["in_poland"] = True
            personal_fields["in_poland"] = True
        elif lowered in {"false", "no", "0"}:
            extra_fields["in_poland"] = False
            personal_fields["in_poland"] = False
    poland_basis = normalized.get("poland_stay_basis") or normalized.get("poland_stay_basis_raw")
    if isinstance(poland_basis, str) and poland_basis.strip():
        extra_fields["poland_stay_basis"] = poland_basis.strip()
        personal_fields["residency_status"] = poland_basis.strip()
    # Handle driving experience - save both raw string and normalized number
    driving_experience = normalized.get("driving_experience_in_europe")
    if isinstance(driving_experience, str) and driving_experience.strip():
        extra_fields["driving_experience_in_europe"] = driving_experience.strip()
    # Also save normalized number of years if available (опыт по ЕС)
    experience_eu_years = normalized.get("experience_eu_years")
    if isinstance(experience_eu_years, int) and experience_eu_years >= 0:
        extra_fields["experience_eu_years"] = experience_eu_years

    from backend.app.services.lead_rodo import rodo_lead_audit_for_candidate_extra

    rodo_audit = rodo_lead_audit_for_candidate_extra(
        normalized if isinstance(normalized, dict) else {},
        str(lead.id),
    )
    if rodo_audit:
        extra_fields["rodo_lead_audit"] = rodo_audit

    candidate_payload: Dict[str, Any] = {
        "first_name": first_name.strip() or "Meta",
        "last_name": last_name.strip() or "Lead",
        "email": email,
        "phone": phone,
        "phone_country_code": normalized.get("phone_country_code"),
        "own_company_id": getattr(lead, "own_company_id", None),
        "company_id": resolved_company_id,
        "vacancy_id": vacancy.id if vacancy else None,
        "contacts": {
            key: value
            for key, value in {
                "email": email,
                "phone": phone,
                "phone_country_code": normalized.get("phone_country_code"),
                "preferred_messenger": extra_fields.get("preferred_contact"),
            }.items()
            if value
        },
        "source": source,
        "origin": {source: normalized},
    }
    if personal_fields:
        candidate_payload["personal_data"] = personal_fields
    if extra_fields:
        candidate_payload["extra"] = extra_fields

    had_candidate_before = bool(getattr(lead, "candidate_id", None))
    stamp_rid = _rule_recruiter_id_from_normalized(normalized)
    vacancy_recruiter_id = (
        await resolve_vacancy_primary_recruiter(db, tenant_id, vacancy)
        if vacancy
        else None
    )
    fallback_recruiter = await _validate_recruiter_id(db, tenant_id, fallback_recruiter_hint)

    try:
        candidate = await execute_create_candidate_outcome(
            db,
            tenant_id=tenant_id,
            lead=lead,
            normalized=normalized,
            source=source,
            candidate_payload=candidate_payload,
            decision=ingest_decision,
            rule_recruiter_id=stamp_rid,
            vacancy_recruiter_id=vacancy_recruiter_id,
            fallback_recruiter_id=fallback_recruiter,
        )
    except HTTPException as exc:
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=str(exc.detail),
        )
        await db.commit()
        raise
    except Exception as exc:  # pragma: no cover - defensive
        await crud.update_lead(
            db,
            lead,
            status="failed",
            candidate_id=None,
            vacancy_id=lead.vacancy_id,
            normalized=normalized,
            error=str(exc),
        )
        await db.commit()
        raise

    recruiter_id = getattr(candidate, "recruiter_id", None)

    await crud.update_lead(
        db,
        lead,
        status="processed",
        candidate_id=str(candidate.id),
        vacancy_id=candidate.vacancy_id,
        normalized=normalized,
        error=None,
    )
    await lead_custom_fields.sync_lead_custom_fields_from_normalized(
        db,
        tenant_id=tenant_id,
        lead_id=str(lead.id),
        normalized=normalized,
    )
    await db.flush()

    if not had_candidate_before:
        from backend.app.services.lead_communications import maybe_send_moving_forward_notice

        await maybe_send_moving_forward_notice(db, tenant_id=tenant_id, lead=lead)
        await db.flush()

    await ensure_recruitment_application_for_converted_lead(
        db,
        tenant_id=tenant_id,
        lead=lead,
        candidate=candidate,
        vacancy_id=str(vacancy.id) if vacancy else None,
        recruiter_id=recruiter_id,
        source=str(source),
    )
    await db.flush()

    # Commit lead status update before automation to avoid losing it on rollback.
    agency_lead_id = str(lead.id)
    await _audit_lead_qualification_rule_match(
        db, tenant_id=tenant_id, lead_id=agency_lead_id, normalized=normalized
    )
    await db.commit()
    try:
        await apply_lead_terminal_cleanup(
            db,
            tenant_id=tenant_id,
            lead_id=agency_lead_id,
            new_stage=getattr(lead, "stage", None),
            new_status=getattr(lead, "status", None),
            actor_id=None,
            reason="lead_converted_to_candidate",
        )
        await db.commit()
    except Exception:
        await db.rollback()
    supervisor_id = await _load_supervisor_id(db, recruiter_id)
    recipient_ids: List[str] = []
    if recruiter_id:
        recipient_ids.append(recruiter_id)
    if supervisor_id:
        recipient_ids.append(supervisor_id)
    assignee_id = await _pick_lead_assignee_id(
        db,
        tenant_id=tenant_id,
        preferred_user_id=recruiter_id or supervisor_id,
        normalized=normalized,
        lead_id=agency_lead_id,
    )
    # Minimal rules builder (R2.2): trigger lead.processed automation rules (agency/employer path).
    try:
        rule_ctx_extras = await lead_custom_fields.automation_context_for_lead(
            db,
            tenant_id=tenant_id,
            lead_id=agency_lead_id,
            normalized=normalized if isinstance(normalized, dict) else {},
        )
        await run_automation_rules(
            db,
            tenant_id=tenant_id,
            trigger="lead.processed",
            actor_id=assignee_id,
            context={
                "entity_type": "lead",
                "entity_id": agency_lead_id,
                "lead_id": agency_lead_id,
                "source": lead.source,
                "status": "processed",
                "business_type": business_type,
                "company_id": resolved_company_id,
                "vacancy_id": str(vacancy.id) if vacancy else None,
                "candidate_id": str(candidate.id),
                "recruiter_id": recruiter_id,
                "assignee_id": assignee_id,
                **rule_ctx_extras,
            },
        )
        await db.commit()
    except Exception:
        await db.rollback()
    await _emit_lead_event(
        db,
        tenant_id=tenant_id,
        lead=lead,
        event_type="lead.processed",
        candidate_id=str(candidate.id),
        recruiter_id=recruiter_id,
        user_ids=recipient_ids,
        business_type=business_type,
        outcome_entity_type="candidate",
        outcome_entity_id=str(candidate.id),
        outcome_entity_name=None,
    )
    await db.commit()

    return MetaLeadResult(
        lead_id=lead.id,
        status="processed",
        vacancy_id=candidate.vacancy_id,
        candidate_id=str(candidate.id),
        recruiter_id=recruiter_id,
        business_type=business_type,
        outcome_entity_type="candidate",
        outcome_entity_id=str(candidate.id),
        outcome_entity_name=None,
        error=None,
        is_new=created_new,
    )
