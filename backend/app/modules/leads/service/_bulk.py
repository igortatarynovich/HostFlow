"""Bulk + reprocess flows for normalized lead payloads.

Extracted from ``backend/app/modules/leads/service/__init__.py`` (Phase 1 #3
step 7/N): payload coercion / fallback merge, Meta-export queue
filtering+counting, single-lead bulk worker, the parallel
``bulk_auto_process_meta_lead_queue`` orchestrator, and
``reprocess_stored_lead_payload`` (admin re-run).

Re-exported via ``service/__init__.py`` so existing call-sites
(router, scripts, tests) keep using ``service.<name>`` access.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import async_session_maker
from backend.app.models import Lead
from backend.app.modules.leads import normalizer

from ._helpers import LeadProcessingError, MetaLeadResult, _load_settings
from ._processing import process_normalized_lead
from .intake_decision import manual_process_block_code


def _coerce_lead_payload_to_dict(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return dict(payload)
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _payload_needs_flat_field_data_coercion(payload: Dict[str, Any]) -> bool:
    """
    ``normalize_meta_payload`` reads ``field_data`` (or Meta webhook ``entry/.../value``).

    CSV import and other flat dicts have neither — wrap with
    ``coerce_generic_json_to_meta_normalizer_payload`` before normalizing.
    """
    if not isinstance(payload, dict) or not payload:
        return False
    entry = payload.get("entry")
    if isinstance(entry, list) and len(entry) > 0:
        return False
    if isinstance(payload.get("field_data"), list):
        return False
    return True


def _merge_lead_normalized_fallback(normalized: Dict[str, Any], prior: Any) -> None:
    """If re-normalizing emptied contacts, keep email/phone/name from the stored lead row."""
    if not isinstance(prior, dict):
        return

    def _empty(v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, str) and not v.strip():
            return True
        return False

    for key in (
        "email",
        "phone",
        "phone_country_code",
        "first_name",
        "last_name",
        "full_name",
        "experience_eu_years",
        "geo_country",
        "country",
    ):
        if not _empty(normalized.get(key)):
            continue
        pv = prior.get(key)
        if pv is None:
            continue
        if isinstance(pv, str) and not pv.strip():
            continue
        normalized[key] = pv
    if normalized.get("ad_id") is None and prior.get("ad_id") is not None:
        normalized["ad_id"] = prior.get("ad_id")
    if _empty(normalized.get("vacancy_id")) and prior.get("vacancy_id"):
        normalized["vacancy_id"] = prior.get("vacancy_id")
    if _empty(normalized.get("vacancy_id_hint")) and prior.get("vacancy_id_hint"):
        normalized["vacancy_id_hint"] = prior.get("vacancy_id_hint")
    if _empty(normalized.get("vacancy_id")) and prior.get("vacancy_id_hint"):
        try:
            normalized["vacancy_id"] = str(UUID(str(prior.get("vacancy_id_hint")).strip()))
        except ValueError:
            pass
    em = normalized.get("email")
    if isinstance(em, str):
        lowered = em.strip().lower()
        normalized["email"] = lowered or None

    for preserve_key in (
        "duplicate_override_v1",
        "duplicate_decisions_history_v1",
        "duplicate_resolution_v1",
        "intake_vacancy_confirm_v1",
        "intake_resolution_v1",
        "recruitment_pool_intent_v1",
        "call_result_v1",
        "call_results_v1",
        "field_answers",
        "additional_answers",
        "raw_field_names",
        "form_question_labels_v1",
        "company_name",
        "company_name_hint",
        "company_profile",
        "company_hints",
    ):
        if preserve_key not in prior:
            continue
        pv = prior[preserve_key]
        if pv is None:
            continue
        cur = normalized.get(preserve_key)
        if preserve_key not in normalized:
            normalized[preserve_key] = pv
        elif isinstance(pv, dict) and isinstance(cur, dict) and not cur and pv:
            normalized[preserve_key] = pv
        elif isinstance(pv, list) and (not cur) and pv:
            normalized[preserve_key] = pv
        elif preserve_key == "recruitment_pool_intent_v1" and pv is True and cur is not True:
            normalized[preserve_key] = True
        elif preserve_key in {"company_name", "company_name_hint"} and _empty(cur) and not _empty(pv):
            normalized[preserve_key] = pv


async def refresh_meta_lead_normalized_from_stored_payload(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Re-normalize ``field_data`` from stored payload into ``lead.normalized`` without
    running the full conversion pipeline (Graph recovery / UI contact display).
    """
    from backend.app.modules.leads.field_mapping_resolve import resolve_field_mapping_for_ingest
    from backend.app.services.lead_communications import normalized_merging_lead_persisted_blocks

    settings_row = await _load_settings(db, tenant_id)
    payload_dict = _coerce_lead_payload_to_dict(payload if payload is not None else lead.payload)
    to_normalize = (
        normalizer.coerce_generic_json_to_meta_normalizer_payload(payload_dict)
        if _payload_needs_flat_field_data_coercion(payload_dict)
        else payload_dict
    )
    field_mapping = await resolve_field_mapping_for_ingest(
        db,
        tenant_id=tenant_id,
        payload=to_normalize,
        source=str(getattr(lead, "source", None) or "meta"),
        settings_row=settings_row,
    )
    normalized = normalizer.normalize_meta_payload(to_normalize, field_mapping=field_mapping)
    normalized.pop("graph_error", None)
    if payload_dict and not _payload_has_graph_error(payload_dict):
        lead.payload = payload_dict
    lead.normalized = normalized_merging_lead_persisted_blocks(lead, normalized)
    if _is_graph_error(getattr(lead, "error", None)):
        lead.error = None
    await db.flush()
    return normalized


