"""Sub-module of telegram_intake (Phase 1 god-module split, step 8/N)."""

from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.services.audit import log_activity
from backend.app.services.candidate_telegram_notifications import (
    sync_candidate_ready_for_handoff_gate,
)
from backend.app.services.integration_inbound_normalization import (
    normalize_inbound_citizenship_alpha2,
)

from ..utils import (
    _as_dict,
    _json_dict,
    _now_utc,
)
from .docs_bridge import (
    _ensure_candidate_intake_token,
    _tg_intake_completion_docs_text,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 2. Intake state-machine constants + helpers.
# ---------------------------------------------------------------------------


_TG_INTL_BOOL_TRUE = {"yes", "y", "true", "1", "да", "д", "есть", "ok", "ага"}
_TG_INTL_BOOL_FALSE = {"no", "n", "false", "0", "нет", "н", "не", "none"}
_TG_INTAKE_STEP_ORDER: list[str] = [
    "full_name",
    "birth_date",
    "citizenship",
    "years_ce",
    "intl_experience",
    "has_adr",
    "agreement_general",
]
_TG_INTAKE_OPTIONAL_STEPS: set[str] = {
    "intl_experience",
    "has_adr",
}


def _tg_answer_yes_no(value: str) -> bool | None:
    normalized = str(value or "").strip().lower()
    if normalized in _TG_INTL_BOOL_TRUE:
        return True
    if normalized in _TG_INTL_BOOL_FALSE:
        return False
    return None


def _tg_get_intake_sections(
    candidate: Candidate,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    state = _as_dict(getattr(candidate, "intake_state", None))
    contacts = _as_dict(state.get("contacts"))
    personal = _as_dict(state.get("personal"))
    experience = _as_dict(state.get("experience"))
    agreements = _as_dict(state.get("agreements"))
    runtime = _as_dict(state.get("telegram_intake"))
    return contacts, personal, experience, agreements, runtime


def _tg_incomplete_steps(candidate: Candidate) -> list[str]:
    _, personal, experience, agreements, runtime = _tg_get_intake_sections(candidate)
    skipped_steps_raw = runtime.get("skipped_steps")
    skipped_steps = {
        str(item).strip()
        for item in (skipped_steps_raw if isinstance(skipped_steps_raw, list) else [])
        if str(item).strip()
    }
    name_ready = bool(
        str(getattr(candidate, "first_name", "") or "").strip()
        and str(getattr(candidate, "last_name", "") or "").strip()
    )
    if not name_ready:
        full_name_state = str(personal.get("full_name") or "").strip()
        name_ready = bool(full_name_state and len(full_name_state.split()) >= 2)
    checks: Dict[str, bool] = {
        "full_name": name_ready,
        "birth_date": bool(str(personal.get("birth_date") or "").strip()),
        "citizenship": len(str(personal.get("citizenship") or "").strip()) == 2,
        "years_ce": isinstance(experience.get("years_ce"), int),
        "intl_experience": isinstance(experience.get("intl_experience"), bool),
        "has_adr": isinstance(personal.get("has_adr"), bool),
        "agreement_general": bool(agreements.get("general") is True),
    }
    return [
        step
        for step in _TG_INTAKE_STEP_ORDER
        if not checks.get(step)
        and not (step in _TG_INTAKE_OPTIONAL_STEPS and step in skipped_steps)
    ]


def _tg_step_prompt(step: str, *, index: int, total: int) -> str:
    prefix = f"Анкета {index}/{total}\n"
    prompts: Dict[str, str] = {
        "full_name": "Введите имя и фамилию (например: Jan Kowalski).",
        "birth_date": "Дата рождения: YYYY-MM-DD (например 1990-05-17).",
        "citizenship": "Гражданство: 2 буквы кода страны (например PL, UA, BY).",
        "years_ce": "Сколько лет опыта по категории CE? (целое число от 0 до 40).",
        "intl_experience": "Есть международный опыт перевозок? Ответьте: да/нет.",
        "has_adr": "Есть ADR? Ответьте: да/нет.",
        "agreement_general": "Подтверждаете согласие на обработку данных? Ответьте: да/нет.",
    }
    return f"{prefix}{prompts.get(step) or 'Введите ответ.'}"


def _tg_step_label(step: str) -> str:
    labels: Dict[str, str] = {
        "full_name": "Имя и фамилия",
        "birth_date": "Дата рождения",
        "citizenship": "Гражданство",
        "years_ce": "Опыт CE (лет)",
        "intl_experience": "Международный опыт",
        "has_adr": "Наличие ADR",
        "agreement_general": "Согласие на обработку данных",
    }
    return labels.get(step) or step


def _tg_intake_progress_text(candidate: Candidate) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    skipped = {
        str(item).strip()
        for item in (
            runtime.get("skipped_steps")
            if isinstance(runtime.get("skipped_steps"), list)
            else []
        )
        if str(item).strip()
    }
    missing = _tg_incomplete_steps(candidate)
    total = len(_TG_INTAKE_STEP_ORDER)
    done = max(0, total - len(missing))
    if not missing:
        return (
            "Анкета заполнена: 7/7. "
            "Следующий шаг: /docs и загрузка документов на сайте (/scan)."
        )
    current = str(runtime.get("current_step") or "").strip()
    if current not in missing:
        current = missing[0]
    lines = [
        f"Прогресс анкеты: {done}/{total}",
        f"Текущий шаг: {_tg_step_label(current)}",
        "Осталось:",
    ]
    for step in missing[:4]:
        lines.append(f"• {_tg_step_label(step)}")
    if len(missing) > 4:
        lines.append(f"• +{len(missing) - 4} еще")
    if skipped:
        lines.append(f"Пропущено опционально: {len(skipped)}")
        ordered_skipped = [step for step in _TG_INTAKE_STEP_ORDER if step in skipped]
        if ordered_skipped:
            lines.append("Можно вернуть командой:")
            for idx, step in enumerate(ordered_skipped, start=1):
                lines.append(
                    f"• /intake unskip {idx} ({_tg_step_label(step)}; key: {step})"
                )
            lines.append("Или вернуть последний пропущенный: /intake unskip")
    lines.append("Продолжить: /intake")
    return "\n".join(lines)


def _tg_intake_skipped_text(candidate: Candidate) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    skipped = {
        str(item).strip()
        for item in (
            runtime.get("skipped_steps")
            if isinstance(runtime.get("skipped_steps"), list)
            else []
        )
        if str(item).strip()
    }
    ordered_skipped = [step for step in _TG_INTAKE_STEP_ORDER if step in skipped]
    if not ordered_skipped:
        return "Пропущенных опциональных шагов нет."
    lines = [
        f"Пропущенные опциональные шаги: {len(ordered_skipped)}",
        "Вернуть можно командами:",
    ]
    for idx, step in enumerate(ordered_skipped, start=1):
        lines.append(f"• /intake unskip {idx} ({_tg_step_label(step)}; key: {step})")
    lines.append("Или вернуть последний: /intake unskip")
    return "\n".join(lines)


def _tg_intake_help_text() -> str:
    return (
        "Команды анкеты:\n"
        "/intake - начать или продолжить анкету\n"
        "/intake status - прогресс и текущий шаг\n"
        "/intake skipped - список пропущенных опциональных шагов\n"
        "/intake skip - пропустить текущий шаг (если он опциональный)\n"
        "/intake unskip [step|number] - вернуть пропущенный шаг\n"
        "/intake reset - сбросить runtime-курсор к первому незаполненному шагу\n"
        "/intake help - показать эту подсказку"
    )


async def _tg_reset_intake_runtime(
    db: AsyncSession,
    *,
    candidate: Candidate,
    chat_id: str,
    username: str | None,
) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    missing = _tg_incomplete_steps(candidate)
    runtime["chat_id"] = chat_id
    if username:
        runtime["username"] = username
    runtime["active"] = bool(missing)
    runtime["current_step"] = missing[0] if missing else None
    runtime["updated_at"] = _now_utc().isoformat()
    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()
    if not missing:
        return "Анкета уже заполнена. Нечего сбрасывать."
    idx = (
        _TG_INTAKE_STEP_ORDER.index(missing[0]) + 1
        if missing[0] in _TG_INTAKE_STEP_ORDER
        else 1
    )
    return (
        "Текущий шаг анкеты сброшен. Ответы сохранены.\n\n"
        + _tg_step_prompt(missing[0], index=idx, total=len(_TG_INTAKE_STEP_ORDER))
    )


async def _tg_skip_intake_step(
    db: AsyncSession,
    *,
    candidate: Candidate,
    chat_id: str,
    username: str | None,
) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    missing = _tg_incomplete_steps(candidate)
    if not missing:
        runtime["active"] = False
        runtime["current_step"] = None
        runtime["completed_at"] = _now_utc().isoformat()
        runtime["updated_at"] = _now_utc().isoformat()
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        await db.commit()
        return "Анкета уже заполнена. Пропуск не требуется."

    current = str(runtime.get("current_step") or "").strip()
    if current not in missing:
        current = missing[0]
    if current not in _TG_INTAKE_OPTIONAL_STEPS:
        idx = (
            _TG_INTAKE_STEP_ORDER.index(current) + 1
            if current in _TG_INTAKE_STEP_ORDER
            else 1
        )
        return (
            f"Шаг «{_tg_step_label(current)}» обязательный и не может быть пропущен.\n\n"
            f"{_tg_step_prompt(current, index=idx, total=len(_TG_INTAKE_STEP_ORDER))}"
        )

    skipped_raw = runtime.get("skipped_steps")
    skipped = [
        str(item).strip()
        for item in (skipped_raw if isinstance(skipped_raw, list) else [])
        if str(item).strip()
    ]
    if current not in skipped:
        skipped.append(current)
    runtime["skipped_steps"] = skipped
    runtime["chat_id"] = chat_id
    if username:
        runtime["username"] = username
    runtime["updated_at"] = _now_utc().isoformat()

    state["telegram_intake"] = runtime
    candidate.intake_state = state

    remaining = _tg_incomplete_steps(candidate)
    if not remaining:
        runtime["active"] = False
        runtime["current_step"] = None
        runtime["completed_at"] = _now_utc().isoformat()
        runtime["updated_at"] = _now_utc().isoformat()
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        await db.commit()
        return (
            f"Шаг «{_tg_step_label(current)}» пропущен.\n"
            "Анкета заполнена. Следующий шаг: /docs и загрузка документов на сайте (/scan)."
        )

    next_step = remaining[0]
    runtime["active"] = True
    runtime["current_step"] = next_step
    runtime["updated_at"] = _now_utc().isoformat()
    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()
    idx = (
        _TG_INTAKE_STEP_ORDER.index(next_step) + 1
        if next_step in _TG_INTAKE_STEP_ORDER
        else 1
    )
    return (
        f"Шаг «{_tg_step_label(current)}» пропущен (опционально).\n\n"
        + _tg_step_prompt(next_step, index=idx, total=len(_TG_INTAKE_STEP_ORDER))
    )


async def _tg_unskip_intake_step(
    db: AsyncSession,
    *,
    candidate: Candidate,
    chat_id: str,
    username: str | None,
    target_step: str | None = None,
) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    skipped_raw = runtime.get("skipped_steps")
    skipped = [
        str(item).strip()
        for item in (skipped_raw if isinstance(skipped_raw, list) else [])
        if str(item).strip()
    ]
    if not skipped:
        return "Нет пропущенных опциональных шагов."

    ordered_skipped = [step for step in _TG_INTAKE_STEP_ORDER if step in skipped]
    target = str(target_step or "").strip().lower()
    if target and re.fullmatch(r"\d+", target):
        numeric = int(target)
        if numeric < 1 or numeric > len(ordered_skipped):
            return f"Неверный номер шага. Укажите 1..{len(ordered_skipped)}."
        target = ordered_skipped[numeric - 1]
    if target:
        if target not in _TG_INTAKE_OPTIONAL_STEPS:
            allowed = ", ".join(sorted(_TG_INTAKE_OPTIONAL_STEPS))
            return f"Можно вернуть только опциональные шаги: {allowed}."
        if target not in skipped:
            listed = ", ".join(skipped)
            return (
                f"Шаг `{target}` не найден среди пропущенных. "
                f"Сейчас пропущено: {listed}."
            )
        step_to_restore = target
    else:
        step_to_restore = skipped[-1]

    skipped = [step for step in skipped if step != step_to_restore]
    runtime["skipped_steps"] = skipped
    runtime["active"] = True
    runtime["current_step"] = step_to_restore
    runtime["chat_id"] = chat_id
    if username:
        runtime["username"] = username
    runtime["updated_at"] = _now_utc().isoformat()

    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()

    idx = (
        _TG_INTAKE_STEP_ORDER.index(step_to_restore) + 1
        if step_to_restore in _TG_INTAKE_STEP_ORDER
        else 1
    )
    return (
        f"Шаг «{_tg_step_label(step_to_restore)}» возвращен в анкету.\n\n"
        + _tg_step_prompt(
            step_to_restore, index=idx, total=len(_TG_INTAKE_STEP_ORDER)
        )
    )


def _tg_parse_step_answer(step: str, text: str) -> tuple[bool, Any, str | None]:
    raw = str(text or "").strip()
    if not raw:
        return False, None, "Ответ пустой. Попробуйте еще раз."
    if step == "full_name":
        parts = [p for p in raw.split() if p]
        if len(parts) < 2:
            return False, None, "Нужно указать имя и фамилию."
        first = parts[0].strip()
        last = " ".join(parts[1:]).strip()
        if len(first) < 2 or len(last) < 2:
            return False, None, "Имя/фамилия слишком короткие."
        return (
            True,
            {"first_name": first, "last_name": last, "full_name": f"{first} {last}"},
            None,
        )
    if step == "birth_date":
        normalized = raw.replace("/", "-").replace(".", "-")
        try:
            if len(normalized) == 10 and normalized[4] == "-":
                parsed = datetime.strptime(normalized, "%Y-%m-%d")
            else:
                parsed = datetime.strptime(normalized, "%d-%m-%Y")
            return True, parsed.date().isoformat(), None
        except Exception:
            return False, None, "Неверный формат даты. Используйте YYYY-MM-DD."
    if step == "citizenship":
        code = normalize_inbound_citizenship_alpha2(re.sub(r"[^A-Za-z]", "", raw))
        if not code:
            return False, None, "Укажите код из 2 букв (например PL)."
        return True, code, None
    if step == "years_ce":
        try:
            years = int(raw)
        except Exception:
            return False, None, "Нужно целое число, например 3."
        if years < 0 or years > 40:
            return False, None, "Допустимый диапазон: 0..40."
        return True, years, None
    if step in {"intl_experience", "has_adr", "agreement_general"}:
        value = _tg_answer_yes_no(raw)
        if value is None:
            return False, None, "Ответьте «да» или «нет»."
        return True, value, None
    return True, raw, None


def _tg_apply_step_answer(candidate: Candidate, step: str, value: Any) -> None:
    state = _as_dict(getattr(candidate, "intake_state", None))
    state["contacts"] = _as_dict(state.get("contacts"))
    state["personal"] = _as_dict(state.get("personal"))
    state["experience"] = _as_dict(state.get("experience"))
    state["agreements"] = _as_dict(state.get("agreements"))

    if step == "full_name":
        first_name = str(_as_dict(value).get("first_name") or "").strip()
        last_name = str(_as_dict(value).get("last_name") or "").strip()
        if first_name:
            candidate.first_name = first_name
        if last_name:
            candidate.last_name = last_name
        state["personal"]["full_name"] = str(
            _as_dict(value).get("full_name") or ""
        ).strip()
    elif step == "birth_date":
        state["personal"]["birth_date"] = str(value or "").strip()
        pd = _as_dict(getattr(candidate, "personal_data", None))
        pd["birth_date"] = str(value or "").strip()
        candidate.personal_data = pd
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["birth_date"] = str(value or "").strip()
        candidate._set_extra(extra)
    elif step == "citizenship":
        state["personal"]["citizenship"] = normalize_inbound_citizenship_alpha2(value)
        pd = _as_dict(getattr(candidate, "personal_data", None))
        pd["citizenship"] = normalize_inbound_citizenship_alpha2(value)
        candidate.personal_data = pd
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["citizenship"] = normalize_inbound_citizenship_alpha2(value)
        candidate._set_extra(extra)
    elif step == "years_ce":
        state["experience"]["years_ce"] = int(value)
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["experience_eu_years"] = int(value)
        candidate._set_extra(extra)
    elif step == "intl_experience":
        state["experience"]["intl_experience"] = bool(value)
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["intl_experience"] = bool(value)
        candidate._set_extra(extra)
    elif step == "has_adr":
        state["personal"]["has_adr"] = bool(value)
        pd = _as_dict(getattr(candidate, "personal_data", None))
        pd["has_adr"] = bool(value)
        candidate.personal_data = pd
        extra = _json_dict(getattr(candidate, "extra", None))
        extra["has_adr"] = bool(value)
        candidate._set_extra(extra)
    elif step == "agreement_general":
        state["agreements"]["general"] = bool(value)
        if bool(value):
            state["agreements"]["general_accepted_at"] = _now_utc().isoformat()

    runtime = _as_dict(state.get("telegram_intake"))
    runtime.setdefault("completed_steps", [])
    completed = runtime.get("completed_steps")
    if not isinstance(completed, list):
        completed = []
    if step not in completed:
        completed.append(step)
    runtime["completed_steps"] = completed
    runtime["updated_at"] = _now_utc().isoformat()
    state["telegram_intake"] = runtime
    candidate.intake_state = state


async def _tg_start_or_resume_intake(
    db: AsyncSession,
    *,
    candidate: Candidate,
    chat_id: str,
    username: str | None,
) -> str:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    missing = _tg_incomplete_steps(candidate)
    if not missing:
        runtime["active"] = False
        runtime["current_step"] = None
        runtime["completed_at"] = _now_utc().isoformat()
        runtime["updated_at"] = _now_utc().isoformat()
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        await db.commit()
        return (
            "Анкета уже заполнена. "
            "Проверьте /docs или отправьте /apply для ссылки на анкету."
        )
    current = str(runtime.get("current_step") or "").strip()
    if current not in missing:
        current = missing[0]
    runtime["active"] = True
    runtime["current_step"] = current
    runtime["chat_id"] = chat_id
    if username:
        runtime["username"] = username
    runtime["updated_at"] = _now_utc().isoformat()
    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()
    idx = (
        _TG_INTAKE_STEP_ORDER.index(current) + 1
        if current in _TG_INTAKE_STEP_ORDER
        else 1
    )
    return _tg_step_prompt(current, index=idx, total=len(_TG_INTAKE_STEP_ORDER))


async def _tg_process_intake_answer(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    text: str,
) -> str | None:
    state = _as_dict(getattr(candidate, "intake_state", None))
    runtime = _as_dict(state.get("telegram_intake"))
    if not bool(runtime.get("active")):
        return None
    current = str(runtime.get("current_step") or "").strip()
    missing = _tg_incomplete_steps(candidate)
    if current not in missing:
        if not missing:
            runtime["active"] = False
            runtime["current_step"] = None
            runtime["completed_at"] = _now_utc().isoformat()
            runtime["updated_at"] = _now_utc().isoformat()
            state["telegram_intake"] = runtime
            candidate.intake_state = state
            await db.commit()
            return await _tg_intake_completion_docs_text(
                db,
                tenant_id=tenant_id,
                candidate=candidate,
            )
        current = missing[0]
        runtime["current_step"] = current
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        await db.commit()
    ok, parsed_value, error = _tg_parse_step_answer(current, text)
    if not ok:
        idx = (
            _TG_INTAKE_STEP_ORDER.index(current) + 1
            if current in _TG_INTAKE_STEP_ORDER
            else 1
        )
        return f"{error}\n\n{_tg_step_prompt(current, index=idx, total=len(_TG_INTAKE_STEP_ORDER))}"

    _tg_apply_step_answer(candidate, current, parsed_value)
    candidate.intake_status = str(getattr(candidate, "intake_status", "") or "draft")
    remaining = _tg_incomplete_steps(candidate)
    runtime = _as_dict(
        _as_dict(getattr(candidate, "intake_state", None)).get("telegram_intake")
    )
    if not remaining:
        runtime["active"] = False
        runtime["current_step"] = None
        runtime["completed_at"] = _now_utc().isoformat()
        runtime.setdefault("ready_for_docs_notified_at", _now_utc().isoformat())
        runtime["updated_at"] = _now_utc().isoformat()
        _ensure_candidate_intake_token(candidate)
        state = _as_dict(getattr(candidate, "intake_state", None))
        state["telegram_intake"] = runtime
        candidate.intake_state = state
        if not str(runtime.get("ready_for_docs_event_logged_at") or "").strip():
            try:
                await log_activity(
                    db,
                    tenant_id=str(tenant_id or "").strip(),
                    action="candidate_ready_for_docs",
                    actor_id=None,
                    target_type="candidate",
                    target_id=str(getattr(candidate, "id", "") or "").strip() or None,
                    payload={
                        "source": "telegram_intake",
                        "channel": "telegram",
                        "completed_at": str(runtime.get("completed_at") or ""),
                        "intake_status": str(getattr(candidate, "intake_status", "") or ""),
                    },
                )
            except Exception:
                logger.exception(
                    "telegram intake ready_for_docs audit failed tenant=%s candidate=%s",
                    tenant_id,
                    getattr(candidate, "id", None),
                )
            runtime["ready_for_docs_event_logged_at"] = _now_utc().isoformat()
            state["telegram_intake"] = runtime
            candidate.intake_state = state
        try:
            await sync_candidate_ready_for_handoff_gate(
                db,
                tenant_id=tenant_id,
                candidate=candidate,
                source="telegram_intake_completion",
            )
        except Exception:
            logger.exception(
                "telegram intake auto-ready-for-handoff sync failed tenant=%s candidate=%s",
                tenant_id,
                getattr(candidate, "id", None),
            )
        await db.commit()
        return await _tg_intake_completion_docs_text(
            db,
            tenant_id=tenant_id,
            candidate=candidate,
        )

    next_step = remaining[0]
    runtime["active"] = True
    runtime["current_step"] = next_step
    runtime["updated_at"] = _now_utc().isoformat()
    state = _as_dict(getattr(candidate, "intake_state", None))
    state["telegram_intake"] = runtime
    candidate.intake_state = state
    await db.commit()
    idx = (
        _TG_INTAKE_STEP_ORDER.index(next_step) + 1
        if next_step in _TG_INTAKE_STEP_ORDER
        else 1
    )
    return _tg_step_prompt(next_step, index=idx, total=len(_TG_INTAKE_STEP_ORDER))
