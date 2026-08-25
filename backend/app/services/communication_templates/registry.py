"""Versioned communication templates (system seed; tenant overrides later)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class CommunicationTemplate:
    key: str
    purpose: str
    channel: str
    locales: Mapping[str, Mapping[str, str]]
    allowed_variables: frozenset[str]
    enabled: bool = True


QUESTIONNAIRE_INVITE_EMAIL_V1 = CommunicationTemplate(
    key="questionnaire_invite_email_v1",
    purpose="questionnaire_invite",
    channel="email",
    locales={
        "pl": {
            "subject": "Kilka pytań dotyczących współpracy",
            "body": (
                "Dzień dobry {{contact_name}},\n\n"
                "dziękujemy za zainteresowanie współpracą.\n\n"
                "Abyśmy mogli lepiej poznać Państwa potrzeby i przygotować odpowiednią propozycję, "
                "prosimy o wypełnienie krótkiej ankiety. Zajmie to około 2–3 minut.\n\n"
                "{{questionnaire_url}}\n\n"
                "Po otrzymaniu odpowiedzi skontaktujemy się z Państwem w sprawie dalszych kroków."
            ),
        },
        "en": {
            "subject": "A few questions about your request",
            "body": (
                "Hello {{contact_name}},\n\n"
                "thank you for your interest in working with us.\n\n"
                "To better understand your needs and prepare the right proposal, please complete this short "
                "questionnaire. It should take about 2–3 minutes.\n\n"
                "{{questionnaire_url}}\n\n"
                "Once we receive your answers, we will contact you to discuss the next steps."
            ),
        },
        "ru": {
            "subject": "Несколько вопросов по вашему обращению",
            "body": (
                "Здравствуйте, {{contact_name}}!\n\n"
                "Спасибо за интерес к сотрудничеству.\n\n"
                "Чтобы мы могли лучше понять вашу задачу и подготовить подходящее предложение, "
                "пожалуйста, заполните короткую анкету. Это займёт около 2–3 минут.\n\n"
                "{{questionnaire_url}}\n\n"
                "После получения ответов мы свяжемся с вами и обсудим дальнейшие шаги."
            ),
        },
    },
    allowed_variables=frozenset(
        {
            "contact_name",
            "questionnaire_url",
            "url",
        }
    ),
)

_SYSTEM_TEMPLATES: tuple[CommunicationTemplate, ...] = (QUESTIONNAIRE_INVITE_EMAIL_V1,)

_VAR_RE = re.compile(r"\{\{([^}]+)\}\}")


class CommunicationTemplateNotFoundError(LookupError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Communication template not found: {key}")
        self.key = key


def resolve_template(key: str, *, tenant_overrides: Optional[Mapping[str, Any]] = None) -> CommunicationTemplate:
    del tenant_overrides  # reserved for future per-tenant overrides
    for tpl in _SYSTEM_TEMPLATES:
        if tpl.key == key and tpl.enabled:
            return tpl
    raise CommunicationTemplateNotFoundError(key)


def render_template(
    template: CommunicationTemplate,
    *,
    locale: str,
    variables: Mapping[str, Any],
) -> dict[str, str]:
    code = str(locale or "pl").strip().lower()[:2] or "pl"
    localized = template.locales.get(code) or template.locales.get("pl") or next(iter(template.locales.values()))
    subject_raw = str(localized.get("subject") or "")
    body_raw = str(localized.get("body") or "")

    values = {str(k): "" if v is None else str(v) for k, v in dict(variables or {}).items()}
    if "url" not in values and "questionnaire_url" in values:
        values["url"] = values["questionnaire_url"]
    if "questionnaire_url" not in values and "url" in values:
        values["questionnaire_url"] = values["url"]

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        if name not in template.allowed_variables:
            raise ValueError(f"Template contains unsupported variables: {name}")
        return values.get(name, "")

    return {
        "subject": _VAR_RE.sub(_replace, subject_raw).strip(),
        "body": _VAR_RE.sub(_replace, body_raw).strip(),
    }


__all__ = [
    "CommunicationTemplate",
    "CommunicationTemplateNotFoundError",
    "QUESTIONNAIRE_INVITE_EMAIL_V1",
    "render_template",
    "resolve_template",
]