def _payload_has_graph_error(payload: Dict[str, Any]) -> bool:
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if not isinstance(change, dict):
                continue
            if change.get("field") != "leadgen":
                continue
            value = change.get("value")
            if isinstance(value, dict) and str(value.get("graph_error") or "").strip():
                return True
    return False


def _is_graph_error(error: Optional[str]) -> bool:
    return str(error or "").strip().upper().startswith("GRAPH_")


def _ad_id_from_meta_lead_export_row(payload: Dict[str, Any]) -> Optional[int]:
    """
    Meta Lead Center CSV exports often use tab-separated rows and ad_id values like 'ag:120245658843840547'.
    """
    return normalizer.parse_meta_export_ad_id(payload.get("ad_id"))


def _bulk_auto_process_meta_queue_filters(
    *,
    tenant_id: str,
    own_company_id: Optional[str],
    statuses: tuple[str, ...],
    only_without_candidate: bool,
    error_equals: Optional[str],
) -> List[Any]:
    st_tuple = tuple(str(s).strip() for s in statuses if str(s or "").strip()) or ("needs_routing", "failed")
    filters: List[Any] = [
        Lead.tenant_id == tenant_id,
        Lead.status.in_(st_tuple),
        func.lower(Lead.source).in_(("meta", "csv_import")),
    ]
    if own_company_id:
        filters.append(Lead.own_company_id == own_company_id)
    if only_without_candidate:
        filters.append(Lead.candidate_id.is_(None))
    if error_equals is not None:
        e = str(error_equals).strip()
        if e:
            filters.append(Lead.error == e)
    return filters


async def count_bulk_auto_process_meta_lead_queue(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str],
    statuses: tuple[str, ...] = ("needs_routing", "failed"),
    only_without_candidate: bool = False,
    error_equals: Optional[str] = None,
) -> int:
    """Same selection rules as ``bulk_auto_process_meta_lead_queue`` (no limit)."""
    filters = _bulk_auto_process_meta_queue_filters(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        statuses=statuses,
        only_without_candidate=only_without_candidate,
        error_equals=error_equals,
    )
    stmt = select(func.count()).select_from(Lead).where(*filters)
    return int((await db.execute(stmt)).scalar_one() or 0)


