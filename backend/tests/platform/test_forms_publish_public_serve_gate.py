"""Public Serve Gate (FP-3).

public request → Adapter resolve live publication → frozen
form_publication_versions snapshot → canonical Form Runtime.

Unpublished / inactive forms are not served as live.
form_presentation_runtime_v1 is not public-serve authority for HostFlow forms.
No second public renderer. FP-2 publish-write semantics unchanged.
Not FP-4 snippet / distribution UX. Not leftover-store deletion. Not Hiring.
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.entity_profile.constants import WAREHOUSE_WORKER_PROFILE_CODE
from backend.app.forms_platform.adapter import deactivate_endpoint
from backend.app.forms_platform.runtime.model import RUNTIME_MODEL_CONTRACT
from backend.app.models.form_publication_version import FormPublicationVersion
from backend.app.models.tenant_lead_form import TenantLeadForm
from backend.app.reference.forms_publish_contract import (
    PRODUCT_ROUTE_REL,
    WRITE_API,
    leftover_answerers,
)
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles
from backend.tests.api.test_public_intake import _headers, _seed_active_lead_form

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs/specs/tasks/external-intake-forms-publish.md"
_ARCH = _REPO_ROOT / "docs/specs/architecture/forms-publish-contract.md"
_QUEUE = _REPO_ROOT / "docs/specs/tasks/sales-to-comms-sequential-queue.md"
_CI = _REPO_ROOT / ".github/workflows/backend-ci.yml"
_INTAKE = _REPO_ROOT / "backend/app/api/public/intake.py"
_BRIDGE = _REPO_ROOT / "backend/app/forms_platform/public_serve_bridge.py"
_FRONTEND = _REPO_ROOT / "hostflow-frontend/src/pages/public/PublicIntakeNew.tsx"
_PRODUCT_ROUTE = _REPO_ROOT / PRODUCT_ROUTE_REL
_PUBLIC_PAGES = _REPO_ROOT / "hostflow-frontend/src/pages/public"

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


def test_fp3_gate_filename() -> None:
    assert Path(__file__).name == "test_forms_publish_public_serve_gate.py"


def test_fp3_leftover_serve_retired() -> None:
    leftovers = leftover_answerers()
    codes = {row.code for row in leftovers}
    assert "entity_profile_presentation_public_serve" not in codes
    assert "public_intake_unbound_no_ledger" not in codes


def test_fp3_one_public_renderer_and_close_path() -> None:
    assert _BRIDGE.is_file()
    bridge = _BRIDGE.read_text(encoding="utf-8")
    assert "resolve_publication" in bridge
    assert "require_active=True" in bridge
    assert "serve(" in bridge
    intake = _INTAKE.read_text(encoding="utf-8")
    assert "public_serve_bridge" in intake
    assert "form_runtime" in intake
    frontend = _FRONTEND.read_text(encoding="utf-8")
    assert "FORM_RUNTIME_MODEL_CONTRACT" in frontend
    assert "formRuntimeToPresentation" in frontend
    renderers = list(_PUBLIC_PAGES.glob("*Runtime*.tsx")) + list(
        _PUBLIC_PAGES.glob("*FormRuntime*.tsx")
    )
    assert renderers == []
    assert (_PUBLIC_PAGES / "PublicIntakePresentationForm.tsx").is_file()


def test_fp3_fp2_write_unchanged() -> None:
    text = _PRODUCT_ROUTE.read_text(encoding="utf-8")
    assert f"async def {WRITE_API}(" not in text
    assert f"await {WRITE_API}(" in text
    tree = ast.parse(text)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
    assert "backend.app.forms_platform.adapter" in imports
    assert "backend.app.forms_platform.runtime.serve" not in imports
    assert "backend.app.forms_platform.public_serve_bridge" not in imports


def test_fp3_brief_and_named_ci() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "Public Serve Gate" in current
    assert "**PASS**" in current
    assert "feat/forms-publish-fp3-public-serve" in current
    assert "form_publication_versions" in current
    assert "Form Runtime" in current
    arch = _ARCH.read_text(encoding="utf-8")
    assert "## Public Serve Gate" in arch
    assert "**PASS**" in arch.split("## Public Serve Gate", 1)[1].split("## ", 1)[0] or (
        "Public Serve Gate" in arch and "**PASS** when:" in arch.split("## Public Serve Gate", 1)[1]
    )
    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "Public Serve Gate **PASS**" in queue_current or "Public Serve Gate** ✅" in queue_current or (
        "**Public Serve Gate** ✅" in queue_current
    )
    assert "feat/forms-publish-fp4-operator-surface" in queue_current
    assert "feat/forms-publish-fp5-external-submit" in queue_current
    assert "Operator Publish Gate **PASS**" in queue_current
    assert "External Intake Acceptance Gate **not PASS**" in queue_current
    ci = _CI.read_text(encoding="utf-8")
    assert "Public Serve Gate" in ci
    assert "test_forms_publish_public_serve_gate.py" in ci
    assert "embed" not in current.lower() or "FP-4" in current


async def _create_and_publish(client: AsyncClient, tenant_id: str) -> tuple[str, str, dict[str, str]]:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"fp3-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "FP-3 Public Serve",
            "public_slug": slug,
            "entity_profile_code": WAREHOUSE_WORKER_PROFILE_CODE,
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
            ],
        },
    )
    assert created.status_code == 200, created.text
    form_id = created.json()["form"]["id"]
    published = await client.post(
        f"/api/v1/platform/forms/{form_id}/publish",
        headers={**headers, "Idempotency-Key": f"fp3-{form_id}"},
        json={
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
            ]
        },
    )
    assert published.status_code == 200, published.text
    return form_id, slug, headers


@pytest.mark.asyncio
async def test_fp3_unpublished_form_not_served_live(client: AsyncClient, tenant_id: str) -> None:
    slug = await _seed_active_lead_form(tenant_id, prefix="fp3-never", publish=False)
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "fp3-never@example.com"}, "lead_form_slug": slug},
    )
    assert create.status_code == 404, create.text
    detail = create.json().get("detail")
    assert isinstance(detail, dict)
    assert detail.get("code") in {
        "forms_publication_version_not_found",
        "forms_publication_not_found",
        "lead_form_not_found",
    }


@pytest.mark.asyncio
async def test_fp3_live_request_serves_frozen_runtime(
    client: AsyncClient, tenant_id: str
) -> None:
    from backend.app.db.session import async_session_maker

    form_id, slug, _headers_admin = await _create_and_publish(client, tenant_id)
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": f"fp3-live-{uuid.uuid4().hex[:8]}@example.com"}, "lead_form_slug": slug},
    )
    assert create.status_code == 200, create.text
    token = create.json()["token"]
    get_resp = await client.get(f"/api/v1/public/apply/{token}", headers=_headers(tenant_id))
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    runtime = body.get("form_runtime")
    assert runtime is not None
    assert runtime.get("contract") == RUNTIME_MODEL_CONTRACT
    assert runtime.get("form_id") == form_id
    assert int(runtime.get("published_version") or 0) >= 1
    field_ids = {
        str(row.get("qualified_code") or row.get("id") or "")
        for row in (runtime.get("fields") or [])
        if isinstance(row, dict)
    }
    assert "recruitment.candidate.first_name" in field_ids
    assert body.get("form_presentation") is None

    async with async_session_maker() as session:
        rows = (
            await session.scalars(
                select(FormPublicationVersion).where(FormPublicationVersion.form_id == form_id)
            )
        ).all()
        form = await session.get(TenantLeadForm, form_id)
    assert len(rows) == 1
    assert form is not None
    assert int(form.published_version or 0) == 1


@pytest.mark.asyncio
async def test_fp3_inactive_form_not_served_live(client: AsyncClient, tenant_id: str) -> None:
    from backend.app.db.session import async_session_maker

    form_id, slug, _headers_admin = await _create_and_publish(client, tenant_id)
    async with async_session_maker() as session:
        await deactivate_endpoint(session, tenant_id=tenant_id, form_id=form_id)
        await session.commit()
    create = await client.post(
        "/api/v1/public/intake",
        headers=_headers(tenant_id),
        json={"contacts": {"email": "fp3-inactive@example.com"}, "lead_form_slug": slug},
    )
    assert create.status_code in {404, 409}, create.text
    detail = create.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") in {
            "forms_endpoint_inactive",
            "lead_form_not_found",
            "forms_publication_not_found",
        }
