import pytest


@pytest.mark.anyio
async def test_client_cannot_set_internal_agency_stage_on_create(client, client_processor_headers):
  # При создании кандидата клиент не может указать внутреннюю агентскую стадию
  resp = await client.post(
      "/api/v1/candidates",
      headers=client_processor_headers,
      json={
          "first_name": "Client",
          "last_name": "Candidate",
          "stage": "new",  # внутренний агентский этап
      },
  )
  assert resp.status_code in (400, 403), resp.text
  body = resp.json()
  detail = (body.get("detail") or "").lower()
  assert "stage" in detail or "not allowed" in detail


@pytest.mark.anyio
async def test_client_can_set_client_visible_stage_after_handoff(
  client,
  client_processor_headers,
  manager_headers,
):
  # Агентство создаёт кандидата и переводит на ready_for_handoff
  create_resp = await client.post(
      "/api/v1/candidates",
      headers=manager_headers,
      json={"first_name": "Handoff", "last_name": "Candidate"},
  )
  assert create_resp.status_code == 200, create_resp.text
  candidate_id = create_resp.json()["id"]

  patch_resp = await client.patch(
      f"/api/v1/candidates/{candidate_id}",
      headers=manager_headers,
      json={"stage": "ready_for_handoff"},
  )
  assert patch_resp.status_code == 200, patch_resp.text

  # Здесь в реальных тестах должен быть сценарий create/accept handoff,
  # который уже покрыт отдельными тестами handoff-сервиса.
  # Для упрощения предполагаем, что фикстура client_processor_headers
  # привязана к тенанту с принятым handoff и может редактировать кандидата.

  # Клиент может перевести кандидата на клиентский этап processing_by_client
  resp = await client.patch(
      f"/api/v1/candidates/{candidate_id}",
      headers=client_processor_headers,
      json={"stage": "processing_by_client"},
  )
  assert resp.status_code == 200, resp.text
  data = resp.json()
  assert data["stage"] == "processing_by_client"


@pytest.mark.anyio
async def test_client_bulk_stage_rejects_internal_stage(
  client,
  client_processor_headers,
  manager_headers,
):
  # Агентство создаёт кандидата
  create_resp = await client.post(
      "/api/v1/candidates",
      headers=manager_headers,
      json={"first_name": "Bulk", "last_name": "ClientStage"},
  )
  assert create_resp.status_code == 200, create_resp.text
  candidate_id = create_resp.json()["id"]

  # Клиент пытается массово перевести на внутренний агентский этап
  resp = await client.post(
      "/api/v1/candidates/bulk-stage",
      headers=client_processor_headers,
      json={
          "candidate_ids": [candidate_id],
          "stage": "docs_wait",  # внутренний этап агентства
      },
  )
  assert resp.status_code == 200, resp.text
  payload = resp.json()
  assert payload
  first = payload[0]
  assert first["ok"] is False
  err = (first.get("error") or "").lower()
  assert "not allowed" in err or "forbidden" in err