async def _bulk_auto_process_single_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str],
    lead: Lead,
    force_candidate_conversion: bool = False,
) -> Dict[str, Any]:
    """One lead through the same pipeline as the bulk queue loop (meta / csv_import)."""
    lid = str(lead.id)
    if not getattr(lead, "payload", None):
        return {
            "lead_id": lid,
            "ok": False,
            "status_after": lead.status,
            "error": "Lead payload is missing",
        }
    # Same doctrine as ``POST /leads/{id}/process``: bulk must not bypass intake / routing gates.
    block = await manual_process_block_code(db, tenant_id, lead)
    if block:
        return {
            "lead_id": lid,
            "ok": False,
            "status_after": lead.status,
            "error": block,
        }
    force_existing = bool(getattr(lead, "candidate_id", None) is None) and getattr(lead, "status", None) in {
        "processed",
        "duplicated",
        "duplicate_review",
    }
    src = (getattr(lead, "source", None) or "").strip().lower()
    try:
        if src == "csv_import":
            payload_dict = _coerce_lead_payload_to_dict(getattr(lead, "payload", None))
            if not payload_dict:
                return {
                    "lead_id": lid,
                    "ok": False,
                    "status_after": lead.status,
                    "error": "Lead payload is empty or invalid",
                }
            prior_norm = dict(lead.normalized or {})
            ad_int = _ad_id_from_meta_lead_export_row(payload_dict)
            if ad_int is not None:
                prior_norm["ad_id"] = ad_int
            elif prior_norm.get("ad_id") is None and getattr(lead, "ad_id", None) is not None:
                try:
                    prior_norm["ad_id"] = int(lead.ad_id)
                except (TypeError, ValueError):
                    pass
            out = await reprocess_stored_lead_payload(
                db,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                payload=payload_dict,
                source="csv_import",
                force_existing=force_existing,
                external_id_hint=(str(lead.external_id).strip() if getattr(lead, "external_id", None) else None),
                prior_normalized=prior_norm,
                force_candidate_conversion=force_candidate_conversion,
                stored_db_vacancy_id=(str(lead.vacancy_id).strip() if getattr(lead, "vacancy_id", None) else None)
                or None,
                stored_db_ad_id=getattr(lead, "ad_id", None),
                stored_lead_id=lid,
            )
        else:
            out = await process_meta_lead(
                db,
                tenant_id=tenant_id,
                own_company_id=own_company_id,
                payload=lead.payload,
                force_existing=force_existing,
                force_candidate_conversion=force_candidate_conversion,
                stored_db_vacancy_id=(str(lead.vacancy_id).strip() if getattr(lead, "vacancy_id", None) else None)
                or None,
                stored_db_ad_id=getattr(lead, "ad_id", None),
                stored_lead_id=lid,
            )
        return {
            "lead_id": lid,
            "ok": True,
            "status_after": out.status,
            "error": None,
        }
    except LeadProcessingError as exc:
        try:
            await db.rollback()
        except Exception:
            pass
        return {
            "lead_id": lid,
            "ok": False,
            "status_after": getattr(lead, "status", None),
            "error": str(exc.message or exc),
        }
    except Exception as exc:
        try:
            await db.rollback()
        except Exception:
            pass
        return {
            "lead_id": lid,
            "ok": False,
            "status_after": getattr(lead, "status", None),
            "error": str(exc),
        }


async def bulk_auto_process_meta_lead_queue(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str],
    max_items: int = 25,
    statuses: tuple[str, ...] = ("needs_routing", "failed"),
    prefer_oldest_first: bool = False,
    only_without_candidate: bool = False,
    error_equals: Optional[str] = None,
    concurrency: int = 12,
    force_candidate_conversion: bool = False,
) -> Dict[str, Any]:
    """
    Process up to `max_items` leads stuck in routing/processing queues.

    - **meta**: same pipeline as POST .../process (``process_meta_lead``).
    - **csv_import**: same as ``reprocess_stored_lead_payload`` (coercion + merge) with ``ad_id`` from export rows.

    Default statuses: needs_routing / failed (auto-fix). Optional: status=new (NBA «unprocessed» batch).
    If ``only_without_candidate`` is true, skips rows that already have ``candidate_id``.
    If ``error_equals`` is set (e.g. ``VACANCY_NOT_RESOLVED``), only those ``Lead.error`` values match.

    ``concurrency`` > 1 runs leads in parallel (one AsyncSession per lead, bounded by a semaphore).
    ``concurrency`` == 1 uses the caller's ``db`` session sequentially (legacy behavior).

    ``force_candidate_conversion``: bypass assisted-mode / fit triage gates so candidates can be created when a vacancy resolves (bulk operator escape hatch). Intake operational blocks (reject, info requested, duplicate review, routing) still apply — use ``manual_process_block_code`` / ``POST .../process`` doctrine.
    """
    max_items = max(1, min(int(max_items or 25), 50))
    conc = max(1, min(int(concurrency or 1), 32))
    filters = _bulk_auto_process_meta_queue_filters(
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        statuses=statuses,
        only_without_candidate=only_without_candidate,
        error_equals=error_equals,
    )

    # Lead has no ``updated_at``; use ``created_at`` for FIFO/LIFO ordering.
    order = Lead.created_at.asc() if prefer_oldest_first else Lead.created_at.desc()

    if conc <= 1:
        stmt = select(Lead).where(*filters).order_by(order).limit(max_items)
        rows = (await db.execute(stmt)).scalars().all()
        results = []
        for lead in rows:
            results.append(
                await _bulk_auto_process_single_lead(
                    db,
                    tenant_id=tenant_id,
                    own_company_id=own_company_id,
                    lead=lead,
                    force_candidate_conversion=force_candidate_conversion,
                )
            )
    else:
        stmt_ids = select(Lead.id).where(*filters).order_by(order).limit(max_items)
        lead_ids = [str(x) for x in (await db.execute(stmt_ids)).scalars().all()]
        sem = asyncio.Semaphore(conc)

        async def _work(lead_id: str) -> Dict[str, Any]:
            async with sem:
                async with async_session_maker() as wdb:
                    lead = await wdb.get(Lead, lead_id)
                    if lead is None:
                        return {
                            "lead_id": lead_id,
                            "ok": False,
                            "status_after": None,
                            "error": "Lead not found",
                        }
                    if str(lead.tenant_id) != str(tenant_id):
                        return {
                            "lead_id": lead_id,
                            "ok": False,
                            "status_after": getattr(lead, "status", None),
                            "error": "Tenant mismatch",
                        }
                    return await _bulk_auto_process_single_lead(
                        wdb,
                        tenant_id=tenant_id,
                        own_company_id=own_company_id,
                        lead=lead,
                        force_candidate_conversion=force_candidate_conversion,
                    )

        results = await asyncio.gather(*[_work(lid) for lid in lead_ids])

    succeeded = sum(1 for r in results if r.get("ok"))
    failed = len(results) - succeeded
    return {"results": results, "attempted": len(results), "succeeded": succeeded, "failed": failed}


