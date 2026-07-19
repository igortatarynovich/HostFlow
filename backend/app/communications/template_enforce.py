"""C4 — Template metadata enforcement (backend allow/deny only).

Does NOT: find templates, pick best template, fallback, substitute locale/
purpose/module, or touch Recruitment/Sales ORM.

Template never defines context. Context defines template eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4

from backend.app.communications.context_resolver import CommunicationContext
from backend.app.communications.template_metadata import (
    ACTIVE_LIFECYCLES,
    CommunicationTemplateMetadata,
)

REASON_ALLOWED = "allowed"
REASON_MISSING_TEMPLATE = "unknown_or_missing_template"
REASON_INCOMPLETE_METADATA = "incomplete_template_metadata"
REASON_MODULE_MISMATCH = "template_module_owner_mismatch"
REASON_DOMAIN_MISMATCH = "template_communication_domain_mismatch"
REASON_PURPOSE_MISMATCH = "template_communication_purpose_mismatch"
REASON_CHANNEL_UNSUPPORTED = "template_channel_unsupported"
REASON_LOCALE_UNSUPPORTED = "template_locale_unsupported"
REASON_LIFECYCLE_INACTIVE = "template_lifecycle_inactive"
REASON_VERSION_REQUIRED = "template_version_required"
REASON_CONTEXT_INCOMPLETE = "incomplete_communication_context"

ENFORCE_VERSION = "communication.template_enforce.v1"


@dataclass(frozen=True, slots=True)
class TemplateEnforceDecision:
    allowed: bool
    reason_code: str
    decision_id: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason_code": self.reason_code,
            "decision_id": self.decision_id,
            "details": dict(self.details),
            "enforce_version": ENFORCE_VERSION,
        }


def _deny(reason_code: str, **details: Any) -> TemplateEnforceDecision:
    return TemplateEnforceDecision(
        allowed=False,
        reason_code=reason_code,
        decision_id=str(uuid4()),
        details=dict(details),
    )


def _allow(**details: Any) -> TemplateEnforceDecision:
    return TemplateEnforceDecision(
        allowed=True,
        reason_code=REASON_ALLOWED,
        decision_id=str(uuid4()),
        details=dict(details),
    )


def enforce_template_metadata(
    *,
    context: CommunicationContext,
    template: CommunicationTemplateMetadata | None,
    channel: str,
    communication_purpose: str,
    locale: str | None = None,
    require_template_version: str | None = None,
) -> TemplateEnforceDecision:
    """Validate that template metadata may be used for this context + purpose + channel.

    Fail-closed on any mismatch. No fallback to another module/purpose/locale.
    """
    if context is None:
        return _deny(REASON_CONTEXT_INCOMPLETE, reason=REASON_CONTEXT_INCOMPLETE)

    ctx_owner = str(context.module_owner or "").strip().lower()
    ctx_domain = str(context.communication_domain or "").strip().lower()
    if not ctx_owner or not ctx_domain or not str(context.result_id or "").strip():
        return _deny(
            REASON_CONTEXT_INCOMPLETE,
            module_owner=ctx_owner,
            communication_domain=ctx_domain,
        )

    if template is None:
        return _deny(REASON_MISSING_TEMPLATE, reason=REASON_MISSING_TEMPLATE)

    tid = str(template.template_id or "").strip()
    tver = str(template.template_version or "").strip()
    t_owner = str(template.module_owner or "").strip().lower()
    t_domain = str(template.communication_domain or "").strip().lower()
    t_purpose = str(template.communication_purpose or "").strip()
    t_life = str(template.lifecycle_status or "").strip().lower()
    if not tid or not tver or not t_owner or not t_domain or not t_purpose or not t_life:
        return _deny(
            REASON_INCOMPLETE_METADATA,
            template_id=tid or None,
            reason=REASON_INCOMPLETE_METADATA,
        )
    if not template.supported_channels:
        return _deny(
            REASON_INCOMPLETE_METADATA,
            template_id=tid,
            reason="missing_supported_channels",
        )

    # Context defines eligibility — never the reverse.
    if t_owner != ctx_owner:
        return _deny(
            REASON_MODULE_MISMATCH,
            context_module_owner=ctx_owner,
            template_module_owner=t_owner,
            template_id=tid,
            # Explicit: no Recruitment substitution.
            fallback=None,
        )
    if t_domain != ctx_domain:
        return _deny(
            REASON_DOMAIN_MISMATCH,
            context_communication_domain=ctx_domain,
            template_communication_domain=t_domain,
            template_id=tid,
            fallback=None,
        )

    purpose = str(communication_purpose or "").strip()
    if not purpose or t_purpose != purpose:
        return _deny(
            REASON_PURPOSE_MISMATCH,
            requested_purpose=purpose or None,
            template_purpose=t_purpose,
            template_id=tid,
            fallback=None,
        )

    ch = str(channel or "").strip().lower()
    if not ch or ch not in template.supported_channels:
        return _deny(
            REASON_CHANNEL_UNSUPPORTED,
            channel=ch or None,
            supported_channels=sorted(template.supported_channels),
            template_id=tid,
            fallback=None,
        )

    if t_life not in ACTIVE_LIFECYCLES:
        return _deny(
            REASON_LIFECYCLE_INACTIVE,
            lifecycle_status=t_life,
            template_id=tid,
            fallback=None,
        )

    if require_template_version is not None:
        required = str(require_template_version).strip()
        if not required or required != tver:
            return _deny(
                REASON_VERSION_REQUIRED,
                required_template_version=required or None,
                template_version=tver,
                template_id=tid,
            )

    if locale is not None:
        loc = str(locale).strip().lower()
        if loc and template.supported_locales and loc not in template.supported_locales:
            return _deny(
                REASON_LOCALE_UNSUPPORTED,
                locale=loc,
                supported_locales=sorted(template.supported_locales),
                template_id=tid,
                fallback=None,
            )

    return _allow(
        template_id=tid,
        template_version=tver,
        module_owner=t_owner,
        communication_purpose=t_purpose,
        channel=ch,
    )
