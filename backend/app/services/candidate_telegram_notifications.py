from __future__ import annotations

import logging
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
from typing import Any, Dict
from uuid import uuid4

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.stages import LABELS as CANDIDATE_STAGE_LABELS
from backend.app.core.crypto import decrypt_secret
from backend.app.core.settings import settings
from backend.app.models.candidate import Candidate
from backend.app.models.candidate_stage_history import CandidateStageHistory
from backend.app.models.communication import CommunicationChannelAccount
from backend.app.modules.documents.crud import ensure_ruleset_seed, list_candidate_documents
from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.services.candidate_notifications import get_document_display_name
from backend.app.services.communications_telegram import TelegramBotConfig, send_telegram_text
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.ruleset_versioning import normalize_ruleset_payload
from backend.app.services.audit import log_activity
from backend.app.services.user_notifications import create_notification

logger = logging.getLogger(__name__)


def _as_dict(value: Any) -> Dict[str, Any]:
    return {**value} if isinstance(value, dict) else {}


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return {**value}
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _candidate_name(candidate: Candidate) -> str:
    first = str(getattr(candidate, "first_name", "") or "").strip()
    last = str(getattr(candidate, "last_name", "") or "").strip()
    full = " ".join(x for x in [first, last] if x).strip()
    return full or str(getattr(candidate, "short_id", "") or getattr(candidate, "id", "") or "candidate")


def _candidate_status_url(candidate: Candidate) -> str | None:
    token = str(getattr(candidate, "status_share_token", None) or getattr(candidate, "intake_token", None) or "").strip()
    if not token:
        return None
    base_url = str(settings.frontend_url or "https://hostflow.cc").strip() or "https://hostflow.cc"
    return f"{base_url.rstrip('/')}/public/status/{token}"


def _candidate_intake_documents_url(candidate: Candidate, *, doc_type: str | None = None) -> str | None:
    token = str(getattr(candidate, "intake_token", None) or "").strip()
    if not token:
        return None
    base_url = str(settings.frontend_url or "https://hostflow.cc").strip() or "https://hostflow.cc"
    query: Dict[str, str] = {"mode": "documents"}
    if doc_type:
        query["doc"] = str(doc_type).strip()
    return f"{base_url.rstrip('/')}/public/apply/{token}?{urlencode(query)}"


def _candidate_tg_chat_id(candidate: Candidate) -> str | None:
    state = _as_dict(getattr(candidate, "intake_state", None))
    notifications = _as_dict(state.get("notifications"))
    telegram_state = _as_dict(notifications.get("telegram"))
    if not bool(telegram_state.get("subscribed", False)):
        return None
    chat_id = str(telegram_state.get("chat_id") or "").strip()
    return chat_id or None


def _telegram_cfg_from_account(account: CommunicationChannelAccount) -> TelegramBotConfig | None:
    settings_json = _as_dict(getattr(account, "settings_json", None))
    telegram_json = _as_dict(settings_json.get("telegram"))
    token = ""
    if telegram_json.get("bot_token_encrypted"):
        token = decrypt_secret(str(telegram_json.get("bot_token_encrypted") or "")) or ""
    elif telegram_json.get("bot_token"):
        token = str(telegram_json.get("bot_token") or "")
    token = token.strip()
    if not token:
        return None
    return TelegramBotConfig(bot_token=token, timeout_seconds=max(3, int(telegram_json.get("timeout_seconds") or 15)))


async def _tenant_telegram_cfg(db: AsyncSession, *, tenant_id: str) -> TelegramBotConfig | None:
    rows = (
        await db.execute(
            sa.select(CommunicationChannelAccount)
            .where(
                CommunicationChannelAccount.tenant_id == tenant_id,
                CommunicationChannelAccount.channel == "telegram",
                CommunicationChannelAccount.is_active.is_(True),
            )
            .order_by(sa.desc(CommunicationChannelAccount.updated_at))
            .limit(10)
        )
    ).scalars().all()
    for account in rows:
        cfg = _telegram_cfg_from_account(account)
        if cfg is not None:
            return cfg
    return None


