"""C2.1 PR-2 — Pure Template Renderer contract tests."""

from __future__ import annotations

import ast
from pathlib import Path

from backend.app.communications.templates.payload import build_payload
from backend.app.communications.templates.renderer import (
    preview,
    render,
    validate,
)
from backend.app.communications.templates.renderer.types import (
    DIAG_CHANNEL_UNSUPPORTED,
    DIAG_MISSING_VARIABLE,
    DIAG_TEMPLATE_NOT_PUBLISHED,
    DIAG_UNKNOWN_VARIABLE,
    DIAG_VERSION_ARCHIVED,
    DIAG_WRONG_TYPE,
    TemplateVariableSpec,
)

RENDERER_DIR = (
    Path(__file__).resolve().parents[2] / "app" / "communications" / "templates" / "renderer"
)

FORBIDDEN_IMPORT_PREFIXES = (
    "sqlalchemy",
    "backend.app.db",
    "app.db",
    "backend.app.models",
    "app.models",
    "backend.app.communications.workspace_commands",
    "backend.app.communications.send_communication",
    "backend.app.communications.execute_intent",
    "backend.app.modules",
    "app.modules",
)


def _published_payload(**overrides):
    base = dict(
        template_version_id="ver-1",
        status="published",
        template_status="active",
        locale="pl",
        subject="Hello {{contact_name}}",
        body_text="Body {{contact_name}} link {{url}}",
        body_html=None,
        channels=["email"],
        variables=[
            TemplateVariableSpec(name="contact_name", var_type="string", required=True),
            TemplateVariableSpec(name="url", var_type="url", required=True),
        ],
    )
    base.update(overrides)
    return build_payload(**base)


def test_pure_renderer_import_gate():
    offenders: list[str] = []
    for path in RENDERER_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            if isinstance(node, ast.Import):
                mods.extend(a.name for a in node.names)
            for mod in mods:
                if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES):
                    offenders.append(f"{path.name}: {mod}")
    assert offenders == [], f"Pure renderer gate violated: {offenders}"


def test_validate_ok_and_render_deterministic():
    payload = _published_payload()
    variables = {
        "contact_name": "Anna",
        "url": "https://hostflow.cc/q/1",
    }
    v1 = validate(payload, variables=variables, channel="email", locale="pl")
    assert v1.ok is True
    assert v1.diagnostics == ()
    assert v1.subject is None  # validate does not substitute

    r1 = render(payload, variables=variables, channel="email", locale="pl")
    r2 = render(payload, variables=variables, channel="email", locale="pl")
    p1 = preview(payload, variables=variables, channel="email", locale="pl")
    assert r1.ok is True
    assert r1 == r2
    assert r1 == p1
    assert r1.subject == "Hello Anna"
    assert "https://hostflow.cc/q/1" in (r1.body_text or "")
    assert r1.to_dict() == r2.to_dict()


def test_missing_wrong_unknown_channel_status_diagnostics():
    payload = _published_payload()

    missing = validate(payload, variables={"url": "https://x.test"}, channel="email")
    assert missing.ok is False
    assert any(d.code == DIAG_MISSING_VARIABLE for d in missing.diagnostics)

    wrong = validate(
        payload,
        variables={"contact_name": "A", "url": "not-a-url"},
        channel="email",
    )
    assert wrong.ok is False
    assert any(d.code == DIAG_WRONG_TYPE for d in wrong.diagnostics)

    unknown = validate(
        payload,
        variables={
            "contact_name": "A",
            "url": "https://x.test",
            "extra": "nope",
        },
        channel="email",
    )
    assert unknown.ok is False
    assert any(d.code == DIAG_UNKNOWN_VARIABLE for d in unknown.diagnostics)

    channel = validate(
        payload,
        variables={"contact_name": "A", "url": "https://x.test"},
        channel="whatsapp",
    )
    assert channel.ok is False
    assert any(d.code == DIAG_CHANNEL_UNSUPPORTED for d in channel.diagnostics)

    draft = validate(
        _published_payload(status="draft"),
        variables={"contact_name": "A", "url": "https://x.test"},
        channel="email",
    )
    assert draft.ok is False
    assert any(d.code == DIAG_TEMPLATE_NOT_PUBLISHED for d in draft.diagnostics)

    archived = validate(
        _published_payload(template_status="archived"),
        variables={"contact_name": "A", "url": "https://x.test"},
        channel="email",
    )
    assert archived.ok is False
    assert any(d.code == DIAG_VERSION_ARCHIVED for d in archived.diagnostics)


def test_typed_boolean_and_enum():
    payload = build_payload(
        template_version_id="ver-2",
        status="published",
        template_status="active",
        locale="en",
        subject="Flag {{flag}} mode {{mode}}",
        body_text="ok",
        channels=["email"],
        variables=[
            TemplateVariableSpec(name="flag", var_type="boolean", required=True),
            TemplateVariableSpec(
                name="mode",
                var_type="enum",
                required=True,
                enum_values=("a", "b"),
            ),
        ],
    )
    ok = render(
        payload,
        variables={"flag": True, "mode": "a"},
        channel="email",
    )
    assert ok.ok is True
    assert ok.subject == "Flag true mode a"

    bad = validate(
        payload,
        variables={"flag": "maybe", "mode": "z"},
        channel="email",
    )
    assert bad.ok is False
    codes = {d.code for d in bad.diagnostics}
    assert DIAG_WRONG_TYPE in codes


def test_failed_render_does_not_emit_partial_content():
    payload = _published_payload()
    result = render(
        payload,
        variables={"contact_name": "A"},  # missing url
        channel="email",
    )
    assert result.ok is False
    assert result.subject is None
    assert result.body_text is None
