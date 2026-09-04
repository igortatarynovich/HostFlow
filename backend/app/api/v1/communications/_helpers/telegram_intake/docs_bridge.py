"""Sub-module of telegram_intake (Phase 1 god-module split, step 8/N)."""

from __future__ import annotations

import re
import secrets
import logging
from datetime import timedelta
from typing import Any, Dict
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.settings import settings
from backend.app.models.candidate import Candidate
from backend.app.services.candidate_notifications import get_document_display_name
from backend.app.services.document_hub_delivery_contract import (
    compute_owner_summary_via_contract,
    ensure_ruleset_seed_via_contract,
    list_candidate_documents_via_contract,
)
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.ruleset_versioning import normalize_ruleset_payload

from ..candidate_lookup import (
    _candidate_apply_url,
)
from ..utils import (
    _as_dict,
    _coerce_datetime,
    _now_utc,
)
from .ui_text import (
    _candidate_owner_context_for_docs,
    _format_doc_types_bullets,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 4. Documents-context bridge (intake-token, ruleset/owner-summary snapshot).
# ---------------------------------------------------------------------------


def _generate_public_candidate_token() -> str:
    return secrets.token_urlsafe(24)


def _ensure_candidate_intake_token(candidate: Candidate) -> bool:
    now = _now_utc()
    token = str(getattr(candidate, "intake_token", None) or "").strip()
    expires_at = _coerce_datetime(getattr(candidate, "intake_token_expires_at", None))
    if token and expires_at and expires_at > now:
        return False
    if not token:
        candidate.intake_token = _generate_public_candidate_token()
        candidate.intake_token_created_at = now
    candidate.intake_token_expires_at = now + timedelta(days=30)
    return True


def _candidate_intake_documents_url(
    candidate: Candidate, doc_type: str | None = None
) -> str | None:
    """Public intake apply flow with documents step (replaces legacy /public/scan)."""
    token = str(getattr(candidate, "intake_token", None) or "").strip()
    if not token:
        return None
    base_url = (
        str(settings.frontend_url or "https://hostflow.cc").strip()
        or "https://hostflow.cc"
    )
    params: Dict[str, str] = {"mode": "documents"}
    doc_norm = str(doc_type or "").strip()
    if doc_norm:
        params["doc"] = doc_norm
    return f"{base_url.rstrip('/')}/public/apply/{token}?{urlencode(params)}"


async def _telegram_required_docs_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Dict[str, Any]:
    oc = getattr(candidate, "own_company_id", None)
    own_company_id = str(oc).strip() if oc else None
    ruleset_version = await ensure_ruleset_seed_via_contract(
        db,
        tenant_id=str(tenant_id),
        ruleset_payload=load_default_ruleset(),
        own_company_id=own_company_id,
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    owner_context = _candidate_owner_context_for_docs(candidate)
    from backend.app.reference.document_policy_overlay_store import load_persisted_tenant_delta

    owner_context["tenant_delta"] = await load_persisted_tenant_delta(db, str(tenant_id))

    docs = await list_candidate_documents_via_contract(
        db,
        tenant_id=str(tenant_id),
        candidate_id=str(candidate.id),
        include_deleted=False,
        active_own_company_id=own_company_id,
    )

    serialized_docs: list[dict[str, Any]] = []
    for doc in docs:
        status_value = (
            doc.status.value
            if hasattr(doc.status, "value")
            else str(doc.status or "").strip().lower()
        )
        expire_date = getattr(doc, "expire_date", None)
        serialized_docs.append(
            {
                "type": str(doc.doc_type or "").strip(),
                "doc_type": str(doc.doc_type or "").strip(),
                "status": status_value,
                "expires_at": expire_date.isoformat() if expire_date is not None else None,
            }
        )

    summary = compute_owner_summary_via_contract(owner_context, ruleset_payload, serialized_docs)
    required = _as_dict(summary.get("required"))
    return {
        "total": int(required.get("total") or 0),
        "ready": int(required.get("ready") or 0),
        "in_progress": [
            str(item)
            for item in (required.get("in_progress_types") or [])
            if str(item or "").strip()
        ],
        "missing": [
            str(item)
            for item in (required.get("missing") or [])
            if str(item or "").strip()
        ],
        "problematic": [
            str(item)
            for item in (required.get("problematic") or [])
            if str(item or "").strip()
        ],
        "docs_count": len(serialized_docs),
    }


async def _telegram_docs_checklist_text(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> str:
    snapshot = await _telegram_required_docs_snapshot(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    total = int(snapshot.get("total") or 0)
    ready = int(snapshot.get("ready") or 0)
    in_progress = list(snapshot.get("in_progress") or [])
    missing = list(snapshot.get("missing") or [])
    problematic = list(snapshot.get("problematic") or [])
    docs_count = int(snapshot.get("docs_count") or 0)

    if total <= 0:
        if docs_count > 0:
            return f"Документы загружены: {docs_count}. Обязательный чеклист не задан."
        return "По вашему профилю пока нет документов и обязательного чеклиста."

    lines: list[str] = [f"Чеклист документов: {ready}/{total} готово"]
    if missing:
        lines.append("Не хватает:")
        lines.extend(_format_doc_types_bullets(missing))
    if in_progress:
        lines.append("В обработке:")
        lines.extend(_format_doc_types_bullets(in_progress))
    if problematic:
        lines.append("Нужна замена/исправление:")
        lines.extend(_format_doc_types_bullets(problematic))
    return "\n".join(lines)


async def _tg_intake_completion_docs_text(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> str:
    lines: list[str] = [
        "Анкета заполнена. Спасибо.",
    ]
    try:
        snapshot = await _telegram_required_docs_snapshot(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
        )
        total = int(snapshot.get("total") or 0)
        ready = int(snapshot.get("ready") or 0)
        missing = [
            str(x)
            for x in (snapshot.get("missing") or [])
            if str(x or "").strip()
        ]
        in_progress = [
            str(x)
            for x in (snapshot.get("in_progress") or [])
            if str(x or "").strip()
        ]
        problematic = [
            str(x)
            for x in (snapshot.get("problematic") or [])
            if str(x or "").strip()
        ]

        if total > 0:
            lines.append(f"Чеклист документов: {ready}/{total} готово")
            if missing:
                lines.append("Осталось загрузить:")
                lines.extend(_format_doc_types_bullets(missing, limit=3))
        else:
            docs_count = int(snapshot.get("docs_count") or 0)
            if docs_count > 0:
                lines.append(f"Документы уже загружены: {docs_count}.")
            else:
                lines.append(
                    "Обязательный чеклист пока не настроен. Можете открыть /docs."
                )

        next_doc = (
            missing[0]
            if missing
            else (
                in_progress[0]
                if in_progress
                else (problematic[0] if problematic else None)
            )
        )
        docs_url = _candidate_intake_documents_url(candidate, doc_type=next_doc)
        if next_doc:
            lines.append(f"Следующий шаг: /scan {next_doc}")
        if docs_url:
            lines.append(f"Ссылка на загрузку документов: {docs_url}")
        lines.append("Полный список документов: /docs")
    except Exception:
        logger.exception(
            "telegram intake completion docs-summary failed tenant=%s candidate=%s",
            tenant_id,
            getattr(candidate, "id", None),
        )
        lines.append("Дальше проверьте список обязательных документов командой /docs.")
    return "\n".join(lines)


async def _telegram_scan_command_text(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    requested_doc_type: str | None = None,
) -> str:
    snapshot = await _telegram_required_docs_snapshot(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    missing = list(snapshot.get("missing") or [])
    in_progress = list(snapshot.get("in_progress") or [])
    problematic = list(snapshot.get("problematic") or [])

    requested = str(requested_doc_type or "").strip().lower()
    if requested:
        requested = re.sub(r"[^a-z0-9_]", "", requested)
    preferred_doc: str | None = None
    allowed_docs = set(missing + in_progress + problematic)
    if requested and requested in allowed_docs:
        preferred_doc = requested
    elif missing:
        preferred_doc = missing[0]
    elif in_progress:
        preferred_doc = in_progress[0]
    elif problematic:
        preferred_doc = problematic[0]
    elif requested:
        preferred_doc = requested

    docs_url = _candidate_intake_documents_url(candidate, preferred_doc)
    apply_url = _candidate_apply_url(candidate)
    if not docs_url:
        if apply_url:
            return (
                f"Загрузка документов недоступна без intake token. "
                f"Откройте анкету: {apply_url}"
            )
        return "Ссылка на загрузку документов пока недоступна. Обратитесь к менеджеру."

    lines: list[str] = []
    if preferred_doc:
        label = str(get_document_display_name(preferred_doc) or preferred_doc)
        lines.append(f"Загрузка документа «{label}» на сайте:")
    else:
        lines.append("Откройте загрузку документов на сайте:")
    lines.append(docs_url)
    if missing:
        lines.append("")
        lines.append("Осталось загрузить обязательно:")
        lines.extend(_format_doc_types_bullets(missing, limit=3))
    if apply_url:
        lines.append("")
        lines.append(f"Полная анкета: {apply_url}")
    return "\n".join(lines)