async def send_candidate_stage_changed_telegram(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    old_stage: str | None,
    new_stage: str | None,
) -> bool:
    old_value = str(old_stage or "").strip()
    new_value = str(new_stage or "").strip()
    if not new_value or old_value == new_value:
        return False
    chat_id = _candidate_tg_chat_id(candidate)
    if not chat_id:
        return False
    cfg = await _tenant_telegram_cfg(db, tenant_id=tenant_id)
    if cfg is None:
        return False

    old_label = CANDIDATE_STAGE_LABELS.get(old_value, old_value) if old_value else "—"
    new_label = CANDIDATE_STAGE_LABELS.get(new_value, new_value)
    link = _candidate_status_url(candidate)
    lines = [
        f"Обновление по заявке {_candidate_name(candidate)}",
        f"Этап изменен: {old_label} -> {new_label}",
    ]
    if link:
        lines.append(f"Статус: {link}")
    try:
        await send_telegram_text(cfg, chat_id=chat_id, text="\n".join(lines))
        return True
    except Exception:
        logger.exception(
            "candidate telegram notify stage failed tenant=%s candidate=%s",
            tenant_id,
            getattr(candidate, "id", None),
        )
        return False


async def send_candidate_document_status_changed_telegram(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    document_type: str,
    old_status: str | None,
    new_status: str | None,
) -> bool:
    old_value = str(old_status or "").strip().lower()
    new_value = str(new_status or "").strip().lower()
    if not new_value or old_value == new_value:
        return False
    chat_id = _candidate_tg_chat_id(candidate)
    if not chat_id:
        return False
    cfg = await _tenant_telegram_cfg(db, tenant_id=tenant_id)
    if cfg is None:
        return False

    doc_label = get_document_display_name(str(document_type or "").strip() or "document")
    link = _candidate_status_url(candidate)
    lines = [
        f"Документ: {doc_label}",
        f"Статус изменен: {old_value or '—'} -> {new_value}",
    ]
    if link:
        lines.append(f"Подробнее: {link}")
    try:
        await send_telegram_text(cfg, chat_id=chat_id, text="\n".join(lines))
        return True
    except Exception:
        logger.exception(
            "candidate telegram notify document failed tenant=%s candidate=%s doc=%s",
            tenant_id,
            getattr(candidate, "id", None),
            document_type,
        )
        return False

def _candidate_owner_context_for_docs(candidate: Candidate) -> Dict[str, Any]:
    state = _as_dict(getattr(candidate, "intake_state", None))
    personal_state = _as_dict(state.get("personal"))
    extra_state = _as_dict(state.get("extra"))
    personal_data = _as_dict(getattr(candidate, "personal_data", None))
    extra_data = _json_dict(getattr(candidate, "extra", None))

    raw_docs = extra_state.get("documents")
    if not isinstance(raw_docs, dict):
        raw_docs = extra_data.get("documents")
    docs_ctx = {
        str(key): bool(value)
        for key, value in (raw_docs.items() if isinstance(raw_docs, dict) else [])
        if isinstance(value, bool)
    }

    has_adr = personal_state.get("has_adr")
    if has_adr is None:
        has_adr = extra_state.get("has_adr")
    if has_adr is None:
        has_adr = extra_data.get("has_adr")

    ctx: Dict[str, Any] = {
        "candidate_id": str(getattr(candidate, "id", "") or "").strip() or None,
        "citizenship": (
            personal_state.get("citizenship")
            or personal_data.get("citizenship")
            or extra_data.get("citizenship")
        ),
        "residency_status": (
            extra_state.get("poland_stay_basis")
            or extra_data.get("poland_stay_basis")
            or personal_state.get("residency_status")
            or personal_data.get("residency_status")
        ),
        "has_adr": has_adr if isinstance(has_adr, bool) else None,
        "documents": docs_ctx,
    }
    return {k: v for k, v in ctx.items() if v is not None}


def _format_bullets(items: list[str], *, limit: int = 3) -> list[str]:
    labels = [str(get_document_display_name(item) or item) for item in items]
    lines = [f"• {label}" for label in labels[:limit]]
    remaining = len(labels) - limit
    if remaining > 0:
        lines.append(f"• +{remaining} еще")
    return lines


