"""C2.1 PR-2 — Pure Template Renderer.

Public ops: validate · preview · render · diagnostics.
No SQL, ORM, Sender, Thread, Campaign, or Automation imports.
"""

from backend.app.communications.templates.renderer.engine import (
    diagnostics,
    preview,
    render,
    validate,
)
from backend.app.communications.templates.renderer.types import (
    VARIABLE_TYPES,
    Diagnostic,
    RenderResult,
    TemplateVariableSpec,
    TemplateVersionPayload,
)

__all__ = [
    "VARIABLE_TYPES",
    "TemplateVariableSpec",
    "TemplateVersionPayload",
    "Diagnostic",
    "RenderResult",
    "validate",
    "preview",
    "render",
    "diagnostics",
]
