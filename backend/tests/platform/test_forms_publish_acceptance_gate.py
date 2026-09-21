"""External Intake Acceptance Gate (FP-5).

live public URL (FP-4) → stranger without auth opens it → fills → submit →
existing C6 / public-submit contracts → production intake → intake entity
visible on the product surface. Browser E2E through that published URL.
No second submit engine. Not Mapping/RS-3. Not Hiring. Not embed snippet.
"""

from __future__ import annotations

import ast
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.entity_profile.constants import WAREHOUSE_WORKER_PROFILE_CODE
from backend.app.forms_platform.runtime.model import RUNTIME_MODEL_CONTRACT
from backend.app.models.candidate import Candidate
from backend.app.models.form_publication_version import FormPublicationVersion
from backend.app.models.lead import Lead
from backend.app.models.tenant import TenantLicense
from backend.app.reference.forms_publish_contract import leftover_answerers
from backend.tests.api.test_intake_forms_settings import _admin_headers
from backend.tests.api.test_intake_forms_settings_p8 import _seed_entity_profiles

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BRIEF = _REPO_ROOT / "docs/specs/tasks/external-intake-forms-publish.md"
_ARCH = _REPO_ROOT / "docs/specs/architecture/forms-publish-contract.md"
_QUEUE = _REPO_ROOT / "docs/specs/tasks/sales-to-comms-sequential-queue.md"
_CI = _REPO_ROOT / ".github/workflows/backend-ci.yml"
_E2E_WORKFLOW = _REPO_ROOT / ".github/workflows/fp5-external-intake-e2e.yml"
_HTTP = _REPO_ROOT / "hostflow-frontend/src/api/http.ts"
_INTAKE = _REPO_ROOT / "backend/app/api/public/intake.py"
_BRIDGE = _REPO_ROOT / "backend/app/forms_platform/public_submit_bridge.py"
_RATE = _REPO_ROOT / "backend/app/core/rate_limit.py"
_E2E = _REPO_ROOT / "e2e/forms-publish-fp5-external-submit.ui.spec.ts"
_START = _REPO_ROOT / "hostflow-frontend/src/pages/public/PublicIntakeStart.tsx"
_PRESENTATION = _REPO_ROOT / "hostflow-frontend/src/pages/public/PublicIntakePresentationForm.tsx"
_OPERATOR = _REPO_ROOT / "hostflow-frontend/src/pages/admin/FormsBuilderPage.tsx"

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
async def _bump_max_candidates_for_fp5(tenant_id: str) -> None:
    """Public submit creates a workspace candidate; default tenant often sits on the license cap."""
    from backend.app.db.session import async_session_maker

    async with async_session_maker() as session:
        lic = (
            await session.execute(select(TenantLicense).where(TenantLicense.tenant_id == tenant_id).limit(1))
        ).scalar_one_or_none()
        if lic is not None:
            lic.max_candidates_active = 500_000
            await session.commit()


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


def test_fp5_gate_filename() -> None:
    assert Path(__file__).name == "test_forms_publish_acceptance_gate.py"


def test_fp5_consumes_existing_submit_contracts() -> None:
    leftovers = leftover_answerers()
    assert leftovers == ()
    bridge = _BRIDGE.read_text(encoding="utf-8")
    assert "resolve_publication" in bridge
    assert "persist_execution" in bridge
    assert "PUBLIC_APPLY_SUBMIT_PATH" in bridge
    intake = _INTAKE.read_text(encoding="utf-8")
    assert "maybe_execute_hostflow_form_public_submit" in intake
    assert "dispatch_public_intake_submit" in intake
    tree = ast.parse(intake)
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    assert "backend.app.forms_platform.public_submit_bridge" in imports
    assert "backend.app.intake_platform.intake_submit_service" in imports
    rate = _RATE.read_text(encoding="utf-8")
    assert "fail-open" in rate
    assert 'scope="public:intake"' in intake


