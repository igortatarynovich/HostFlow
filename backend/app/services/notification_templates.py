from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class ChannelTemplateDef:
    """
    Describes a per-channel notification template binding.
    `template_key` points to the localisation key (or slug) that the
    frontend / template renderer should use. Optional `subject_key`
    allows channels (email/webhook) to split subject/body resources.
    """

    channel: str
    template_key: str
    subject_key: Optional[str] = None
    default_subject: Optional[str] = None
    body_key: Optional[str] = None
    default_body: Optional[str] = None


@dataclass(frozen=True)
class NotificationTemplateDef:
    """
    Canonical notification template descriptor used by reminders and UI.
    """

    slug: str
    event_type: str
    description: str
    offset_hours: Optional[int] = None
    schedule_key: Optional[str] = None
    variables: List[str] = field(default_factory=list)
    channels: List[ChannelTemplateDef] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


DOCUMENT_EXPIRY_TEMPLATES: List[NotificationTemplateDef] = [
    NotificationTemplateDef(
        slug="document.expiry.pre_24",
        event_type="document.expiry",
        description="Reminder 24 hours before the document expires.",
        offset_hours=-24,
        schedule_key="document_expiry:-24",
        variables=[
            "candidate_name",
            "document_name",
            "expires_at",
            "offset_hours",
            "offset_days",
        ],
        channels=[
            ChannelTemplateDef(
                channel="in_app",
                template_key="notifications.document_expiry.pre_24",
                default_body="Document {document_name} will expire in 24 hours.",
            ),
            ChannelTemplateDef(
                channel="email",
                template_key="email.document_expiry.pre_24",
                subject_key="email.document_expiry.pre_24.subject",
                default_subject="Document {document_name} expires in 24 hours",
                body_key="email.document_expiry.pre_24.body",
                default_body=(
                    "Document {document_name} for {candidate_name} will expire on {expires_at}."
                ),
            ),
            ChannelTemplateDef(
                channel="webhook",
                template_key="webhook.document_expiry.pre_24",
            ),
        ],
        metadata={"severity": "info", "phase": "pre"},
    ),
    NotificationTemplateDef(
        slug="document.expiry.pre_4",
        event_type="document.expiry",
        description="Reminder 4 hours before the document expires.",
        offset_hours=-4,
        schedule_key="document_expiry:-4",
        variables=[
            "candidate_name",
            "document_name",
            "expires_at",
            "offset_hours",
            "offset_days",
        ],
        channels=[
            ChannelTemplateDef(
                channel="in_app",
                template_key="notifications.document_expiry.pre_4",
                default_body="Document {document_name} will expire in 4 hours.",
            ),
            ChannelTemplateDef(
                channel="email",
                template_key="email.document_expiry.pre_4",
                subject_key="email.document_expiry.pre_4.subject",
                default_subject="Document {document_name} expires in 4 hours",
                body_key="email.document_expiry.pre_4.body",
                default_body=(
                    "Document {document_name} for {candidate_name} will expire on {expires_at}."
                ),
            ),
            ChannelTemplateDef(
                channel="webhook",
                template_key="webhook.document_expiry.pre_4",
            ),
        ],
        metadata={"severity": "warning", "phase": "pre"},
    ),
    NotificationTemplateDef(
        slug="document.expiry.due",
        event_type="document.expiry",
        description="Reminder at the moment of expiry (T+0).",
        offset_hours=0,
        schedule_key="document_expiry:0",
        variables=[
            "candidate_name",
            "document_name",
            "expires_at",
            "offset_hours",
            "offset_days",
        ],
        channels=[
            ChannelTemplateDef(
                channel="in_app",
                template_key="notifications.document_expiry.due",
                default_body="Document {document_name} expires today.",
            ),
            ChannelTemplateDef(
                channel="email",
                template_key="email.document_expiry.due",
                subject_key="email.document_expiry.due.subject",
                default_subject="Document {document_name} expires today",
                body_key="email.document_expiry.due.body",
                default_body=(
                    "Document {document_name} for {candidate_name} expires today ({expires_at})."
                ),
            ),
            ChannelTemplateDef(
                channel="webhook",
                template_key="webhook.document_expiry.due",
            ),
        ],
        metadata={"severity": "critical", "phase": "due"},
    ),
    NotificationTemplateDef(
        slug="document.expiry.overdue",
        event_type="document.expiry",
        description="Reminder after the document is overdue (T+N).",
        offset_hours=24,
        schedule_key="document_expiry:+24",
        variables=[
            "candidate_name",
            "document_name",
            "expires_at",
            "offset_hours",
            "offset_days",
        ],
        channels=[
            ChannelTemplateDef(
                channel="in_app",
                template_key="notifications.document_expiry.overdue",
                default_body="Document {document_name} is overdue by {offset_days} days.",
            ),
            ChannelTemplateDef(
                channel="email",
                template_key="email.document_expiry.overdue",
                subject_key="email.document_expiry.overdue.subject",
                default_subject="Document {document_name} is overdue",
                body_key="email.document_expiry.overdue.body",
                default_body=(
                    "Document {document_name} for {candidate_name} has been overdue since {expires_at}."
                ),
            ),
            ChannelTemplateDef(
                channel="webhook",
                template_key="webhook.document_expiry.overdue",
            ),
        ],
        metadata={"severity": "critical", "phase": "post"},
    ),
    NotificationTemplateDef(
        slug="document.expiry.pre_custom",
        event_type="document.expiry",
        description="Custom lead time reminder before the document expires.",
        offset_hours=None,
        schedule_key=None,
        variables=[
            "candidate_name",
            "document_name",
            "expires_at",
            "offset_hours",
            "offset_days",
        ],
        channels=[
            ChannelTemplateDef(
                channel="in_app",
                template_key="notifications.document_expiry.pre_custom",
                default_body="Document {document_name} will expire soon.",
            ),
            ChannelTemplateDef(
                channel="email",
                template_key="email.document_expiry.pre_custom",
                subject_key="email.document_expiry.pre_custom.subject",
                default_subject="Document {document_name} will expire soon",
                body_key="email.document_expiry.pre_custom.body",
                default_body=(
                    "Document {document_name} for {candidate_name} will expire on {expires_at}."
                ),
            ),
            ChannelTemplateDef(
                channel="webhook",
                template_key="webhook.document_expiry.pre_custom",
            ),
        ],
        metadata={"severity": "info", "phase": "pre"},
    ),
    NotificationTemplateDef(
        slug="document.expiry.overdue_repeat",
        event_type="document.expiry",
        description="Repeated reminder while the document stays overdue (T+N repeating).",
        offset_hours=None,
        schedule_key=None,
        variables=[
            "candidate_name",
            "document_name",
            "expires_at",
            "offset_hours",
            "offset_days",
        ],
        channels=[
            ChannelTemplateDef(
                channel="in_app",
                template_key="notifications.document_expiry.overdue_repeat",
                default_body="Document {document_name} is still overdue.",
            ),
            ChannelTemplateDef(
                channel="email",
                template_key="email.document_expiry.overdue_repeat",
                subject_key="email.document_expiry.overdue_repeat.subject",
                default_subject="Document {document_name} remains overdue",
                body_key="email.document_expiry.overdue_repeat.body",
                default_body=(
                    "Document {document_name} for {candidate_name} remains overdue since {expires_at}."
                ),
            ),
            ChannelTemplateDef(
                channel="webhook",
                template_key="webhook.document_expiry.overdue_repeat",
            ),
        ],
        metadata={"severity": "critical", "phase": "post"},
    ),
    NotificationTemplateDef(
        slug="candidate.intake_submitted",
        event_type="candidate.intake_submitted",
        description="Candidate submitted the public questionnaire.",
        variables=[
            "candidate_id",
            "candidate_name",
            "stage",
            "manager_id",
            "recruiter_id",
        ],
        channels=[
            ChannelTemplateDef(
                channel="in_app",
                template_key="notifications.candidate.intake_submitted",
                default_body="{candidate_name} submitted the questionnaire.",
            ),
            ChannelTemplateDef(
                channel="webhook",
                template_key="webhook.candidate.intake_submitted",
            ),
        ],
        metadata={"severity": "info"},
    ),
]

