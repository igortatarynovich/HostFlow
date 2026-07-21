"""ORM → pure TemplateVersionPayload adapter (outside the renderer package)."""

from __future__ import annotations

from backend.app.communications.templates.renderer.types import (
    TemplateVariableSpec,
    TemplateVersionPayload,
)
from backend.app.models.communication_template import (
    CommunicationTemplate,
    CommunicationTemplateVersion,
)


def template_version_to_payload(
    version: CommunicationTemplateVersion,
    *,
    template: CommunicationTemplate | None = None,
) -> TemplateVersionPayload:
    """Build a pure renderer payload from loaded ORM rows.

    Caller must ensure relationships (variables, channel_bindings) are loaded.
    """
    tpl = template if template is not None else getattr(version, "template", None)
    template_status = str(getattr(tpl, "status", "active") or "active")

    variables = tuple(
        TemplateVariableSpec(
            name=str(v.name),
            var_type=str(v.var_type or "string"),
            required=bool(v.required),
            default_value=v.default_value,
            enum_values=(),
        )
        for v in (version.variables or [])
    )
    channels = frozenset(
        str(c.channel).strip().lower()
        for c in (version.channel_bindings or [])
        if c.channel
    )
    return TemplateVersionPayload(
        template_version_id=str(version.id),
        status=str(version.status or "").strip().lower(),
        template_status=template_status.strip().lower(),
        locale=str(version.locale or "pl"),
        subject=version.subject,
        body_text=version.body_text,
        body_html=version.body_html,
        channels=channels,
        variables=variables,
    )


def build_payload(
    *,
    template_version_id: str,
    status: str,
    template_status: str,
    locale: str,
    subject: str | None,
    body_text: str | None,
    body_html: str | None = None,
    channels: set[str] | frozenset[str] | list[str],
    variables: list[TemplateVariableSpec] | tuple[TemplateVariableSpec, ...],
) -> TemplateVersionPayload:
    """Helper constructor that never touches the DB (tests / non-ORM callers)."""
    return TemplateVersionPayload(
        template_version_id=str(template_version_id),
        status=str(status).strip().lower(),
        template_status=str(template_status).strip().lower(),
        locale=str(locale or "pl"),
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        channels=frozenset(str(c).strip().lower() for c in channels),
        variables=tuple(variables),
    )


__all__ = ["template_version_to_payload", "build_payload"]