def test_fp5_stranger_http_and_operator_surface() -> None:
    http = _HTTP.read_text(encoding="utf-8")
    assert "function isAnonymousPublicIntakePath" in http
    assert "path.includes('/public/intake')" in http
    assert "delete (config.headers as any)['Authorization']" in http
    assert "delete (config.headers as any)['X-Tenant-Id']" in http
    start = _START.read_text(encoding="utf-8")
    assert "createPublicIntake" in start
    assert "lead_form_slug" in start
    assert 'data-testid="public-intake-email"' in start
    presentation = _PRESENTATION.read_text(encoding="utf-8")
    assert 'data-testid="public-intake-submit"' in presentation
    assert "public-intake-lang-" in presentation
    spec = _E2E.read_text(encoding="utf-8")
    assert "public-intake-lang-en" in spec
    operator = _OPERATOR.read_text(encoding="utf-8")
    assert 'data-testid="form-publish"' in operator
    assert 'data-testid="form-public-url"' in operator


def test_fp5_browser_e2e_is_the_close_proof() -> None:
    assert _E2E.is_file()
    spec = _E2E.read_text(encoding="utf-8")
    assert "lead_form_slug" in spec
    assert "form-publish" in spec
    assert "public-intake-submit" in spec
    assert "/app/candidates" in spec
    assert "storageState: { cookies: [], origins: [] }" in spec
    assert _E2E_WORKFLOW.is_file()
    workflow = _E2E_WORKFLOW.read_text(encoding="utf-8")
    assert "forms-publish-fp5-external-submit.ui.spec.ts" in workflow


def test_fp5_brief_and_named_ci() -> None:
    brief = _BRIEF.read_text(encoding="utf-8")
    current = brief.split("## History", 1)[0]
    assert "External Intake Acceptance Gate" in current
    assert "**PASS**" in current
    assert "feat/forms-publish-fp5-runtime" in current
    assert "browser" in current.lower()
    arch = _ARCH.read_text(encoding="utf-8")
    gate = arch.split("## External Intake Acceptance Gate", 1)[1].split("## ", 1)[0]
    assert "**PASS**" in gate
    assert "browser" in gate.lower()
    queue = _QUEUE.read_text(encoding="utf-8")
    queue_current = queue.split("## 8. History", 1)[0]
    assert "External Intake Acceptance Gate **PASS**" in queue_current
    assert "feat/forms-publish-fp5-runtime" in queue_current
    assert "This stamp does not ship runtime" not in queue_current
    ci = _CI.read_text(encoding="utf-8")
    assert "External Intake Acceptance Gate" in ci
    assert "test_forms_publish_acceptance_gate.py" in ci
    false_close = arch.split("## False close", 1)[1].split("## ", 1)[0]
    assert "inherited red" in false_close.lower()
    assert "54537f00" in false_close


