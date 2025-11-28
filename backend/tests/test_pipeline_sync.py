import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stage_sync_smoke(app_with_db, auth_headers):
    """
    Создаём компанию, вакансию, кандидата, линкуем.
    Меняем stage кандидата → колонка пайплайна меняется.
    """
    client: AsyncClient = app_with_db

    # company
    r = await client.post(
        "/api/v1/companies/",
        json={"name": "Acme", "country": "PL"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    comp_id = r.json()["id"]

    # vacancy
    r = await client.post(
        "/api/v1/vacancies/",
        json={"company_id": comp_id, "title": "Frontend"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    vac_id = r.json()["id"]

    # candidate (stage=new)
    r = await client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Anna",
            "last_name": "Kowalska",
            "stage": "Новый",
            "email": "anna@example.com",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    cand_id = r.json()["id"]
    assert r.json()["stage"] == "new"

    # link (new)
    r = await client.post(
        f"/api/v1/vacancies/{vac_id}/candidates",
        json={"candidate_id": cand_id},
        headers=auth_headers,
    )
    assert r.status_code == 200

    # pipeline -> new
    r = await client.get(f"/api/v1/vacancies/{vac_id}/pipeline", headers=auth_headers)
    data = r.json()
    assert any(
        col["status"] == "new"
        for col in [{"status": k} for k in data["columns"].keys()]
    )
    assert len(data["columns"]["new"]) == 1

    # stage -> contacted => column interview
    r = await client.patch(
        f"/api/v1/candidates/{cand_id}",
        json={"stage": "Контакт установлен"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    r = await client.get(f"/api/v1/vacancies/{vac_id}/pipeline", headers=auth_headers)
    data = r.json()
    assert len(data["columns"]["new"]) == 0
    assert len(data["columns"]["interview"]) == 1


@pytest.mark.asyncio
async def test_stage_patch_with_vacancy_payload(app_with_db, auth_headers):
    """
    Переход кандидата с указанием vacancy_id не падает 500 (баг #pipeline-stage).
    """
    client: AsyncClient = app_with_db

    # company
    r = await client.post(
        "/api/v1/companies/",
        json={"name": "PipelineCo", "country": "PL"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    comp_id = r.json()["id"]

    # vacancy
    r = await client.post(
        "/api/v1/vacancies/",
        json={"company_id": comp_id, "title": "Driver"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    vac_id = r.json()["id"]

    # candidate default stage=new
    r = await client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Piotr",
            "last_name": "Nowak",
            "email": "piotr@example.com",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    cand_id = r.json()["id"]

    # patch stage & vacancy simultaneously (regression guard)
    r = await client.patch(
        f"/api/v1/candidates/{cand_id}",
        json={"stage": "contacted", "vacancy_id": vac_id},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "contacted"
    assert body["vacancy_id"] == vac_id


@pytest.mark.asyncio
async def test_stage_patch_from_terminal_allowed(app_with_db, auth_headers):
    """
    Разрешаем менять этап даже из финального статуса — проверяем откат с probation_ok.
    """
    client: AsyncClient = app_with_db

    # create candidate directly in terminal stage
    r = await client.post(
        "/api/v1/candidates",
        json={
            "first_name": "Final",
            "last_name": "Stage",
            "stage": "probation_ok",
            "email": "final@example.com",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    cand_id = r.json()["id"]
    assert r.json()["stage"] == "probation_ok"

    # patch back to an earlier stage
    r = await client.patch(
        f"/api/v1/candidates/{cand_id}",
        json={"stage": "contacted"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["stage"] == "contacted"
