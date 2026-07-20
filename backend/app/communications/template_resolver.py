"""TemplateResolver — resolve template by intent/key without callers touching the registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from backend.app.communications.intent import (
    CommunicationIntent,
    resolve_intent_policy,
)
from backend.app.services.communication_templates.registry import (
    CommunicationTemplate,
    CommunicationTemplateNotFoundError,
    render_template,
    resolve_template,
)


@dataclass(frozen=True, slots=True)
class ResolvedTemplate:
    key: str
    version: int
    purpose: str
    channel: str
    template: CommunicationTemplate


class TemplateResolver(Protocol):
    def resolve_by_key(self, key: str) -> ResolvedTemplate: ...

    def resolve_for_intent(
        self,
        intent: CommunicationIntent | str,
        *,
        channel: str = "email",
        preferred_key: str | None = None,
    ) -> ResolvedTemplate: ...

    def render(
        self,
        resolved: ResolvedTemplate,
        *,
        locale: str,
        variables: Mapping[str, Any],
    ) -> dict[str, str]: ...


class SeedTemplateResolver:
    """Wraps the seed CommunicationTemplate registry (single-template path for now)."""

    def resolve_by_key(self, key: str) -> ResolvedTemplate:
        tpl = resolve_template(key)
        return ResolvedTemplate(
            key=tpl.key,
            version=1,
            purpose=tpl.purpose,
            channel=tpl.channel,
            template=tpl,
        )

    def resolve_for_intent(
        self,
        intent: CommunicationIntent | str,
        *,
        channel: str = "email",
        preferred_key: str | None = None,
    ) -> ResolvedTemplate:
        policy = resolve_intent_policy(intent)
        key = (preferred_key or "").strip() or None
        if key and policy.allowed_template_keys and key not in policy.allowed_template_keys:
            raise CommunicationTemplateNotFoundError(key)
        if not key:
            if not policy.allowed_template_keys:
                raise CommunicationTemplateNotFoundError(
                    f"intent:{getattr(intent, 'value', intent)}"
                )
            key = sorted(policy.allowed_template_keys)[0]
        resolved = self.resolve_by_key(key)
        if channel and resolved.channel != channel:
            raise CommunicationTemplateNotFoundError(key)
        return resolved

    def render(
        self,
        resolved: ResolvedTemplate,
        *,
        locale: str,
        variables: Mapping[str, Any],
    ) -> dict[str, str]:
        return render_template(resolved.template, locale=locale, variables=variables)


_default_template_resolver: TemplateResolver = SeedTemplateResolver()


def get_template_resolver() -> TemplateResolver:
    return _default_template_resolver
