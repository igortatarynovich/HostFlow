"""Sales-owned metadata for operator freeform thread replies (inbox).

Does not send mail. Purpose + template metadata only — C5 still authorizes.
"""

from __future__ import annotations

from backend.app.communications.template_metadata import (
    CommunicationTemplateMetadata,
    build_template_metadata,
)
from backend.app.modules.sales.communication.policy_adapter import POLICY_VERSION

PURPOSE_MANUAL_THREAD_REPLY = "manual_thread_reply"
TEMPLATE_ID = "tpl_sales_manual_thread_reply_v1"
TEMPLATE_VERSION = "1"


def sales_manual_thread_reply_template_metadata() -> CommunicationTemplateMetadata:
    return build_template_metadata(
        template_id=TEMPLATE_ID,
        template_version=TEMPLATE_VERSION,
        module_owner="sales",
        communication_domain="sales",
        communication_purpose=PURPOSE_MANUAL_THREAD_REPLY,
        supported_channels=["email", "sms", "whatsapp", "telegram", "system"],
        supported_locales=["pl", "en", "ru", "uk", "de"],
        lifecycle_status="active",
        policy_version=POLICY_VERSION,
    )
