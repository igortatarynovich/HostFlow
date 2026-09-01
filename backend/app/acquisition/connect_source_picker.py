"""Connect Source Meta picker enrichment — human labels for intake-source-options.

Donor compose: ``campaign_source_cards.enrich_intake_source_card``.
When ``form_name`` / page name are missing in SoT, hydrate once from Meta Graph
(page access token) and cache ``form_name`` on ``meta_lead_form_mappings``.
Connected Pages also contribute active ``/{page-id}/leadgen_forms`` so Connect
Source is not empty before the first lead.

See ``docs/specs/tasks/acquisition-ui-cutover-connect-source-picker-enrichment.md``.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.acquisition.campaign_source_cards import (
    enrich_intake_source_card,
    load_last_submission_by_endpoint,
    load_meta_form_mappings_by_form_id,
    parse_meta_form_id,
)
from backend.app.acquisition.endpoint_activity import intake_source_endpoint_id
from backend.app.models.intake_routing import IntakeSourceBinding, IntakeSourceProfile
from backend.app.models.lead import Lead, MetaAdsMap
from backend.app.models.vacancy import Vacancy

logger = logging.getLogger(__name__)


async def sample_ad_ids_by_form_id(
    db: AsyncSession,
    *,
    tenant_id: str,
    form_ids: set[str],
    per_form: int = 3,
) -> dict[str, list[str]]:
    if not form_ids:
        return {}
    wanted = {str(f).strip() for f in form_ids if str(f).strip()}
    rows = (
        await db.execute(
            select(Lead.ad_id, Lead.payload, Lead.created_at)
            .where(
                Lead.tenant_id == str(tenant_id),
                Lead.ad_id.isnot(None),
            )
            .order_by(Lead.created_at.desc())
            .limit(800)
        )
    ).all()
    out: dict[str, list[str]] = {fid: [] for fid in wanted}
    for ad_id, payload, _created in rows:
        aid = str(ad_id or "").strip()
        if not aid:
            continue
        form_id = ""
        try:
            entry = (payload or {}).get("entry") or []
            if entry:
                changes = (entry[0] or {}).get("changes") or []
                if changes:
                    value = (changes[0] or {}).get("value") or {}
                    form_id = str(value.get("form_id") or "").strip()
        except Exception:
            form_id = ""
        if form_id not in wanted:
            continue
        bucket = out[form_id]
        if aid not in bucket and len(bucket) < per_form:
            bucket.append(aid)
        if all(len(v) >= per_form for v in out.values()):
            break
    return {k: v for k, v in out.items() if v}


async def _local_ad_labels(
    db: AsyncSession,
    *,
    tenant_id: str,
    ad_ids: set[str],
) -> dict[str, str]:
    if not ad_ids:
        return {}
    numeric_ids: list[int] = []
    for raw in ad_ids:
        try:
            numeric_ids.append(int(str(raw).strip()))
        except (TypeError, ValueError):
            continue
    out: dict[str, str] = {}
    if not numeric_ids:
        return out
    rows = (
        await db.execute(
            select(MetaAdsMap.ad_id, MetaAdsMap.note, MetaAdsMap.vacancy_id).where(
                MetaAdsMap.tenant_id == str(tenant_id),
                MetaAdsMap.ad_id.in_(numeric_ids),
            )
        )
    ).all()
    vacancy_ids = {str(v) for _a, _n, v in rows if v}
    titles: dict[str, str] = {}
    if vacancy_ids:
        vrows = (
            await db.execute(
                select(Vacancy.id, Vacancy.title).where(Vacancy.id.in_(list(vacancy_ids)))
            )
        ).all()
        titles = {str(i): str(t).strip() for i, t in vrows if t and str(t).strip()}
    for ad_id, note, vacancy_id in rows:
        aid = str(ad_id)
        label = str(note or "").strip()
        if label and "—" in label:
            label = label.split("—", 1)[0].strip()
        if not label:
            label = titles.get(str(vacancy_id or ""), "")
        if label:
            out[aid] = label
    return out


async def _graph_hydrate_labels(
    db: AsyncSession,
    *,
    tenant_id: str,
    items: list[dict[str, Any]],
    ad_ids: set[str],
    local_ad_labels: dict[str, str],
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Return (form_name_by_id, page_name_by_id, ad_name_by_id). Cache form_name in mappings."""
    from backend.app.core.crypto import decrypt_secret
    from backend.app.modules.leads import admin_service
    from backend.app.modules.leads import crud as leads_crud
    from backend.app.modules.leads.meta_marketing_graph import (
        _graph_get,
        fetch_ad_node,
        fetch_page_node,
    )

    form_names: dict[str, str] = {}
    page_names: dict[str, str] = {}
    ad_names: dict[str, str] = dict(local_ad_labels)

    need_forms: list[tuple[str, Optional[str]]] = []
    need_pages: set[str] = set()
    for it in items:
        fid = str(it.get("meta_form_id") or "").strip()
        pid = str(it.get("page_id") or "").strip() or None
        fname = str(it.get("lead_form_name") or "").strip()
        if fid and not fname:
            need_forms.append((fid, pid))
        if pid and not str(it.get("page_name") or "").strip():
            need_pages.add(pid)

    need_ads = {a for a in ad_ids if a and a not in ad_names}

    async def token_for(page_id: Optional[str]) -> Optional[str]:
        if page_id:
            tok = await admin_service.get_page_access_token(db, tenant_id, page_id)
            if tok:
                return tok
        entries = await leads_crud.list_meta_credentials(db, tenant_id=tenant_id)
        for entry in entries:
            if str(getattr(entry, "status", "") or "").strip().lower() != "active":
                continue
            tok = decrypt_secret(entry.encrypted_access_token)
            if tok:
                return tok
        return None

    page_tokens: dict[str, str] = {}
    all_tokens: list[str] = []
    seen_tok: set[str] = set()
    for pid in need_pages:
        tok = await token_for(pid)
        if tok:
            page_tokens[pid] = tok
            if tok not in seen_tok:
                all_tokens.append(tok)
                seen_tok.add(tok)
    entries = await leads_crud.list_meta_credentials(db, tenant_id=tenant_id)
    for entry in entries:
        if str(getattr(entry, "status", "") or "").strip().lower() != "active":
            continue
        tok = decrypt_secret(entry.encrypted_access_token)
        if tok and tok not in seen_tok:
            all_tokens.append(tok)
            seen_tok.add(tok)
    fallback_token = all_tokens[0] if all_tokens else None

    async def fetch_form(fid: str, page_id: Optional[str]) -> None:
        candidates: list[str] = []
        preferred = page_tokens.get(page_id or "")
        if preferred:
            candidates.append(preferred)
        for tok in all_tokens:
            if tok not in candidates:
                candidates.append(tok)
        if not candidates:
            return
        for tok in candidates:
            try:
                data = await _graph_get(
                    fid, access_token=tok, params={"fields": "id,name,locale,status"}
                )
                name = str(data.get("name") or "").strip()
                if name:
                    form_names[fid] = name
                    try:
                        existing = await leads_crud.get_meta_form_mapping(
                            db,
                            tenant_id=tenant_id,
                            form_id=fid,
                            page_id=page_id,
                            source="meta",
                        )
                        if existing is not None:
                            existing.form_name = name
                            existing.updated_by = "connect_source_picker_graph"
                            await db.flush()
                        else:
                            await leads_crud.upsert_meta_form_mapping(
                                db,
                                tenant_id=tenant_id,
                                form_id=fid,
                                page_id=page_id,
                                source="meta",
                                mapping_rules=[],
                                form_name=name,
                                updated_by="connect_source_picker_graph",
                            )
                    except Exception:
                        logger.exception("cache form_name failed form_id=%s", fid)
                    return
            except Exception as exc:
                logger.info("graph form hydrate try failed form_id=%s: %s", fid, exc)
                continue

    async def fetch_page(pid: str) -> None:
        tok = page_tokens.get(pid) or fallback_token
        if not tok:
            return
        try:
            data = await fetch_page_node(pid, tok)
            name = str(data.get("name") or "").strip()
            if name:
                page_names[pid] = name
        except Exception as exc:
            logger.info("graph page hydrate failed page_id=%s: %s", pid, exc)

    async def fetch_ad(aid: str) -> None:
        tok = fallback_token or (next(iter(page_tokens.values())) if page_tokens else None)
        if not tok:
            return
        try:
            data = await fetch_ad_node(aid, tok)
            name = str(data.get("name") or "").strip()
            if name:
                ad_names[aid] = name
        except Exception as exc:
            logger.info("graph ad hydrate failed ad_id=%s: %s", aid, exc)

    await asyncio.gather(
        *(fetch_form(fid, pid) for fid, pid in need_forms),
        *(fetch_page(pid) for pid in need_pages),
        *(fetch_ad(aid) for aid in list(need_ads)[:12]),
        return_exceptions=True,
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("commit form_name cache failed")
    return form_names, page_names, ad_names


DISCOVERED_ID_PREFIX = "discovered:"


def discovered_option_id(form_id: str) -> str:
    return f"{DISCOVERED_ID_PREFIX}{str(form_id or '').strip()}"


def parse_discovered_form_id(option_id: str) -> Optional[str]:
    raw = str(option_id or "").strip()
    if not raw.startswith(DISCOVERED_ID_PREFIX):
        return None
    fid = raw[len(DISCOVERED_ID_PREFIX) :].strip()
    return fid or None


async def discover_leadgen_forms_from_connected_pages(
    db: AsyncSession, *, tenant_id: str
) -> list[dict[str, Optional[str]]]:
    """Active Lead Forms on Pages with stored Meta credentials (no wait for first lead)."""
    from backend.app.core.crypto import decrypt_secret
    from backend.app.modules.leads import crud as leads_crud
    from backend.app.modules.leads.meta_marketing_graph import fetch_page_leadgen_forms

    entries = await leads_crud.list_meta_credentials(db, tenant_id=tenant_id)
    out: list[dict[str, Optional[str]]] = []
    seen: set[str] = set()
    for entry in entries:
        if str(getattr(entry, "status", "") or "").strip().lower() != "active":
            continue
        page_id = (decrypt_secret(entry.encrypted_page_id) or "").strip()
        token = (decrypt_secret(entry.encrypted_access_token) or "").strip()
        if not page_id or not token:
            continue
        try:
            rows = await fetch_page_leadgen_forms(page_id, token, limit=50)
        except Exception as exc:
            logger.info("graph leadgen_forms failed page_id=%s: %s", page_id, exc)
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            status = str(row.get("status") or "ACTIVE").strip().upper()
            if status not in {"", "ACTIVE"}:
                continue
            fid = str(row.get("id") or "").strip()
            if not fid or fid in seen:
                continue
            seen.add(fid)
            name = str(row.get("name") or "").strip() or None
            out.append(
                {
                    "form_id": fid,
                    "page_id": page_id,
                    "form_name": name,
                    "source": "meta",
                }
            )
    return out


async def build_intake_source_options(
    db: AsyncSession,
    *,
    tenant_id: str,
    profiles: list[IntakeSourceProfile],
    hydrate_graph: bool = True,
    include_discovered: bool = True,
) -> list[dict[str, Any]]:
    profile_ids = [str(r.id) for r in profiles]
    bindings_by_profile: dict[str, list[IntakeSourceBinding]] = {pid: [] for pid in profile_ids}
    form_ids: set[str] = set()
    if profile_ids:
        bindings_rows = (
            await db.execute(
                select(IntakeSourceBinding).where(
                    IntakeSourceBinding.tenant_id == str(tenant_id),
                    IntakeSourceBinding.intake_source_profile_id.in_(profile_ids),
                )
            )
        ).scalars().all()
        for b in bindings_rows:
            pid = str(b.intake_source_profile_id)
            bindings_by_profile.setdefault(pid, []).append(b)
            fid = parse_meta_form_id(getattr(b, "external_key", "") or "")
            if fid:
                form_ids.add(fid)
    for r in profiles:
        code = str(r.code or "")
        if code.startswith("meta-form-"):
            form_ids.add(code[len("meta-form-") :])

    known_form_ids = set(form_ids)
    discovered_rows: list[dict[str, Optional[str]]] = []
    if include_discovered:
        from backend.app.modules.leads import crud as leads_crud

        discovered_rows = await leads_crud.list_discovered_meta_forms_from_leads(
            db, tenant_id=str(tenant_id), source="meta", limit=50
        )
        mapping_rows = await leads_crud.list_meta_form_mapping_rows(
            db, tenant_id=str(tenant_id), source="meta"
        )
        for row in mapping_rows:
            fid = str(getattr(row, "form_id", "") or "").strip()
            if not fid:
                continue
            discovered_rows.append(
                {
                    "form_id": fid,
                    "page_id": str(getattr(row, "page_id", "") or "").strip() or None,
                    "form_name": str(getattr(row, "form_name", "") or "").strip() or None,
                    "source": "meta",
                }
            )
        if hydrate_graph:
            graph_rows = await discover_leadgen_forms_from_connected_pages(
                db, tenant_id=str(tenant_id)
            )
            discovered_rows.extend(graph_rows)
        for row in discovered_rows:
            fid = str(row.get("form_id") or "").strip()
            if fid and fid not in known_form_ids:
                form_ids.add(fid)

    meta_by_form = await load_meta_form_mappings_by_form_id(
        db, tenant_id=str(tenant_id), form_ids=form_ids
    )
    endpoint_ids = [intake_source_endpoint_id(pid) for pid in profile_ids]
    last_by_endpoint = await load_last_submission_by_endpoint(
        db, tenant_id=str(tenant_id), endpoint_ids=endpoint_ids
    )
    sample_ads_map = await sample_ad_ids_by_form_id(
        db, tenant_id=str(tenant_id), form_ids=form_ids
    )

    draft: list[dict[str, Any]] = []
    all_ad_ids: set[str] = set()
    for r in profiles:
        pid = str(r.id)
        bindings = bindings_by_profile.get(pid) or []
        meta_form_id: Optional[str] = None
        for b in bindings:
            meta_form_id = parse_meta_form_id(getattr(b, "external_key", "") or "")
            if meta_form_id:
                break
        if not meta_form_id:
            code = str(r.code or "")
            if code.startswith("meta-form-"):
                meta_form_id = code[len("meta-form-") :] or None
        meta_map = meta_by_form.get(meta_form_id) if meta_form_id else None
        card = enrich_intake_source_card(
            r,
            bindings,
            meta_map=meta_map,
            last_submission_at=last_by_endpoint.get(intake_source_endpoint_id(pid)),
        )
        ads = list(sample_ads_map.get(str(card.meta_form_id or ""), []))
        all_ad_ids.update(ads)
        draft.append(
            {
                "id": pid,
                "name": str(r.name or r.code or r.id),
                "provider": str(r.provider or ""),
                "code": str(r.code or ""),
                "is_active": bool(r.is_active),
                "needs_create": False,
                "display_title": card.display_title,
                "lead_form_name": card.lead_form_name,
                "meta_form_id": card.meta_form_id,
                "page_id": card.page_id,
                "page_name": card.page_name,
                "last_submission_at": card.last_submission_at,
                "sample_ad_ids": ads,
                "sample_ads": [{"ad_id": a, "label": None} for a in ads],
            }
        )

    if include_discovered:
        for row in discovered_rows:
            fid = str(row.get("form_id") or "").strip()
            if not fid or fid in known_form_ids:
                continue
            known_form_ids.add(fid)
            page_id = str(row.get("page_id") or "").strip() or None
            meta_map = meta_by_form.get(fid)
            lead_form_name = None
            page_name = None
            if meta_map is not None:
                lead_form_name = str(getattr(meta_map, "form_name", None) or "").strip() or None
                if not page_id:
                    page_id = str(getattr(meta_map, "page_id", None) or "").strip() or None
            if not lead_form_name:
                lead_form_name = str(row.get("form_name") or "").strip() or None
            ads = list(sample_ads_map.get(fid, []))
            all_ad_ids.update(ads)
            code = f"meta-form-{fid}"
            title = lead_form_name or f"Meta form {fid}"
            draft.append(
                {
                    "id": discovered_option_id(fid),
                    "name": title,
                    "provider": "meta",
                    "code": code,
                    "is_active": True,
                    "needs_create": True,
                    "display_title": title,
                    "lead_form_name": lead_form_name,
                    "meta_form_id": fid,
                    "page_id": page_id,
                    "page_name": page_name,
                    "last_submission_at": None,
                    "sample_ad_ids": ads,
                    "sample_ads": [{"ad_id": a, "label": None} for a in ads],
                }
            )

    if not draft:
        return []

    local_labels = await _local_ad_labels(db, tenant_id=tenant_id, ad_ids=all_ad_ids)
    form_names: dict[str, str] = {}
    page_names: dict[str, str] = {}
    ad_names = dict(local_labels)
    needs_graph = hydrate_graph and any(
        (d.get("provider") or "").lower() == "meta"
        and (
            not d.get("lead_form_name")
            or (d.get("page_id") and not d.get("page_name"))
            or any(a not in local_labels for a in (d.get("sample_ad_ids") or []))
        )
        for d in draft
    )
    if needs_graph:
        form_names, page_names, ad_names = await _graph_hydrate_labels(
            db,
            tenant_id=tenant_id,
            items=draft,
            ad_ids=all_ad_ids,
            local_ad_labels=local_labels,
        )

    for d in draft:
        fid = str(d.get("meta_form_id") or "")
        page_id = str(d.get("page_id") or "")
        if not d.get("lead_form_name") and fid in form_names:
            d["lead_form_name"] = form_names[fid]
        if not d.get("page_name") and page_id in page_names:
            d["page_name"] = page_names[page_id]
        if d.get("lead_form_name"):
            d["display_title"] = d["lead_form_name"]
            if d.get("needs_create"):
                d["name"] = d["lead_form_name"]
        sample = []
        for aid in d.get("sample_ad_ids") or []:
            sample.append({"ad_id": str(aid), "label": ad_names.get(str(aid)) or None})
        d["sample_ads"] = sample
    return draft


__all__ = [
    "DISCOVERED_ID_PREFIX",
    "build_intake_source_options",
    "discover_leadgen_forms_from_connected_pages",
    "discovered_option_id",
    "parse_discovered_form_id",
    "sample_ad_ids_by_form_id",
]