async def get_candidate_required_docs_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> Dict[str, Any]:
    oc = getattr(candidate, "own_company_id", None)
    own_company_id = str(oc).strip() if oc else None
    ruleset_version = await ensure_ruleset_seed(
        db,
        str(tenant_id),
        load_default_ruleset(),
        own_company_id=own_company_id,
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)
    owner_context = _candidate_owner_context_for_docs(candidate)
    docs = await list_candidate_documents(
        db,
        str(tenant_id),
        str(candidate.id),
        include_deleted=False,
        active_own_company_id=own_company_id,
    )
    docs_payload: list[dict[str, Any]] = []
    for doc in docs:
        expire_date = getattr(doc, "expire_date", None)
        docs_payload.append(
            {
                "type": str(doc.doc_type or "").strip(),
                "doc_type": str(doc.doc_type or "").strip(),
                "status": doc.status.value
                if hasattr(doc.status, "value")
                else str(doc.status or "").strip().lower(),
                "expires_at": expire_date.isoformat() if expire_date is not None else None,
            }
        )
    summary = compute_owner_summary(owner_context, ruleset_payload, docs_payload)
    required = _as_dict(summary.get("required"))
    total = int(required.get("total") or 0)
    ready = int(required.get("ready") or 0)
    missing = [str(item) for item in (required.get("missing") or []) if str(item or "").strip()]
    in_progress = [str(item) for item in (required.get("in_progress_types") or []) if str(item or "").strip()]
    problematic = [str(item) for item in (required.get("problematic") or []) if str(item or "").strip()]
    next_doc = missing[0] if missing else (in_progress[0] if in_progress else (problematic[0] if problematic else None))
    return {
        "total": total,
        "ready": ready,
        "missing": missing,
        "in_progress": in_progress,
        "problematic": problematic,
        "next_doc_type": next_doc,
        "docs_count": len(docs_payload),
    }


async def sync_candidate_ready_for_handoff_gate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    source: str,
) -> bool:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    completed_at = _parse_dt(runtime.get("completed_at")) or _parse_dt(getattr(candidate, "intake_submitted_at", None))
    if completed_at is None:
        intake_status = str(getattr(candidate, "intake_status", "") or "").strip().lower()
        if intake_status not in {"submitted", "completed"}:
            return False

    snapshot = await get_candidate_required_docs_snapshot(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )
    total = int(snapshot.get("total") or 0)
    ready = int(snapshot.get("ready") or 0)
    if total <= 0 or ready < total:
        return False

    current_stage = str(getattr(candidate, "stage", "") or "").strip().lower()
    if current_stage == "ready_for_handoff":
        return False

    now = datetime.now(timezone.utc)
    prev_stage = str(getattr(candidate, "stage", "") or "").strip() or None
    candidate.stage = "ready_for_handoff"
    candidate.status = "ready_for_handoff"
    runtime["auto_ready_for_handoff_at"] = now.isoformat()
    runtime["auto_ready_for_handoff_source"] = str(source or "").strip() or "system"
    state["telegram_intake"] = runtime
    candidate.intake_state = state

    db.add(
        CandidateStageHistory(
            id=str(uuid4()),
            tenant_id=str(tenant_id),
            candidate_id=str(candidate.id),
            from_code=prev_stage,
            to_code="ready_for_handoff",
            reason="auto_gate_docs_complete",
            actor="system",
            at=now,
        )
    )
    await log_activity(
        db,
        tenant_id=str(tenant_id),
        action="candidate_auto_ready_for_handoff",
        actor_id=None,
        target_type="candidate",
        target_id=str(candidate.id),
        payload={
            "source": str(source or "").strip() or "system",
            "from_stage": prev_stage,
            "to_stage": "ready_for_handoff",
            "required_docs_total": total,
            "required_docs_ready": ready,
        },
    )
    manager_id = str(getattr(candidate, "manager", "") or "").strip() or None
    if manager_id:
        await create_notification(
            db,
            tenant_id=str(tenant_id),
            user_id=manager_id,
            event_type="candidate_ready_for_handoff_auto",
            entity_type="candidate",
            entity_id=str(candidate.id),
            payload={
                "type": "candidate_ready_for_handoff_auto",
                "source": "candidate_pipeline",
                "severity": "high",
                "requires_action": True,
                "title": "Кандидат готов к передаче",
                "description": (
                    f"Кандидат {_candidate_name(candidate)} автоматически переведен в 'Готов к передаче'."
                ),
                "candidate_id": str(candidate.id),
                "to_stage": "ready_for_handoff",
                "dedupe_key": f"candidate_ready_for_handoff_auto:{tenant_id}:{manager_id}:{candidate.id}",
            },
            dedupe_window_minutes=60 * 24 * 30,
        )
    await db.flush()
    return True


