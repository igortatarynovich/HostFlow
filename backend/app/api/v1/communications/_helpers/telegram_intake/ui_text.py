"""Sub-module of telegram_intake (Phase 1 god-module split, step 8/N)."""

from __future__ import annotations

import hashlib
from typing import Any, Dict

from backend.app.core.settings import settings
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.services.candidate_notifications import get_document_display_name
from backend.app.services.communications_telegram import (
    TelegramBotConfig,
    send_telegram_text,
)

from ..utils import (
    _as_dict,
    _json_dict,
)


# ---------------------------------------------------------------------------
# 1. Pure text / keyboard helpers (no DB, no state mutation).
# ---------------------------------------------------------------------------


def _telegram_extract_command(text: str | None) -> tuple[str, list[str]] | None:
    raw = str(text or "").strip()
    if not raw.startswith("/"):
        return None
    line = raw.splitlines()[0].strip()
    parts = [str(p).strip() for p in line.split(" ") if str(p).strip()]
    if not parts:
        return None
    cmd = parts[0][1:].split("@", 1)[0].strip().lower()
    if not cmd:
        return None
    return cmd, parts[1:]


def _telegram_otp_hash(*, chat_id: str, code: str) -> str:
    payload = f"{chat_id}:{code}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _telegram_onboarding_text() -> str:
    base_url = (
        str(settings.frontend_url or "https://hostflow.cc").strip()
        or "https://hostflow.cc"
    )
    return (
        "Два способа заполнения:\n"
        "1) На сайте: /apply\n"
        "2) Прямо в Telegram: /intake\n\n"
        "Привязка /bind нужна только если профиль уже существует в CRM.\n"
        f"Портал статуса: {base_url.rstrip('/')}/public/portal\n"
        "Если нужна помощь, напишите сообщение менеджеру в этом чате."
    )


def _candidate_verification_email_body(*, candidate_name: str, code: str) -> str:
    return (
        f"Здравствуйте, {candidate_name}!\n\n"
        "Код подтверждения для привязки Telegram к вашей заявке:\n"
        f"{code}\n\n"
        "Код действует 10 минут."
    )


def _telegram_name_parts(
    sender_label: str | None, username: str | None
) -> tuple[str, str]:
    raw = str(sender_label or "").strip()
    if raw and not raw.startswith("@"):
        parts = [p for p in raw.split() if p]
        if len(parts) >= 2:
            return parts[0][:80], " ".join(parts[1:])[:120]
        if len(parts) == 1:
            return parts[0][:80], "Telegram"
    user = str(username or "").strip()
    if user:
        return user[:80], "Telegram"
    return "Telegram", "Candidate"


def _telegram_vacancies_text(vacancies: list[Vacancy]) -> str:
    if not vacancies:
        return (
            "Сейчас нет активных вакансий. "
            "Напишите менеджеру, и мы подберем предложение."
        )
    lines = ["Активные вакансии:"]
    for idx, vacancy in enumerate(vacancies[:5], start=1):
        title = str(getattr(vacancy, "title", "") or "Vacancy").strip()
        location = str(getattr(vacancy, "location", "") or "").strip()
        if location:
            lines.append(f"{idx}. {title} ({location})")
        else:
            lines.append(f"{idx}. {title}")
    lines.append("Если интересно, напишите сообщение и менеджер свяжется с вами.")
    return "\n".join(lines)


def _telegram_keyboard(linked: bool) -> Dict[str, Any]:
    if linked:
        rows = [
            [{"text": "/status"}, {"text": "/docs"}],
            [{"text": "/intake"}, {"text": "/apply"}],
            [{"text": "/scan"}, {"text": "/vacancies"}],
            [{"text": "/subscribe"}, {"text": "/unsubscribe"}],
            [{"text": "Связаться с менеджером"}],
        ]
    else:
        rows = [
            [{"text": "/intake"}, {"text": "/apply"}],
            [{"text": "Привязать профиль"}, {"text": "/bind"}],
            [{"text": "Поделиться номером", "request_contact": True}],
            [{"text": "/vacancies"}, {"text": "Связаться с менеджером"}],
        ]
    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


async def _send_candidate_telegram_reply(
    *,
    cfg: TelegramBotConfig,
    chat_id: str,
    text: str,
    linked: bool,
) -> None:
    await send_telegram_text(
        cfg,
        chat_id=chat_id,
        text=text,
        reply_markup=_telegram_keyboard(linked),
    )


def _telegram_help_text() -> str:
    return (
        "Доступные команды:\n"
        "/intake - заполнить анкету в Telegram (создаст профиль, если его еще нет)\n"
        "/apply - заполнить анкету на сайте\n"
        "/bind <token|email|phone> - привязать Telegram к уже существующему профилю\n"
        "/status - текущий этап и статус заявки\n"
        "/intake help - команды анкеты\n"
        "/intake status - показать прогресс анкеты\n"
        "/intake skipped - показать пропущенные опциональные шаги\n"
        "/intake reset - сбросить текущий шаг анкеты и начать с актуального места\n"
        "/intake skip - пропустить текущий шаг (только если шаг опциональный)\n"
        "/intake unskip [step|number] - вернуть пропущенный опциональный шаг в анкету\n"
        "/docs - сводка по документам\n"
        "/scan [doc_type] - ссылка на загрузку документов на сайте\n"
        "/subscribe - подписаться на уведомления в Telegram\n"
        "/unsubscribe - отключить уведомления в Telegram\n"
        "/lang <ru|en|pl|uk> - язык уведомлений\n"
        "/vacancies - активные вакансии\n"
        "/help - показать список команд"
    )


def _telegram_docs_summary_text(rows: list[tuple[Any, int]]) -> str:
    if not rows:
        return "По вашему профилю пока нет документов."
    by_status: Dict[str, int] = {}
    total = 0
    for raw_status, cnt in rows:
        if hasattr(raw_status, "value"):
            key = str(getattr(raw_status, "value") or "").strip().lower()
        else:
            key = str(raw_status or "").strip().lower()
        if not key:
            key = "unknown"
        amount = int(cnt or 0)
        by_status[key] = int(by_status.get(key) or 0) + amount
        total += amount
    ordered = [
        "missing",
        "requested",
        "in_progress",
        "submitted",
        "received",
        "approved",
        "completed",
        "rejected",
        "expired",
    ]
    all_keys = ordered + [k for k in by_status.keys() if k not in ordered]
    lines: list[str] = [f"Документы: всего {total}"]
    for key in all_keys:
        if key in by_status:
            lines.append(f"• {key}: {by_status[key]}")
    return "\n".join(lines)


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


def _format_doc_types_bullets(items: list[str], *, limit: int = 5) -> list[str]:
    if not items:
        return []
    labels = [str(get_document_display_name(code) or code) for code in items]
    lines = [f"• {label}" for label in labels[:limit]]
    remaining = len(labels) - limit
    if remaining > 0:
        lines.append(f"• +{remaining} еще")
    return lines
