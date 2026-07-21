"""Pure data contracts for the C2.1 Template Renderer (no ORM / I/O)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

# Declared variable types (Validate catches mismatches before send).
VARIABLE_TYPES: frozenset[str] = frozenset(
    {
        "string",
        "text",
        "markdown",
        "html",
        "email",
        "phone",
        "url",
        "date",
        "datetime",
        "currency",
        "boolean",
        "bool",  # alias accepted for PR-1 rows
        "number",
        "enum",
    }
)

DIAG_MISSING_VARIABLE = "missing_variable"
DIAG_WRONG_TYPE = "wrong_type"
DIAG_UNKNOWN_VARIABLE = "unknown_variable"
DIAG_CHANNEL_UNSUPPORTED = "channel_unsupported"
DIAG_TEMPLATE_NOT_PUBLISHED = "template_not_published"
DIAG_VERSION_ARCHIVED = "version_archived"
DIAG_INVALID_TEMPLATE = "invalid_template"

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

# Unknown variables are errors (strict) for reproducible sends.
UNKNOWN_VARIABLE_POLICY = "error"


@dataclass(frozen=True, slots=True)
class TemplateVariableSpec:
    name: str
    var_type: str
    required: bool = True
    default_value: str | None = None
    enum_values: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TemplateVersionPayload:
    """Immutable snapshot of a template version — loaded by the caller, never by Renderer."""

    template_version_id: str
    status: str  # draft | published
    template_status: str  # active | archived
    locale: str
    subject: str | None
    body_text: str | None
    body_html: str | None
    channels: frozenset[str]
    variables: tuple[TemplateVariableSpec, ...]


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    path: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "details": dict(self.details or {}),
        }


@dataclass(frozen=True, slots=True)
class RenderResult:
    ok: bool
    template_version_id: str
    subject: str | None
    body_text: str | None
    body_html: str | None
    diagnostics: tuple[Diagnostic, ...]
    locale: str
    channel: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "template_version_id": self.template_version_id,
            "locale": self.locale,
            "channel": self.channel,
            "subject": self.subject,
            "body_text": self.body_text,
            "body_html": self.body_html,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


__all__ = [
    "VARIABLE_TYPES",
    "DIAG_MISSING_VARIABLE",
    "DIAG_WRONG_TYPE",
    "DIAG_UNKNOWN_VARIABLE",
    "DIAG_CHANNEL_UNSUPPORTED",
    "DIAG_TEMPLATE_NOT_PUBLISHED",
    "DIAG_VERSION_ARCHIVED",
    "DIAG_INVALID_TEMPLATE",
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "UNKNOWN_VARIABLE_POLICY",
    "TemplateVariableSpec",
    "TemplateVersionPayload",
    "Diagnostic",
    "RenderResult",
]