def _apply_stored_lead_row_ids_to_normalized(
    normalized: Dict[str, Any],
    *,
    db_vacancy_id: Optional[str],
    db_ad_id: Optional[Any],
) -> None:
    """When UI/DB already set vacancy/ad on the Lead row, payload re-normalization may drop them."""
    def _empty(v: Any) -> bool:
        if v is None:
            return True
        if isinstance(v, str) and not v.strip():
            return True
        return False

    if db_vacancy_id and _empty(normalized.get("vacancy_id")) and _empty(normalized.get("vacancy_id_hint")):
        vs = str(db_vacancy_id).strip()
        if vs:
            try:
                normalized["vacancy_id"] = str(UUID(vs))
            except ValueError:
                normalized["vacancy_id_hint"] = vs
    if normalized.get("ad_id") is None and db_ad_id is not None:
        try:
            normalized["ad_id"] = int(db_ad_id)
        except (TypeError, ValueError):
            pass


async def reprocess_stored_lead_payload(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    payload: Dict[str, Any],
    source: str,
    force_existing: bool = False,
    external_id_hint: Optional[str] = None,
    prior_normalized: Optional[Dict[str, Any]] = None,
    force_candidate_conversion: bool = False,
    stored_db_vacancy_id: Optional[str] = None,
    stored_db_ad_id: Optional[Any] = None,
    stored_lead_id: Optional[str] = None,
) -> MetaLeadResult:
    """
    Re-run field mapping + ``process_normalized_lead`` for a lead row already stored in DB.

    Used by webhook/Meta ingest, bulk queue, and ``POST /leads/{id}/manual`` processing.
    ``source`` must match the stored lead (e.g. ``meta`` vs ``csv_import``) so external_id lookup works.

    **CSV / flat rows:** ``normalize_meta_payload`` expects ``field_data`` or a Meta webhook shape.
    Plain dicts are coerced first.     ``prior_normalized`` + ``external_id_hint`` avoid losing contacts
    and dedupe keys when the raw row does not include synthetic ids.

    ``stored_lead_id``: when re-running a specific DB row, pass its id so routing does not
    bind to another lead sharing the same Meta ``external_id`` (duplicate CSV/webhook rows).
    """
    settings_row = await _load_settings(db, tenant_id)
    payload_dict = _coerce_lead_payload_to_dict(payload)
    to_normalize = (
        normalizer.coerce_generic_json_to_meta_normalizer_payload(payload_dict)
        if _payload_needs_flat_field_data_coercion(payload_dict)
        else payload_dict
    )
    from backend.app.entity_profile.ingest_runtime import (
        prepare_meta_ingest_runtime,
        stamp_ingest_envelope_v1,
        stamp_mapping_applied_from_envelope,
    )

    validated_mapping, ingest_envelope, intake_route, _profile_view = await prepare_meta_ingest_runtime(
        db,
        tenant_id=tenant_id,
        source=source,
        raw_payload=to_normalize,
        own_company_id=own_company_id,
        settings_row=settings_row,
        vacancy_id=str(stored_db_vacancy_id).strip() if stored_db_vacancy_id else None,
    )
    normalized = normalizer.normalize_meta_payload(
        to_normalize,
        field_mapping=validated_mapping,
    )
    ingest_envelope.normalized_payload = dict(normalized)
    stamp_ingest_envelope_v1(normalized, ingest_envelope)
    stamp_mapping_applied_from_envelope(
        normalized,
        rules=list(validated_mapping or []),
        envelope=ingest_envelope,
        profile_updated_at=str(
            (ingest_envelope.mapping_result or {}).get("profile_updated_at") or ""
        ).strip()
        or None,
    )
    normalized["intake_routing_v1"] = intake_route.to_intake_routing_v1()
    normalized["intake_route_v1"] = intake_route.to_normalized_block()
    if intake_route.entity_profile_code:
        normalized.setdefault("entity_profile_code", intake_route.entity_profile_code)
    _merge_lead_normalized_fallback(normalized, prior_normalized)
    _apply_stored_lead_row_ids_to_normalized(
        normalized,
        db_vacancy_id=stored_db_vacancy_id,
        db_ad_id=stored_db_ad_id,
    )
    raw_lead_id = normalized.get("raw_lead_id")
    external_id = str(raw_lead_id).strip() if raw_lead_id else None
    if not external_id and external_id_hint:
        external_id = str(external_id_hint).strip() or None
    src = (source or "meta").strip().lower() or "meta"
    return await process_normalized_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        payload=payload_dict,
        normalized=normalized,
        source=src,
        external_id=external_id,
        force_existing=force_existing,
        force_candidate_conversion=force_candidate_conversion,
        target_lead_id=stored_lead_id,
    )