_TEMPLATES_BY_SLUG: Dict[str, NotificationTemplateDef] = {
    template.slug: template for template in DOCUMENT_EXPIRY_TEMPLATES
}

_TEMPLATES_BY_OFFSET: Dict[int, NotificationTemplateDef] = {
    template.offset_hours: template
    for template in DOCUMENT_EXPIRY_TEMPLATES
    if template.offset_hours is not None
}


def list_notification_templates() -> List[NotificationTemplateDef]:
    """
    Return all notification templates known to the backend.
    """

    return list(DOCUMENT_EXPIRY_TEMPLATES)


def get_notification_template(slug: str) -> Optional[NotificationTemplateDef]:
    return _TEMPLATES_BY_SLUG.get(slug)


def get_document_expiry_template(offset_hours: int) -> NotificationTemplateDef:
    """
    Resolve template by offset. Fallbacks map any unknown negative offsets
    to `pre_custom` and positive offsets (beyond the first SLA repeat) to
    `overdue_repeat`.
    """

    if offset_hours in _TEMPLATES_BY_OFFSET:
        return _TEMPLATES_BY_OFFSET[offset_hours]

    if offset_hours < 0:
        return _TEMPLATES_BY_SLUG["document.expiry.pre_custom"]

    if offset_hours > 0:
        # 24h is the canonical first overdue offset; subsequent reminders reuse repeat template
        if offset_hours == 24:
            return _TEMPLATES_BY_SLUG["document.expiry.overdue"]
        return _TEMPLATES_BY_SLUG["document.expiry.overdue_repeat"]

    return _TEMPLATES_BY_SLUG["document.expiry.due"]


def iter_channel_templates(
    template: NotificationTemplateDef,
) -> Iterable[ChannelTemplateDef]:
    return template.channels
