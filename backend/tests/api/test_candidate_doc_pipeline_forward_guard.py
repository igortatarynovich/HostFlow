import pytest


@pytest.fixture(autouse=True)
def _noop_rodo_enforcement_for_doc_pipeline_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """RODO gate is a separate compliance slice; these tests focus on doc/vacancy gates only."""

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "backend.app.api.v1.candidates.service._enforce_rodo_before_contact_stage",
        _noop,
    )


@pytest.mark.anyio
async def test_forward_blocked_docs_wait_to_docs_got_without_documents(client, manager_headers):
    """Mirrors UI: at docs_wait+, missing required docs block forward moves."""
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Doc", "last_name": "PipelineGuard"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    r1 = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "docs_wait"},
    )
    assert r1.status_code == 200, r1.text

    r2 = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "docs_got"},
    )
    assert r2.status_code == 409, r2.text
    detail = r2.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "stage_blocked_by_documents"
    else:
        assert "document" in str(detail).lower()


@pytest.mark.anyio
async def test_backward_allowed_docs_wait_to_contacted_without_documents(client, manager_headers):
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Back", "last_name": "Ok"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "docs_wait"},
    )
    rb = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "contacted"},
    )
    assert rb.status_code == 200, rb.text


@pytest.mark.anyio
async def test_forward_blocked_contacted_without_vacancy(client, manager_headers):
    """Plan §3: contact phase requires vacancy before moving on."""
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Vac", "last_name": "Gate"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    r1 = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "contacted"},
    )
    assert r1.status_code == 200, r1.text

    r2 = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "questionnaire_submitted"},
    )
    assert r2.status_code == 409, r2.text
    detail = r2.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "stage_blocked_by_vacancy"
    else:
        assert "vacancy" in str(detail).lower()


@pytest.mark.anyio
async def test_forward_allowed_contacted_when_vacancy_set(client, manager_headers):
    comp = await client.post(
        "/api/v1/companies",
        headers=manager_headers,
        json={
            "name": "Vac Co",
            "legal_name": "Vac Co Sp. z o.o.",
            "tax_id": "PL9988877766",
            "email": "vac@test.example",
        },
    )
    assert comp.status_code == 200, comp.text
    company_id = comp.json()["id"]

    vac = await client.post(
        "/api/v1/vacancies",
        headers=manager_headers,
        json={
            "company_id": company_id,
            "title": "Test gate vacancy",
            "target": 1,
            "status": "open",
        },
    )
    assert vac.status_code == 200, vac.text
    vacancy_id = vac.json()["id"]

    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Vac", "last_name": "Ok"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "contacted"},
    )

    r = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "questionnaire_submitted", "vacancy_id": vacancy_id},
    )
    assert r.status_code == 200, r.text


@pytest.mark.anyio
async def test_forward_allowed_new_to_contacted_without_documents(client, manager_headers):
    create = await client.post(
        "/api/v1/candidates",
        headers=manager_headers,
        json={"first_name": "Early", "last_name": "Stage"},
    )
    assert create.status_code == 200, create.text
    cid = create.json()["id"]

    r = await client.patch(
        f"/api/v1/candidates/{cid}",
        headers=manager_headers,
        json={"stage": "contacted"},
    )
    assert r.status_code == 200, r.text