async def process_meta_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    payload: Dict[str, Any],
    force_existing: bool = False,
    force_candidate_conversion: bool = False,
    stored_db_vacancy_id: Optional[str] = None,
    stored_db_ad_id: Optional[Any] = None,
    stored_lead_id: Optional[str] = None,
) -> MetaLeadResult:
    return await reprocess_stored_lead_payload(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        payload=payload,
        source="meta",
        force_existing=force_existing,
        force_candidate_conversion=force_candidate_conversion,
        stored_db_vacancy_id=stored_db_vacancy_id,
        stored_db_ad_id=stored_db_ad_id,
        stored_lead_id=stored_lead_id,
    )


async def process_generic_inbound_webhook_lead(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: Optional[str] = None,
    body: Dict[str, Any],
) -> MetaLeadResult:
    """
    §2.11: arbitrary JSON POST → same field_mapping + process_normalized_lead as Meta; source=webhook.
    """
    settings_row = await _load_settings(db, tenant_id)
    coerced = normalizer.coerce_generic_json_to_meta_normalizer_payload(body)
    from backend.app.entity_profile.ingest_runtime import (
        prepare_meta_ingest_runtime,
        stamp_ingest_envelope_v1,
        stamp_mapping_applied_from_envelope,
    )

    validated_mapping, ingest_envelope, intake_route, _profile_view = await prepare_meta_ingest_runtime(
        db,
        tenant_id=tenant_id,
        source="webhook",
        raw_payload=coerced,
        own_company_id=own_company_id,
        settings_row=settings_row,
    )
    normalized = normalizer.normalize_meta_payload(
        coerced,
        field_mapping=validated_mapping,
    )
    ingest_envelope.normalized_payload = dict(normalized)
    stamp_ingest_envelope_v1(normalized, ingest_envelope)
    stamp_mapping_applied_from_envelope(
        normalized,
        rules=list(validated_mapping or []),
        envelope=ingest_envelope,
        profile_updated_at=str(
            (ingest_envelope.mapping_result or {}).get("profile_updated_at") or ""
        ).strip()
        or None,
    )
    normalized["intake_routing_v1"] = intake_route.to_intake_routing_v1()
    normalized["intake_route_v1"] = intake_route.to_normalized_block()
    raw_lead_id = normalized.get("raw_lead_id")
    external_id = str(raw_lead_id).strip() if raw_lead_id else None
    return await process_normalized_lead(
        db,
        tenant_id=tenant_id,
        own_company_id=own_company_id,
        payload=body,
        normalized=normalized,
        source="webhook",
        external_id=external_id,
        force_existing=False,
    )
