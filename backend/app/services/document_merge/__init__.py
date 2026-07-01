from __future__ import annotations

from backend.app.services.document_merge.generate import generate_merge_document
from backend.app.services.document_merge.templates_repo import (
    create_template,
    delete_template,
    get_template,
    list_templates,
    resolve_template_for_scope,
    update_template,
)

__all__ = [
    "create_template",
    "delete_template",
    "generate_merge_document",
    "get_template",
    "list_templates",
    "resolve_template_for_scope",
    "update_template",
]