async def send_candidate_documents_progress_telegram(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    source_doc_type: str | None = None,
) -> bool:
    chat_id = _candidate_tg_chat_id(candidate)
    if not chat_id:
        return False
    cfg = await _tenant_telegram_cfg(db, tenant_id=tenant_id)
    if cfg is None:
        return False

    try:
        snapshot = await get_candidate_required_docs_snapshot(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
        )
        total = int(snapshot.get("total") or 0)
        ready = int(snapshot.get("ready") or 0)
        missing = [str(item) for item in (snapshot.get("missing") or []) if str(item or "").strip()]
        in_progress = [str(item) for item in (snapshot.get("in_progress") or []) if str(item or "").strip()]
        problematic = [str(item) for item in (snapshot.get("problematic") or []) if str(item or "").strip()]

        lines: list[str] = ["Документы обновлены."]
        if source_doc_type:
            lines.append(f"Загружен: {get_document_display_name(str(source_doc_type))}")
        if total > 0:
            lines.append(f"Прогресс обязательных: {ready}/{total}")
            if missing:
                lines.append("Осталось загрузить:")
                lines.extend(_format_bullets(missing))
        next_doc = str(snapshot.get("next_doc_type") or "").strip() or None
        docs_url = _candidate_intake_documents_url(candidate, doc_type=next_doc)
        if docs_url:
            if next_doc:
                lines.append(f"Загрузка следующего документа на сайте: {docs_url}")
            else:
                lines.append(f"Загрузка документов на сайте: {docs_url}")
        status_url = _candidate_status_url(candidate)
        if status_url:
            lines.append(f"Статус: {status_url}")
        await send_telegram_text(cfg, chat_id=chat_id, text="\n".join(lines))
        return True
    except Exception:
        logger.exception(
            "candidate telegram notify docs-progress failed tenant=%s candidate=%s",
            tenant_id,
            getattr(candidate, "id", None),
        )
        return False


async def send_candidate_documents_deadline_nudge_telegram(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    hours_since_ready: int,
) -> bool:
    chat_id = _candidate_tg_chat_id(candidate)
    if not chat_id:
        return False
    cfg = await _tenant_telegram_cfg(db, tenant_id=tenant_id)
    if cfg is None:
        return False
    try:
        snapshot = await get_candidate_required_docs_snapshot(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
        )
        total = int(snapshot.get("total") or 0)
        ready = int(snapshot.get("ready") or 0)
        missing = [str(item) for item in (snapshot.get("missing") or []) if str(item or "").strip()]
        if total <= 0 or ready >= total or not missing:
            return False
        next_doc = str(snapshot.get("next_doc_type") or "").strip() or missing[0]
        lines = [
            f"Напоминание: по заявке {_candidate_name(candidate)} не хватает документов.",
            f"Прогресс обязательных: {ready}/{total}",
            f"Прошло примерно {max(1, int(hours_since_ready))} ч. после завершения анкеты.",
            "Осталось загрузить:",
        ]
        lines.extend(_format_bullets(missing))
        lines.append(f"Быстрый шаг: /scan {next_doc}")
        docs_url = _candidate_intake_documents_url(candidate, doc_type=next_doc)
        if docs_url:
            lines.append(f"Загрузка на сайте: {docs_url}")
        status_url = _candidate_status_url(candidate)
        if status_url:
            lines.append(f"Статус: {status_url}")
        await send_telegram_text(cfg, chat_id=chat_id, text="\n".join(lines))
        return True
    except Exception:
        logger.exception(
            "candidate telegram notify docs-deadline failed tenant=%s candidate=%s",
            tenant_id,
            getattr(candidate, "id", None),
        )
        return False
