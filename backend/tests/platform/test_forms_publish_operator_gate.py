"""Operator Publish Gate (FP-4).

Form UI → existing FP-2 publish / lifecycle → refresh → existing FP-3
publication state / public URL. UI displays authority; it is not a new
authority. Embed snippet is a later product slice.
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import AsyncClient

from backend.app.entity_profile.constants import WAREHOUSE_WORKER_PROFILE_CODE
from backend.app.forms_platform.operator_publication import (
    PUBLIC_FORM_PATH,
    operator_state_from_lead_form,
    public_form_url_from_publication,
)
from backend.app.reference.forms_publish_contract import (
    OPERATOR_STATES,
    PRODUCT_ROUTE_REL,
    WRITE_API,
    leftover_answerers,
)
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs/specs/tasks/external-intake-forms-publish.md"
_ARCH = _REPO_ROOT / "docs/specs/architecture/forms-publish-contract.md"
_QUEUE = _REPO_ROOT / "docs/specs/tasks/sales-to-comms-sequential-queue.md"
_CI = _REPO_ROOT / ".github/workflows/backend-ci.yml"
_PRODUCT_ROUTE = _REPO_ROOT / PRODUCT_ROUTE_REL
_OPERATOR = _REPO_ROOT / "backend/app/forms_platform/operator_publication.py"
_FRONTEND_PAGE = _REPO_ROOT / "hostflow-frontend/src/pages/admin/FormsBuilderPage.tsx"
_FRONTEND_API = _REPO_ROOT / "hostflow-frontend/src/api/formsPublications.ts"

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


def test_fp4_gate_filename() -> None:
    assert Path(__file__).name == "test_forms_publish_operator_gate.py"


def test_fp4_operator_state_is_consume_of_existing_authority() -> None:
    never = SimpleNamespace(published_version=0, published_snapshot_v1=None, is_active=True, lifecycle_status="active")
    live = SimpleNamespace(
        published_version=1,
        published_snapshot_v1={"field_schema": {"schema_contract": "forms.field_schema.v1"}},
        is_active=True,
        lifecycle_status="active",
    )
    inactive = SimpleNamespace(
        published_version=1,
        published_snapshot_v1={"field_schema": {"schema_contract": "forms.field_schema.v1"}},
        is_active=False,
        lifecycle_status="active",
    )
    assert operator_state_from_lead_form(never) == "never_published"
    assert operator_state_from_lead_form(live) == "live"
    assert operator_state_from_lead_form(inactive) == "inactive"
    assert public_form_url_from_publication(public_slug="drivers", operator_state="live") == (
        f"{PUBLIC_FORM_PATH}?lead_form_slug=drivers"
    )
    assert public_form_url_from_publication(public_slug="drivers", operator_state="inactive") is None
    assert public_form_url_from_publication(public_slug="drivers", operator_state="never_published") is None
    for state in ("never_published", "live", "inactive"):
        assert state in OPERATOR_STATES
    text = _OPERATOR.read_text(encoding="utf-8")
    assert f"def {WRITE_API}(" not in text
    assert "serve(" not in text


def test_fp4_unpublish_is_lifecycle_consume_not_a_write() -> None:
    text = _PRODUCT_ROUTE.read_text(encoding="utf-8")
    assert f"async def {WRITE_API}(" not in text
    assert f"await {WRITE_API}(" in text
    assert "await deactivate_endpoint(" in text
    assert "/{form_id}/unpublish" in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
    assert "backend.app.forms_platform.adapter" in imports
    assert "backend.app.forms_platform.runtime.serve" not in imports
    leftovers = leftover_answerers()
    assert leftovers == ()


def test_fp4_ui_displays_authority_and_does_not_become_one() -> None:
    page = _FRONTEND_PAGE.read_text(encoding="utf-8")
    api = _FRONTEND_API.read_text(encoding="utf-8")
    assert "fetchFormPublication" in page
    assert "publishFormPublication" in page
    assert "unpublishFormPublication" in page
    assert "setPublication(next)" in page
    assert "setPublication(pub)" in page
    assert "operator_state" in page
    assert "public_form_url" in page
    assert "publicIntakeUrlForSlug" not in page
    assert "is_active &&" not in page
    assert "isLive(" not in page
    assert "operator_state:" not in page
    assert "public_form_url:" not in page
    assert "embed" not in page.lower()
    assert "iframe" not in page.lower()
    assert "/platform/forms/publications/resolve" in api
    assert "/publish" in api
    assert "/unpublish" in api
    assert "lead_form_slug=" not in api


def test_fp4_brief_and_named_ci() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "Operator Publish Gate" in current
    assert "**PASS**" in current
    assert "feat/forms-publish-fp4-operator-surface" in current
    assert "commit_publish" in current
    assert "Never published" in current or "never_published" in current
    assert "embed snippet" in current.lower() or "Embed snippet" in brief
    arch = _ARCH.read_text(encoding="utf-8")
    gate = arch.split("## Operator Publish Gate", 1)[1].split("## ", 1)[0]
    assert "**PASS**" in gate
    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "Operator Publish Gate **PASS**" in queue_current
    assert "feat/forms-publish-fp5-runtime" in queue_current
    assert "External Intake Acceptance Gate **PASS**" in queue_current
    ci = _CI.read_text(encoding="utf-8")
    assert "Operator Publish Gate" in ci
    assert "test_forms_publish_operator_gate.py" in ci


async def _create_form(client: AsyncClient, tenant_id: str) -> tuple[str, str, dict[str, str]]:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"fp4-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "FP-4 Operator Surface",
            "public_slug": slug,
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    return created.json()["form"]["id"], slug, headers


async def _resolve(client: AsyncClient, headers: dict[str, str], form_id: str) -> dict:
    resp = await client.get(
        "/api/v1/platform/forms/publications/resolve",
        headers=headers,
        params={"form_id": form_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_fp4_operator_close_path(client: AsyncClient, tenant_id: str) -> None:
    """Never published → Publish → Live v1 + URL → Unpublish → Inactive + URL absent.

    After each act the displayed state is a fresh resolve of backend authority,
    not the write response kept as a local publication store.
    """
    from backend.app.db.session import async_session_maker
    from backend.app.models.form_publication_version import FormPublicationVersion
    from sqlalchemy import func, select

    form_id, slug, headers = await _create_form(client, tenant_id)
    never = await _resolve(client, headers, form_id)
    assert never["operator_state"] == "never_published"
    assert never["public_form_url"] is None

    unauth = await client.post(f"/api/v1/platform/forms/{form_id}/unpublish", json={})
    assert unauth.status_code in {401, 403}

    published = await client.post(
        f"/api/v1/platform/forms/{form_id}/publish",
        headers={**headers, "Idempotency-Key": f"fp4-{form_id}"},
        json={
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
            ]
        },
    )
    assert published.status_code == 200, published.text
    live = await _resolve(client, headers, form_id)
    assert live["operator_state"] == "live"
    assert live["public_form_url"] == f"/public/intake?lead_form_slug={slug}"
    assert int(live["published_version"]) == 1
    assert live["operator_state"] == published.json()["operator_state"]
    assert live["public_form_url"] == published.json()["public_form_url"]

    unpublished = await client.post(
        f"/api/v1/platform/forms/{form_id}/unpublish",
        headers=headers,
    )
    assert unpublished.status_code == 200, unpublished.text
    inactive = await _resolve(client, headers, form_id)
    assert inactive["operator_state"] == "inactive"
    assert inactive["public_form_url"] is None
    assert int(inactive["published_version"]) == 1
    assert inactive["operator_state"] == unpublished.json()["operator_state"]
    assert inactive["public_form_url"] == unpublished.json()["public_form_url"]

    async with async_session_maker() as session:
        rows = int(
            await session.scalar(
                select(func.count()).select_from(FormPublicationVersion).where(
                    FormPublicationVersion.form_id == form_id
                )
            )
            or 0
        )
    assert rows == 1
