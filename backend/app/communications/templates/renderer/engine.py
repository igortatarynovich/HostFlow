"""C2.1 PR-2 — Pure Template Renderer (deterministic; no SQL/ORM/I/O)."""

from __future__ import annotations

import re
from typing import Any, Mapping

from backend.app.communications.templates.renderer.types import (
    DIAG_CHANNEL_UNSUPPORTED,
    DIAG_INVALID_TEMPLATE,
    DIAG_MISSING_VARIABLE,
    DIAG_TEMPLATE_NOT_PUBLISHED,
    DIAG_UNKNOWN_VARIABLE,
    DIAG_VERSION_ARCHIVED,
    DIAG_WRONG_TYPE,
    SEVERITY_ERROR,
    TemplateVersionPayload,
    Diagnostic,
    RenderResult,
)
from backend.app.communications.templates.renderer.typing_check import (
    check_value_type,
    coerce_for_render,
    normalize_var_type,
)

_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _diag(
    code: str,
    message: str,
    *,
    path: str | None = None,
    details: Mapping[str, Any] | None = None,
    severity: str = SEVERITY_ERROR,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        path=path,
        details=dict(details or {}),
    )


def _collect_placeholders(*texts: str | None) -> tuple[str, ...]:
    found: list[str] = []
    seen: set[str] = set()
    for text in texts:
        if not text:
            continue
        for match in _VAR_RE.finditer(str(text)):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                found.append(name)
    return tuple(found)


def _status_diagnostics(payload: TemplateVersionPayload) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    if not str(payload.template_version_id or "").strip():
        out.append(
            _diag(
                DIAG_INVALID_TEMPLATE,
                "template_version_id is required",
                path="template_version_id",
            )
        )
    status = str(payload.status or "").strip().lower()
    if status != "published":
        out.append(
            _diag(
                DIAG_TEMPLATE_NOT_PUBLISHED,
                f"TemplateVersion status is {status or 'missing'!r}, expected 'published'",
                path="status",
                details={"status": status},
            )
        )
    tpl_status = str(payload.template_status or "").strip().lower()
    if tpl_status == "archived":
        out.append(
            _diag(
                DIAG_VERSION_ARCHIVED,
                "Template is archived and cannot be rendered",
                path="template_status",
                details={"template_status": tpl_status},
            )
        )
    return out


def _channel_diagnostics(payload: TemplateVersionPayload, channel: str) -> list[Diagnostic]:
    ch = str(channel or "").strip().lower()
    if not ch:
        return [
            _diag(
                DIAG_CHANNEL_UNSUPPORTED,
                "channel is required",
                path="channel",
            )
        ]
    allowed = frozenset(str(c).strip().lower() for c in (payload.channels or frozenset()) if c)
    if ch not in allowed:
        return [
            _diag(
                DIAG_CHANNEL_UNSUPPORTED,
                f"Channel {ch!r} is not bound on this template version",
                path="channel",
                details={"channel": ch, "allowed": sorted(allowed)},
            )
        ]
    return []


def _variable_diagnostics(
    payload: TemplateVersionPayload,
    variables: Mapping[str, Any],
) -> list[Diagnostic]:
    out: list[Diagnostic] = []
    provided = {str(k): v for k, v in dict(variables or {}).items()}
    specs = {str(s.name): s for s in (payload.variables or ())}

    for name, spec in specs.items():
        present = name in provided and provided[name] is not None
        if not present:
            if spec.default_value is not None:
                provided[name] = spec.default_value
                present = True
            elif spec.required:
                out.append(
                    _diag(
                        DIAG_MISSING_VARIABLE,
                        f"Missing required variable: {name}",
                        path=f"variables.{name}",
                        details={"name": name, "var_type": spec.var_type},
                    )
                )
                continue
            else:
                continue
        err = check_value_type(
            var_type=spec.var_type,
            value=provided[name],
            enum_values=tuple(spec.enum_values or ()),
        )
        if err:
            out.append(
                _diag(
                    DIAG_WRONG_TYPE,
                    f"Variable {name!r}: {err}",
                    path=f"variables.{name}",
                    details={
                        "name": name,
                        "var_type": normalize_var_type(spec.var_type),
                        "reason": err,
                    },
                )
            )

    for name in sorted(provided.keys()):
        if name not in specs:
            out.append(
                _diag(
                    DIAG_UNKNOWN_VARIABLE,
                    f"Unknown variable: {name}",
                    path=f"variables.{name}",
                    details={"name": name, "policy": "error"},
                )
            )

    # Placeholders in body that are not declared in schema → missing_variable
    placeholders = _collect_placeholders(
        payload.subject, payload.body_text, payload.body_html
    )
    for name in placeholders:
        if name not in specs:
            out.append(
                _diag(
                    DIAG_MISSING_VARIABLE,
                    f"Template references undeclared variable: {name}",
                    path=f"template.{name}",
                    details={"name": name},
                )
            )
    return out


