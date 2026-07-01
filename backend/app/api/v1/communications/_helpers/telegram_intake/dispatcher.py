"""Sub-module of telegram_intake (Phase 1 god-module split, step 8/N)."""

from __future__ import annotations

import logging
from typing import Any, Dict

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.stages import LABELS as CANDIDATE_STAGE_LABELS
from backend.app.core.settings import settings
from backend.app.models.communication import (
    CommunicationChannelAccount,
)
from backend.app.models.document import Document
from backend.app.models.vacancy import Vacancy

from ..candidate_lookup import (
    _candidate_apply_url,
    _candidate_email_options,
    _candidate_name,
    _candidate_public_status_url,
    _find_candidate_by_bind_token,
    _find_candidate_by_telegram_chat,
    _find_candidates_by_contact,
)
from ..channels import _telegram_config_from_account_settings
from ..utils import (
    _as_dict,
    _coerce_datetime,
    _is_six_digit_code,
    _looks_like_phone,
    _normalize_email_value,
    _now_utc,
)
from .ui_text import (
    _send_candidate_telegram_reply,
    _telegram_docs_summary_text,
    _telegram_extract_command,
    _telegram_help_text,
    _telegram_onboarding_text,
    _telegram_otp_hash,
    _telegram_vacancies_text,
)
from .intake_state import (
    _tg_intake_help_text,
    _tg_intake_progress_text,
    _tg_intake_skipped_text,
    _tg_process_intake_answer,
    _tg_reset_intake_runtime,
    _tg_skip_intake_step,
    _tg_start_or_resume_intake,
    _tg_unskip_intake_step,
)
from .candidate_link import (
    _create_candidate_from_telegram_intake,
    _find_candidate_by_pending_verification,
    _link_candidate_to_telegram_chat,
    _send_telegram_link_code,
)
from .docs_bridge import (
    _ensure_candidate_intake_token,
    _telegram_docs_checklist_text,
    _telegram_scan_command_text,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 5. Main command dispatcher (called from the telegram webhook routes).
# ---------------------------------------------------------------------------


async def _process_public_telegram_candidate_command(
    db: AsyncSession,
    *,
    account: CommunicationChannelAccount,
    tenant_id: str,
    normalized: Dict[str, Any],
) -> tuple[bool, str | None]:
    text = normalized.get("text")
    text_str = str(text or "").strip() if isinstance(text, str) else ""
    parsed = _telegram_extract_command(text_str)
    cmd = ""
    args: list[str] = []
    if parsed:
        cmd, args = parsed

    chat_id = str(normalized.get("provider_chat_ref") or "").strip()
    if not chat_id:
        return False, None
    cfg = _telegram_config_from_account_settings(account)
    if cfg is None:
        return False, None

    payload_data = _as_dict(normalized.get("payload"))
    username = str(payload_data.get("telegram_username") or "").strip() or None
    sender_label = str(normalized.get("sender_label") or "").strip() or None
    sender_address = str(normalized.get("sender_address") or "").strip() or None
    contact_phone = (
        str(payload_data.get("telegram_contact_phone") or "").strip() or None
    )
    now_iso = _now_utc().isoformat()
    reply = ""
    linked_candidate_id: str | None = None

    linked_candidate = await _find_candidate_by_telegram_chat(
        db, tenant_id=tenant_id, chat_id=chat_id
    )
    if linked_candidate is not None:
        linked_candidate_id = str(linked_candidate.id)

    # Non-command input: support OTP and contact-based linking.
    if not parsed:
        if linked_candidate is not None:
            intake_reply = await _tg_process_intake_answer(
                db,
                tenant_id=tenant_id,
                candidate=linked_candidate,
                text=text_str,
            )
            if intake_reply:
                reply = intake_reply
                linked_candidate_id = str(linked_candidate.id)

        if text_str.lower() in {"связаться с менеджером", "manager", "contact manager"}:
            if linked_candidate is not None:
                reply = "Сообщение передано менеджеру. Ответ придет в этот чат."
                linked_candidate_id = str(linked_candidate.id)
            else:
                reply = "Напишите коротко ваш вопрос. Менеджер подключится к диалогу."

        if linked_candidate is None and not reply:
            if _is_six_digit_code(text_str):
                pending_candidate = await _find_candidate_by_pending_verification(
                    db, tenant_id=tenant_id, chat_id=chat_id
                )
                if pending_candidate is not None:
                    state = _as_dict(pending_candidate.intake_state)
                    notifications = _as_dict(state.get("notifications"))
                    tg = _as_dict(notifications.get("telegram"))
                    pending = _as_dict(tg.get("link_verification"))
                    expires_at = _coerce_datetime(pending.get("expires_at"))
                    if expires_at is not None and expires_at < _now_utc():
                        tg.pop("link_verification", None)
                        notifications["telegram"] = tg
                        state["notifications"] = notifications
                        pending_candidate.intake_state = state
                        await db.commit()
                        reply = (
                            "Код истек. Отправьте email или телефон повторно, "
                            "чтобы получить новый код."
                        )
                    else:
                        attempts = int(pending.get("attempts") or 0)
                        if attempts >= 5:
                            tg.pop("link_verification", None)
                            notifications["telegram"] = tg
                            state["notifications"] = notifications
                            pending_candidate.intake_state = state
                            await db.commit()
                            reply = (
                                "Слишком много попыток. "
                                "Запросите новый код по email или телефону."
                            )
                        else:
                            expected_hash = str(pending.get("code_hash") or "")
                            if expected_hash and expected_hash == _telegram_otp_hash(
                                chat_id=chat_id, code=text_str
                            ):
                                await _link_candidate_to_telegram_chat(
                                    db,
                                    tenant_id=tenant_id,
                                    chat_id=chat_id,
                                    candidate=pending_candidate,
                                    username=username,
                                )
                                await db.commit()
                                linked_candidate_id = str(pending_candidate.id)
                                reply = (
                                    f"Готово. Профиль {_candidate_name(pending_candidate)} "
                                    f"привязан.\n"
                                    "Теперь доступны /status, /docs и /subscribe."
                                )
                            else:
                                pending["attempts"] = attempts + 1
                                tg["link_verification"] = pending
                                notifications["telegram"] = tg
                                state["notifications"] = notifications
                                pending_candidate.intake_state = state
                                await db.commit()
                                reply = "Неверный код. Проверьте email и попробуйте снова."
                else:
                    reply = "Сначала отправьте email или номер телефона, чтобы получить код."
            elif _normalize_email_value(text_str) or _looks_like_phone(text_str):
                matches = await _find_candidates_by_contact(
                    db, tenant_id=tenant_id, contact_input=text_str
                )
                if not matches:
                    reply = _telegram_onboarding_text()
                elif len(matches) > 1:
                    reply = (
                        "Найдено несколько кандидатов. Для точной привязки отправьте email, "
                        "который указан в анкете."
                    )
                else:
                    candidate = matches[0]
                    email_opts = sorted(_candidate_email_options(candidate))
                    email_to = email_opts[0] if email_opts else None
                    if not email_to:
                        reply = (
                            "Для этого профиля не найден email. Напишите менеджеру в этот чат, "
                            "мы поможем с привязкой."
                        )
                    else:
                        ok, msg = await _send_telegram_link_code(
                            db,
                            tenant_id=tenant_id,
                            chat_id=chat_id,
                            username=username,
                            candidate=candidate,
                            email_to=email_to,
                        )
                        reply = msg
            else:
                if text_str.lower() in {"привязать профиль", "bind", "link"}:
                    reply = "Отправьте email или номер телефона, который вы указывали в анкете."
                else:
                    reply = _telegram_onboarding_text()

        if reply:
            try:
                await _send_candidate_telegram_reply(
                    cfg=cfg,
                    chat_id=chat_id,
                    text=reply,
                    linked=bool(linked_candidate_id),
                )
            except Exception:
                logger.exception(
                    "communications telegram command reply failed tenant=%s account=%s command=%s",
                    tenant_id,
                    account.id,
                    "non_command",
                )
            return True, linked_candidate_id
        return False, linked_candidate_id

    if cmd not in {
        "start",
        "help",
        "bind",
        "status",
        "intake",
        "docs",
        "scan",
        "subscribe",
        "unsubscribe",
        "lang",
        "vacancies",
        "apply",
    }:
        return False, linked_candidate_id

    if cmd in {"start", "help"}:
        reply = f"{_telegram_onboarding_text()}\n\n{_telegram_help_text()}"
    elif cmd == "bind":
        bind_value = str(args[0] if args else "").strip()
        if not bind_value:
            reply = "Отправьте `/bind <email или телефон>` или просто напишите email/телефон в чат."
        else:
            if _normalize_email_value(bind_value) or _looks_like_phone(bind_value):
                matches = await _find_candidates_by_contact(
                    db, tenant_id=tenant_id, contact_input=bind_value
                )
                if not matches:
                    reply = _telegram_onboarding_text()
                elif len(matches) > 1:
                    reply = (
                        "Найдено несколько профилей. "
                        "Отправьте email из анкеты для точной привязки."
                    )
                else:
                    candidate = matches[0]
                    email_opts = sorted(_candidate_email_options(candidate))
                    email_to = email_opts[0] if email_opts else None
                    if not email_to:
                        reply = (
                            "У кандидата не найден email. "
                            "Напишите менеджеру, и мы поможем с привязкой."
                        )
                    else:
                        ok, msg = await _send_telegram_link_code(
                            db,
                            tenant_id=tenant_id,
                            chat_id=chat_id,
                            username=username,
                            candidate=candidate,
                            email_to=email_to,
                        )
                        reply = msg
            else:
                candidate = await _find_candidate_by_bind_token(
                    db, tenant_id=tenant_id, token=bind_value
                )
                if candidate is None:
                    reply = "Кандидат не найден. Используйте email/телефон или проверьте токен."
                else:
                    await _link_candidate_to_telegram_chat(
                        db,
                        tenant_id=tenant_id,
                        chat_id=chat_id,
                        candidate=candidate,
                        username=username,
                    )
                    await db.commit()
                    linked_candidate_id = str(candidate.id)
                    reply = (
                        f"Готово. Telegram привязан к кандидату {_candidate_name(candidate)}.\n"
                        "Теперь доступны /status и /docs."
                    )
    elif cmd == "vacancies":
        rows = (
            await db.execute(
                sa.select(Vacancy)
                .where(
                    Vacancy.tenant_id == tenant_id,
                    Vacancy.is_active.is_(True),
                    Vacancy.is_archived.is_(False),
                )
                .order_by(sa.desc(Vacancy.updated_at))
                .limit(5)
            )
        ).scalars().all()
        reply = _telegram_vacancies_text(rows)
    elif cmd == "apply":
        if linked_candidate is not None:
            link = _candidate_apply_url(linked_candidate)
            reply = f"Ваша анкета: {link}" if link else "Анкета недоступна. Напишите менеджеру."
        else:
            base_url = (
                str(settings.frontend_url or "https://hostflow.cc").strip()
                or "https://hostflow.cc"
            )
            reply = f"Заполнить анкету: {base_url.rstrip('/')}/public/intake"
    elif cmd in {"status", "intake", "docs", "scan", "subscribe", "unsubscribe", "lang"}:
        candidate = linked_candidate
        if candidate is None and cmd == "intake":
            try:
                candidate = await _create_candidate_from_telegram_intake(
                    db,
                    tenant_id=tenant_id,
                    chat_id=chat_id,
                    username=username,
                    sender_label=sender_label,
                    sender_address=sender_address,
                    contact_phone=contact_phone,
                )
                linked_candidate = candidate
                linked_candidate_id = str(candidate.id)
            except Exception:
                logger.exception(
                    "telegram intake candidate bootstrap failed tenant=%s chat=%s",
                    tenant_id,
                    chat_id,
                )
                reply = "Не удалось начать анкету. Попробуйте еще раз или используйте /apply."
        if candidate is None:
            reply = (
                "Профиль не найден. Вы можете:\n"
                "• начать новую анкету в Telegram: /intake\n"
                "• заполнить анкету на сайте: /apply\n"
                "• привязать существующий профиль: /bind <email|phone>"
            )
        else:
            linked_candidate_id = str(candidate.id)
            if cmd == "status":
                stage = str(getattr(candidate, "stage", "") or "").strip()
                stage_label = (
                    CANDIDATE_STAGE_LABELS.get(stage, stage) if stage else "—"
                )
                status_value = (
                    str(getattr(candidate, "status", "") or "").strip() or stage or "—"
                )
                status_link = _candidate_public_status_url(candidate)
                lines = [
                    f"Кандидат: {_candidate_name(candidate)}",
                    f"Этап: {stage_label}" if stage else "Этап: —",
                    f"Статус: {status_value}",
                ]
                if status_link:
                    lines.append(f"Публичная страница: {status_link}")
                reply = "\n".join(lines)
            elif cmd == "intake":
                mode = str(args[0] if args else "").strip().lower()
                if mode in {"help", "commands"}:
                    reply = _tg_intake_help_text()
                elif mode in {"status", "progress"}:
                    reply = _tg_intake_progress_text(candidate)
                elif mode == "skipped":
                    reply = _tg_intake_skipped_text(candidate)
                elif mode == "reset":
                    reply = await _tg_reset_intake_runtime(
                        db,
                        candidate=candidate,
                        chat_id=chat_id,
                        username=username,
                    )
                elif mode == "skip":
                    reply = await _tg_skip_intake_step(
                        db,
                        candidate=candidate,
                        chat_id=chat_id,
                        username=username,
                    )
                elif mode == "unskip":
                    reply = await _tg_unskip_intake_step(
                        db,
                        candidate=candidate,
                        chat_id=chat_id,
                        username=username,
                        target_step=str(args[1] if len(args) > 1 else "").strip() or None,
                    )
                else:
                    reply = await _tg_start_or_resume_intake(
                        db,
                        candidate=candidate,
                        chat_id=chat_id,
                        username=username,
                    )
            elif cmd == "docs":
                try:
                    reply = await _telegram_docs_checklist_text(
                        db,
                        tenant_id=tenant_id,
                        candidate=candidate,
                    )
                except Exception:
                    logger.exception(
                        "communications telegram docs summary failed tenant=%s candidate=%s",
                        tenant_id,
                        getattr(candidate, "id", None),
                    )
                    rows = (
                        await db.execute(
                            sa.select(Document.status, sa.func.count())
                            .where(
                                Document.tenant_id == tenant_id,
                                Document.candidate_id == str(candidate.id),
                                Document.deleted_at.is_(None),
                            )
                            .group_by(Document.status)
                        )
                    ).all()
                    reply = _telegram_docs_summary_text(rows)
            elif cmd == "scan":
                if _ensure_candidate_intake_token(candidate):
                    await db.commit()
                requested_doc = str(args[0] if args else "").strip() or None
                try:
                    reply = await _telegram_scan_command_text(
                        db,
                        tenant_id=tenant_id,
                        candidate=candidate,
                        requested_doc_type=requested_doc,
                    )
                except Exception:
                    logger.exception(
                        "communications telegram scan link failed tenant=%s candidate=%s",
                        tenant_id,
                        getattr(candidate, "id", None),
                    )
                    apply = _candidate_apply_url(candidate)
                    if apply:
                        reply = f"Откройте анкету и загрузите документы: {apply}"
                    else:
                        reply = "Сканер временно недоступен. Попробуйте позже."
            elif cmd in {"subscribe", "unsubscribe"}:
                state = _as_dict(candidate.intake_state)
                notifications = _as_dict(state.get("notifications"))
                telegram_state = _as_dict(notifications.get("telegram"))
                telegram_state["chat_id"] = chat_id
                telegram_state["subscribed"] = cmd == "subscribe"
                telegram_state["updated_at"] = now_iso
                if username:
                    telegram_state["username"] = username
                notifications["telegram"] = telegram_state
                state["notifications"] = notifications
                candidate.intake_state = state
                await db.commit()
                reply = (
                    "Уведомления в Telegram включены."
                    if cmd == "subscribe"
                    else "Уведомления в Telegram отключены."
                )
            elif cmd == "lang":
                language = str(args[0] if args else "").strip().lower()
                if language not in {"ru", "en", "pl", "uk"}:
                    reply = "Поддерживаемые языки: ru, en, pl, uk. Пример: /lang pl"
                else:
                    state = _as_dict(candidate.intake_state)
                    notifications = _as_dict(state.get("notifications"))
                    telegram_state = _as_dict(notifications.get("telegram"))
                    telegram_state["chat_id"] = chat_id
                    telegram_state["language"] = language
                    telegram_state["updated_at"] = now_iso
                    if username:
                        telegram_state["username"] = username
                    notifications["telegram"] = telegram_state
                    state["notifications"] = notifications
                    candidate.intake_state = state
                    await db.commit()
                    reply = f"Язык уведомлений обновлен: {language.upper()}."

    if reply:
        try:
            await _send_candidate_telegram_reply(
                cfg=cfg,
                chat_id=chat_id,
                text=reply,
                linked=bool(linked_candidate_id),
            )
        except Exception:
            logger.exception(
                "communications telegram command reply failed tenant=%s account=%s command=%s",
                tenant_id,
                account.id,
                cmd,
            )
    return True, linked_candidate_id
