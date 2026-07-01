"""Resolve document checklist from vacancy-linked CandidateProfile (single source with CRM UI)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.candidate_profile import CandidateProfile
from backend.app.models.document_type import DocumentType
from backend.app.models.vacancy import Vacancy
from backend.app.services.document_catalog import normalize_doc_type

DRIVER_CE_DEFAULT_PROFILE_CODE = "driver_ce_default"


def _try_uuid_key(raw: object) -> Optional[str]:
    """Return canonical UUID string if ``raw`` is a UUID, else None."""
    s = str(raw or "").strip()
    if not s:
        return None
    try:
        return str(UUID(s))
    except ValueError:
        pass
    compact = "".join(c for c in s if c.isalnum())
    if len(compact) == 32:
        try:
            return str(UUID(compact))
        except ValueError:
            return None
    return None


def _catalog_code_from_row_code(code: str) -> str:
    raw = str(code or "").strip().lower()
    if not raw:
        return "additional_document"
    n = normalize_doc_type(raw)
    if n == "additional_document":
        return raw
    return n


async def resolve_vacancy_profile_for_document_checklist(
    session: AsyncSession,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[CandidateProfile]:
    """Vacancy profile if set; otherwise tenant ``driver_ce_default`` profile."""
    tid = str(tenant_id).strip()
    profile: Optional[CandidateProfile] = None
    vid = getattr(candidate, "vacancy_id", None)
    if vid:
        v = await session.get(Vacancy, str(vid))
        if v is not None and str(getattr(v, "tenant_id", "")) == tid:
            pid = getattr(v, "candidate_profile_id", None)
            if pid:
                profile = await session.get(CandidateProfile, str(pid))
                if profile is not None and not getattr(profile, "is_active", True):
                    profile = None
    if profile is None:
        row = await session.execute(
            select(CandidateProfile)
            .where(CandidateProfile.tenant_id == tid)
            .where(CandidateProfile.code == DRIVER_CE_DEFAULT_PROFILE_CODE)
            .limit(1)
        )
        profile = row.scalar_one_or_none()
    return profile


async def checklist_dict_from_profile(
    session: AsyncSession,
    tenant_id: str,
    profile: CandidateProfile,
) -> Optional[Dict[str, Any]]:
    """Build requiredTypes/optionalTypes from ``profile.config.document_configs``.

    Resolves ``document_type_id`` UUIDs to catalog codes via ``document_types`` so
    owner-summary / UI show ``passport`` instead of raw ids.
    """
    cfg = profile.config or {}
    configs = cfg.get("document_configs")
    if not isinstance(configs, list) or not configs:
        return None

    tid = str(tenant_id).strip()
    uuid_keys: List[str] = []
    for item in configs:
        if not isinstance(item, dict):
            continue
        hint = item.get("document_type_code") or item.get("code")
        if hint and str(hint).strip():
            continue
        raw = item.get("document_type_id") or item.get("doc_type")
        if not raw:
            continue
        raw_str = str(raw).strip()
        norm_underscored = raw_str.lower().replace("-", "_").replace(" ", "_")
        if normalize_doc_type(norm_underscored) != "additional_document":
            continue
        uid = _try_uuid_key(raw_str)
        if uid:
            uuid_keys.append(uid)

    id_to_catalog: Dict[str, str] = {}
    if uuid_keys:
        uniq = list(dict.fromkeys(uuid_keys))
        rows = (
            await session.execute(
                select(DocumentType.id, DocumentType.code).where(
                    DocumentType.tenant_id == tid,
                    DocumentType.id.in_(uniq),
                )
            )
        ).all()
        for did, dcode in rows:
            if did:
                id_to_catalog[str(did)] = _catalog_code_from_row_code(str(dcode or ""))

    required: List[str] = []
    optional: List[str] = []
    seen_r: set[str] = set()
    seen_o: set[str] = set()

    for item in configs:
        if not isinstance(item, dict):
            continue
        code: Optional[str] = None
        hint = item.get("document_type_code") or item.get("code")
        if hint and str(hint).strip():
            h = str(hint).strip().lower()
            n = normalize_doc_type(h)
            code = n if n != "additional_document" else h

        raw = item.get("document_type_id") or item.get("doc_type")
        if code is None and raw:
            raw_str = str(raw).strip()
            norm_underscored = raw_str.lower().replace("-", "_").replace(" ", "_")
            n2 = normalize_doc_type(norm_underscored)
            if n2 != "additional_document":
                code = n2
            else:
                uid = _try_uuid_key(raw_str)
                if uid and uid in id_to_catalog:
                    code = id_to_catalog[uid]
                elif norm_underscored:
                    code = norm_underscored

        if not code:
            continue

        if bool(item.get("required")):
            if code not in seen_r:
                required.append(code)
                seen_r.add(code)
        else:
            if code not in seen_o:
                optional.append(code)
                seen_o.add(code)

    optional = [t for t in optional if t not in seen_r]
    return {
        "requiredTypes": required,
        "optionalTypes": optional,
        "debug": {
            "schema": "candidate_profile",
            "profile_id": str(profile.id),
            "profile_code": profile.code,
        },
    }


async def profile_checklist_for_owner_summary(
    session: AsyncSession,
    tenant_id: str,
    candidate: Candidate,
) -> Optional[Dict[str, Any]]:
    """Checklist dict for ``compute_owner_summary(..., checklist=...)`` from vacancy/default profile."""
    prof = await resolve_vacancy_profile_for_document_checklist(session, tenant_id, candidate)
    if prof is None:
        return None
    return await checklist_dict_from_profile(session, tenant_id, prof)