def _resolved_values(
    payload: TemplateVersionPayload,
    variables: Mapping[str, Any],
) -> dict[str, str]:
    provided = {str(k): v for k, v in dict(variables or {}).items()}
    out: dict[str, str] = {}
    for spec in payload.variables or ():
        name = str(spec.name)
        raw = provided.get(name, spec.default_value)
        if raw is None:
            out[name] = ""
        else:
            out[name] = coerce_for_render(var_type=spec.var_type, value=raw)
    return out


def _substitute(template: str | None, values: Mapping[str, str]) -> str | None:
    if template is None:
        return None

    def _replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return values.get(name, "")

    return _VAR_RE.sub(_replace, str(template))


def _locale(payload: TemplateVersionPayload, locale: str | None) -> str:
    if locale is not None and str(locale).strip():
        return str(locale).strip().lower()[:16]
    return str(payload.locale or "pl").strip().lower()[:16] or "pl"


def validate(
    payload: TemplateVersionPayload,
    *,
    variables: Mapping[str, Any],
    channel: str,
    locale: str | None = None,
) -> RenderResult:
    """Validate only — no content substitution in result bodies."""
    diags = (
        _status_diagnostics(payload)
        + _channel_diagnostics(payload, channel)
        + _variable_diagnostics(payload, variables)
    )
    # Stable diagnostic order for determinism
    diags_sorted = tuple(
        sorted(diags, key=lambda d: (d.code, d.path or "", d.message))
    )
    ok = not any(d.severity == SEVERITY_ERROR for d in diags_sorted)
    return RenderResult(
        ok=ok,
        template_version_id=str(payload.template_version_id),
        subject=None,
        body_text=None,
        body_html=None,
        diagnostics=diags_sorted,
        locale=_locale(payload, locale),
        channel=str(channel or "").strip().lower(),
    )


def diagnostics(
    payload: TemplateVersionPayload,
    *,
    variables: Mapping[str, Any],
    channel: str,
    locale: str | None = None,
) -> tuple[Diagnostic, ...]:
    return validate(
        payload, variables=variables, channel=channel, locale=locale
    ).diagnostics


def _render_common(
    payload: TemplateVersionPayload,
    *,
    variables: Mapping[str, Any],
    channel: str,
    locale: str | None,
) -> RenderResult:
    base = validate(payload, variables=variables, channel=channel, locale=locale)
    if not base.ok:
        return base
    values = _resolved_values(payload, variables)
    return RenderResult(
        ok=True,
        template_version_id=str(payload.template_version_id),
        subject=_substitute(payload.subject, values),
        body_text=_substitute(payload.body_text, values),
        body_html=_substitute(payload.body_html, values),
        diagnostics=base.diagnostics,
        locale=base.locale,
        channel=base.channel,
    )


def preview(
    payload: TemplateVersionPayload,
    *,
    variables: Mapping[str, Any],
    channel: str,
    locale: str | None = None,
) -> RenderResult:
    """Operator preview — same engine as render (deterministic)."""
    return _render_common(
        payload, variables=variables, channel=channel, locale=locale
    )


def render(
    payload: TemplateVersionPayload,
    *,
    variables: Mapping[str, Any],
    channel: str,
    locale: str | None = None,
) -> RenderResult:
    """Final render for the platform pipeline — identical to preview for same inputs."""
    return _render_common(
        payload, variables=variables, channel=channel, locale=locale
    )


__all__ = [
    "validate",
    "preview",
    "render",
    "diagnostics",
]
