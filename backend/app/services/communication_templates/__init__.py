"""Re-export communication template registry."""

from backend.app.services.communication_templates.registry import (  # noqa: F401
    CommunicationTemplate,
    CommunicationTemplateNotFoundError,
    QUESTIONNAIRE_INVITE_EMAIL_V1,
    render_template,
    resolve_template,
)

__all__ = [
    "CommunicationTemplate",
    "CommunicationTemplateNotFoundError",
    "QUESTIONNAIRE_INVITE_EMAIL_V1",
    "render_template",
    "resolve_template",
]
