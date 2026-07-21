"""C2.1 Template Platform — domain package (Intent-only; no module imports)."""

from backend.app.communications.templates.errors import TemplateDomainError
from backend.app.communications.templates.lifecycle import (
    archive_template,
    create_template_with_draft,
    get_draft_version,
    publish_draft,
    replace_draft_bindings,
    replace_draft_variables,
    update_draft_content,
)
from backend.app.models.communication_template import (
    Template,
    TemplateChannelBinding,
    TemplateIntentBinding,
    TemplateVariable,
    TemplateVersion,
)

__all__ = [
    "Template",
    "TemplateVersion",
    "TemplateVariable",
    "TemplateChannelBinding",
    "TemplateIntentBinding",
    "TemplateDomainError",
    "create_template_with_draft",
    "get_draft_version",
    "update_draft_content",
    "replace_draft_variables",
    "replace_draft_bindings",
    "publish_draft",
    "archive_template",
]
