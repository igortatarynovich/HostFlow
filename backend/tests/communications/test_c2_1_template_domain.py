"""C2.1 PR-1 — Template domain invariants (no UI / no product API)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.communications.command import (
    CommunicationCommand,
    CommunicationOrigin,
    CommunicationRecipient,
    SendCommunicationContent,
)
from backend.app.communications.intent import CommunicationIntent
from backend.app.communications.snapshot import build_outbound_snapshot
from backend.app.communications.templates import (
    TemplateDomainError,
    create_template_with_draft,
    get_draft_version,
    publish_draft,
    replace_draft_variables,
    update_draft_content,
)
from backend.app.communications.templates.lifecycle import assert_version_immutable_for_write
from backend.app.models.communication_template import (
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    CommunicationTemplateVersion,
)

REPO = Path(__file__).resolve().parents[2]
TEMPLATES_PKG = REPO / "app" / "communications" / "templates"
TEMPLATE_MODEL = REPO / "app" / "models" / "communication_template.py"

FORBIDDEN_MODULE_IMPORT_PREFIXES = (
    "backend.app.modules.recruitment",
    "backend.app.modules.sales",
    "backend.app.modules.hr",
    "backend.app.modules.services",
    "backend.app.modules.finance",
    "app.modules.recruitment",
    "app.modules.sales",
    "app.modules.hr",
    "app.modules.services",
    "app.modules.finance",
)


def _iter_py_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in root.rglob("*.py"):
        yield path


def test_capability_isolation_no_module_imports():
    offenders: list[str] = []
    for path in (*_iter_py_files(TEMPLATES_PKG), TEMPLATE_MODEL):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_MODULE_IMPORT_PREFIXES):
                    offenders.append(f"{path.name}: from {mod}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if any(
                        name == p or name.startswith(p + ".")
                        for p in FORBIDDEN_MODULE_IMPORT_PREFIXES
                    ):
                        offenders.append(f"{path.name}: import {name}")
    assert offenders == [], f"C2.1 capability isolation violated: {offenders}"


def test_communication_command_has_template_version_id_field():
    cmd = CommunicationCommand(
        tenant_id="t",
        origin=CommunicationOrigin(entity_type="candidate", entity_id="c1"),
        recipients=[CommunicationRecipient(address="a@b.c")],
        channel="email",
        intent=CommunicationIntent.MANUAL_OUTBOUND,
        content=SendCommunicationContent(subject="s", body_text="b"),
        template_key="k",
        template_version=2,
        template_version_id="version-uuid",
    )
    assert cmd.template_version_id == "version-uuid"
    snap = build_outbound_snapshot(cmd)
    assert snap.template_version_id == "version-uuid"
    assert snap.to_dict()["template_version_id"] == "version-uuid"


@pytest.mark.asyncio
async def test_publish_creates_immutable_version_and_keeps_draft(db, tenant_id: str):
    template, draft = await create_template_with_draft(
        db,
        tenant_id=tenant_id,
        key="c2_1_smoke_invite",
        name="C2.1 Smoke Invite",
        subject="Hello {{contact_name}}",
        body_text="Body {{contact_name}}",
        channels=["email"],
        intent_keys=["questionnaire_invite"],
        variables=[{"name": "contact_name", "var_type": "string", "required": True}],
    )
    assert draft.status == VERSION_STATUS_DRAFT
    assert draft.version_number == 0

    published = await publish_draft(
        db,
        tenant_id=tenant_id,
        template_id=str(template.id),
        actor_user_id="actor-1",
    )
    assert published.status == VERSION_STATUS_PUBLISHED
    assert published.version_number == 1
    assert published.id != draft.id
    assert published.subject == "Hello {{contact_name}}"
    assert published.published_at is not None

    # Draft still editable.
    draft2 = await get_draft_version(db, tenant_id=tenant_id, template_id=str(template.id))
    assert draft2.id == draft.id
    await update_draft_content(
        db,
        tenant_id=tenant_id,
        version=draft2,
        subject="Edited draft",
    )
    assert draft2.subject == "Edited draft"

    # Published row must not be mutated via domain guard.
    with pytest.raises(TemplateDomainError) as exc:
        assert_version_immutable_for_write(published)
    assert exc.value.code == "published_immutable"

    with pytest.raises(TemplateDomainError) as exc2:
        await update_draft_content(
            db,
            tenant_id=tenant_id,
            version=published,
            subject="hack",
        )
    assert exc2.value.code == "version_not_draft"

    # Second publish creates version 2; v1 unchanged.
    published2 = await publish_draft(
        db,
        tenant_id=tenant_id,
        template_id=str(template.id),
    )
    assert published2.version_number == 2
    assert published2.subject == "Edited draft"

    v1 = (
        await db.execute(
            select(CommunicationTemplateVersion).where(
                CommunicationTemplateVersion.id == published.id
            )
        )
    ).scalar_one()
    assert v1.subject == "Hello {{contact_name}}"
    assert v1.status == VERSION_STATUS_PUBLISHED


@pytest.mark.asyncio
async def test_cannot_replace_variables_on_published(db, tenant_id: str):
    template, _draft = await create_template_with_draft(
        db,
        tenant_id=tenant_id,
        key="c2_1_pub_vars",
        name="pub vars",
        channels=["email"],
    )
    published = await publish_draft(
        db, tenant_id=tenant_id, template_id=str(template.id)
    )
    with pytest.raises(TemplateDomainError) as exc:
        await replace_draft_variables(
            db,
            tenant_id=tenant_id,
            version=published,
            variables=[{"name": "x", "var_type": "string"}],
        )
    assert exc.value.code == "version_not_draft"
