"""Publish Action Gate (FP-2).

Authenticated product route → Adapter commit_publish → form_publication_versions.
Presentation / Form Definition leftover version bumps are retired.
Republish is idempotent per identity. Not FP-3 serve/embed. Not Hiring E2E.
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.entity_profile.constants import WAREHOUSE_WORKER_PROFILE_CODE
from backend.app.models.form_publication_version import FormPublicationVersion
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.reference.forms_publish_contract import (
    PRODUCT_ROUTE_PATH,
    PRODUCT_ROUTE_REL,
    WRITE_API,
    WRITE_PRODUCER_REL,
    leftover_answerers,
)
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ROUTE = _REPO_ROOT / PRODUCT_ROUTE_REL
_WRITE_SERVICE = _REPO_ROOT / "backend/app/services/intake_form_write_service.py"
_FORM_DEFINITION = _REPO_ROOT / "backend/app/intake_platform/form_definition.py"
_BRIEF = _REPO_ROOT / "docs/specs/tasks/external-intake-forms-publish.md"
_ARCH = _REPO_ROOT / "docs/specs/architecture/forms-publish-contract.md"
_QUEUE = _REPO_ROOT / "docs/specs/tasks/sales-to-comms-sequential-queue.md"
_CI = _REPO_ROOT / ".github/workflows/backend-ci.yml"
_SERVE = "backend.app.forms_platform.runtime.serve"
_EMBED_MARKERS = (
    "backend.app.forms_platform.runtime",
    "backend.app.entity_profile.public_intake_presentation_bridge",
    "backend.app.api.public.intake",
)

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _bypass_lead_source_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _noop(*args, **kwargs):  # noqa: ANN002, ANN003
        return None

    async def _zero(*args, **kwargs):  # noqa: ANN002, ANN003
        return 0

    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_lead_source_limit",
        _noop,
    )
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.count_tenant_lead_sources",
        _zero,
    )
    monkeypatch.setattr(
        "backend.app.services.intake_form_write_service.ensure_tenant_lead_form_active_count_allows_transition",
        _noop,
    )


def test_fp2_gate_filename() -> None:
    assert Path(__file__).name == "test_forms_publish_action_gate.py"


def test_fp2_product_route_calls_commit_publish_only() -> None:
    text = _ROUTE.read_text(encoding="utf-8")
    assert f"async def {WRITE_API}(" not in text
    assert f"await {WRITE_API}(" in text
    assert WRITE_PRODUCER_REL.split("/")[-1].replace(".py", "") in text or "commit_publish" in text
    assert PRODUCT_ROUTE_PATH.split("/platform/")[-1] in text or "/{form_id}/publish" in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
    assert _SERVE not in imports
    for marker in _EMBED_MARKERS:
        assert marker not in imports
    assert "backend.app.forms_platform.adapter" in imports


def test_fp2_leftover_version_bumps_retired() -> None:
    write_src = _WRITE_SERVICE.read_text(encoding="utf-8")
    assert "lead_form.published_version = int(getattr(lead_form, \"published_version\"" not in write_src
    assert "published_version=1," not in write_src
    leftovers = leftover_answerers()
    assert "intake_form_write_service_version_bump" not in {row.code for row in leftovers}
    assert "form_definition_published_version_write" not in {row.code for row in leftovers}

    tree = ast.parse(_FORM_DEFINITION.read_text(encoding="utf-8"))
    apply_fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "apply_form_definition_fields"
    )
    assigned: list[str] = []
    for node in ast.walk(apply_fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Attribute) and target.attr == "published_version":
                    assigned.append("published_version")
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute):
            if node.target.attr == "published_version":
                assigned.append("published_version")
    assert assigned == []


def test_fp2_brief_and_named_ci() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "Publish Action Gate" in current
    assert "**PASS**" in current
    assert "feat/forms-publish-fp2-publish-action" in current
    assert "commit_publish" in current
    assert "/public/intake" in brief or "FP-3" in current
    arch = _ARCH.read_text(encoding="utf-8")
    assert "## Publish Action Gate" in arch
    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "Publish Action Gate **PASS**" in queue_current
    assert "feat/forms-publish-fp3-public-serve" in queue_current
    assert "feat/forms-publish-fp4-operator-surface" in queue_current
    assert "Public Serve Gate **PASS**" in queue_current
    assert "Operator Publish Gate **not PASS**" in queue_current
    assert "This stamp does not ship operator UI" in queue_current or "This stamp does not ship operator UI" in queue
    ci = _CI.read_text(encoding="utf-8")
    assert "Publish Action Gate" in ci
    assert "test_forms_publish_action_gate.py" in ci


async def _create_form(client: AsyncClient, tenant_id: str) -> tuple[str, dict[str, str]]:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"fp2-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "FP-2 Publish Action",
            "public_slug": slug,
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    return created.json()["form"]["id"], headers


@pytest.mark.asyncio
async def test_fp2_unauthenticated_publish_rejected(client: AsyncClient, tenant_id: str) -> None:
    form_id, _headers = await _create_form(client, tenant_id)
    resp = await client.post(f"/api/v1/platform/forms/{form_id}/publish", json={})
    assert resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_fp2_authenticated_publish_commits_ledger(
    client: AsyncClient, tenant_id: str
) -> None:
    from backend.app.db.session import async_session_maker

    form_id, headers = await _create_form(client, tenant_id)
    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        assert form is not None
        assert int(form.published_version or 0) == 0
        before = await session.scalar(
            select(func.count()).select_from(FormPublicationVersion).where(
                FormPublicationVersion.form_id == form_id
            )
        )
    assert int(before or 0) == 0

    saved = await client.put(
        f"/api/v1/settings/intake-forms/{form_id}/presentation",
        headers=headers,
        json={
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {
                    "qualified_code": "recruitment.candidate.first_name",
                    "intake_level": "required",
                    "sort_order": 10,
                }
            ],
        },
    )
    assert saved.status_code == 200, saved.text
    async with async_session_maker() as session:
        form = await session.get(TenantLeadForm, form_id)
        assert form is not None
        assert int(form.published_version or 0) == 0

    first = await client.post(
        f"/api/v1/platform/forms/{form_id}/publish",
        headers={**headers, "Idempotency-Key": f"fp2-{form_id}"},
        json={},
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["publication_id"] == form_id
    assert body["published_version"] == 1
    assert body.get("has_immutable_snapshot") is True
    assert body.get("contract_identity")
    assert body.get("idempotent_replay") is not True

    replay = await client.post(
        f"/api/v1/platform/forms/{form_id}/publish",
        headers={**headers, "Idempotency-Key": f"fp2-{form_id}"},
        json={},
    )
    assert replay.status_code == 200, replay.text
    replayed = replay.json()
    assert replayed.get("idempotent_replay") is True
    assert replayed["published_version"] == 1
    assert replayed.get("replayed_version") == 1

    async with async_session_maker() as session:
        rows = (
            await session.scalars(
                select(FormPublicationVersion).where(FormPublicationVersion.form_id == form_id)
            )
        ).all()
        form = await session.get(TenantLeadForm, form_id)
    assert len(rows) == 1
    assert int(rows[0].version) == 1
    assert form is not None
    assert int(form.published_version) == 1