async def _create_and_publish(client: AsyncClient, tenant_id: str) -> tuple[str, str, dict[str, str]]:
    await _seed_entity_profiles(tenant_id)
    headers = await _admin_headers(tenant_id)
    slug = f"fp5-{uuid.uuid4().hex[:8]}"
    created = await client.post(
        "/api/v1/settings/intake-forms",
        headers=headers,
        json={
            "title": "FP-5 External Submit",
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
    form_id = created.json()["form"]["id"]
    published = await client.post(
        f"/api/v1/platform/forms/{form_id}/publish",
        headers={**headers, "Idempotency-Key": f"fp5-{form_id}"},
        json={
            "fields": [
                {"qualified_code": "recruitment.candidate.first_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.last_name", "intake_level": "required"},
                {"qualified_code": "recruitment.candidate.contacts.phone", "intake_level": "required"},
            ]
        },
    )
    assert published.status_code == 200, published.text
    return form_id, slug, headers


@pytest.mark.asyncio
async def test_fp5_stranger_submit_creates_workspace_entity(
    client: AsyncClient, tenant_id: str
) -> None:
    """Published live URL → unauthenticated submit → product list shows the entity.

    Stranger calls send no Authorization and no X-Tenant-Id. The intake entity is
    created only by production public submit, not by a helper candidates/leads write.
    """
    from backend.app.db.session import async_session_maker

    form_id, slug, headers = await _create_and_publish(client, tenant_id)
    resolve = await client.get(
        "/api/v1/platform/forms/publications/resolve",
        headers=headers,
        params={"form_id": form_id},
    )
    assert resolve.status_code == 200, resolve.text
    live = resolve.json()
    assert live["operator_state"] == "live"
    assert live["public_form_url"] == f"/public/intake?lead_form_slug={slug}"

    email = f"fp5-stranger-{uuid.uuid4().hex[:8]}@example.com"
    phone = f"+4811{uuid.uuid4().int % 10_000_000:07d}"
    create = await client.post(
        "/api/v1/public/intake",
        json={"contacts": {"email": email, "phone": phone}, "lead_form_slug": slug, "source": "public-intake-ui"},
    )
    assert create.status_code == 200, create.text
    created = create.json()
    token = created["token"]
    lead_id = created.get("lead_id")
    assert token
    assert lead_id
    assert not created.get("candidate_id")

    get_resp = await client.get(f"/api/v1/public/apply/{token}")
    assert get_resp.status_code == 200, get_resp.text
    served = get_resp.json()
    runtime = served.get("form_runtime")
    assert runtime is not None
    assert runtime.get("contract") == RUNTIME_MODEL_CONTRACT
    assert served.get("form_presentation") is None

    put = await client.put(
        f"/api/v1/public/apply/{token}",
        json={
            "data": {
                "contacts": {"email": email, "phone": phone},
                "personal": {},
                "experience": {},
                "employments": [],
                "agreements": {},
                "presentation_values": {
                    "recruitment.candidate.first_name": "Jan",
                    "recruitment.candidate.last_name": "Kowalski",
                    "recruitment.candidate.contacts.phone": phone,
                },
            }
        },
    )
    assert put.status_code == 200, put.text

    submit = await client.post(
        f"/api/v1/public/apply/{token}/submit",
        json={
            "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
            "documents_version": {
                "privacy": "2025-02-01",
                "terms": "2025-02-01",
                "cookies": "2025-02-01",
            },
            "cookies_accepted": True,
        },
    )
    assert submit.status_code == 200, submit.text
    submitted = submit.json()
    assert submitted["status"] == "submitted"
    submitted_candidate_id = submitted.get("candidate_id")

    listed = await client.get(
        "/api/v1/candidates",
        headers=headers,
        params={"q": email},
    )
    assert listed.status_code == 200, listed.text
    items = listed.json().get("items") or []
    ids = {str(row.get("id") or "") for row in items if isinstance(row, dict)}

    leads = await client.get("/api/v1/leads", headers=headers, params={"q": email})
    assert leads.status_code == 200, leads.text

    from backend.app.entity_profile.public_intake_draft_session import get_public_intake_draft_block

    async with async_session_maker() as session:
        lead = await session.get(Lead, lead_id)
        assert lead is not None
        if not submitted_candidate_id:
            submitted_candidate_id = str(lead.candidate_id or "") or None
        assert submitted_candidate_id
        candidate = await session.get(Candidate, submitted_candidate_id)
        ledger = int(
            await session.scalar(
                select(func.count()).select_from(FormPublicationVersion).where(
                    FormPublicationVersion.form_id == form_id
                )
            )
            or 0
        )
        block = get_public_intake_draft_block(lead)
        state = block.get("intake_state") if isinstance(block.get("intake_state"), dict) else {}
        execution = state.get("forms_execution_v1") if isinstance(state.get("forms_execution_v1"), dict) else {}

    assert execution.get("ok") is True or execution.get("envelope_id")
    assert submitted_candidate_id in ids
    assert ledger == 1
    assert candidate is not None
    assert str(candidate.tenant_id) == str(tenant_id)
    assert str(lead.candidate_id or "") == str(submitted_candidate_id)
