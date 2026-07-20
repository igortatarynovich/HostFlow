"""Resolve module-owned manual_thread_reply purpose + template (operator inbox).

Uses confirmed CommunicationContext.module_owner — never invents domain from host
or legacy entity_type. Lazy-imports published module metadata builders only.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.communications.template_metadata import CommunicationTemplateMetadata

PURPOSE_MANUAL_THREAD_REPLY = "manual_thread_reply"


@dataclass(frozen=True, slots=True)
class ManualThreadReplyBinding:
    communication_purpose: str
    template: CommunicationTemplateMetadata


def manual_thread_reply_binding(
    *,
    module_owner: str,
    channel: str,
) -> ManualThreadReplyBinding | None:
    """Return purpose+template for freeform operator reply, or None if unsupported."""
    owner = str(module_owner or "").strip().lower()
    ch = str(channel or "").strip().lower()
    if not owner or not ch:
        return None

    if owner == "sales":
        from backend.app.modules.sales.communication.manual_thread_reply import (
            PURPOSE_MANUAL_THREAD_REPLY as purpose,
            sales_manual_thread_reply_template_metadata,
        )

        template = sales_manual_thread_reply_template_metadata()
    elif owner == "recruitment":
        from backend.app.modules.recruitment.communication.manual_thread_reply import (
            PURPOSE_MANUAL_THREAD_REPLY as purpose,
            recruitment_manual_thread_reply_template_metadata,
        )

        template = recruitment_manual_thread_reply_template_metadata()
    else:
        return None

    if ch not in template.supported_channels:
        return None
    return ManualThreadReplyBinding(
        communication_purpose=purpose,
        template=template,
    )
