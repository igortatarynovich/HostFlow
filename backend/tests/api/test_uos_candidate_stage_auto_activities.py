from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict

import pytest
from httpx import AsyncClient

CANDIDATES_BASE = "/api/v1/candidates"
REMINDERS_BASE = "/api/v1/reminders"


@pytest.mark.anyio
async def test_uos_candidate_stage_follow_up_on_patch(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    # The two PATCHes below move the candidate forward through the
    # hiring pipeline, which trips three independent stage gates that
    # this test must satisfy up-front:
    #
    #  (a) ``_enforce_rodo_before_contact_stage`` (RODO art.14) fires
    #      on the move to ``contacted`` / ``no_answer`` and rejects
    #      with HTTP 409 ``{"detail":"RODO must be sent to candidate
    #      before moving to contact/screening stage"}`` unless either
    #      ``rodo_consent_log`` already has a sent row for the
    #      candidate, or the candidate has an ``email`` and the
    #      auto-send path in ``app/api/v1/candidates/service.py``
    #      (the ``if (c.email or "").strip(): await _send_rodo_email``
    #      branch) ran during create. We pick option two by passing
    #      ``email`` on create.
    #
    #  (b) ``enforce_pipeline_vacancy_forward_block`` fires when
    #      moving FORWARD FROM ``contacted`` /
    #      ``questionnaire_submitted`` (see
    #      ``hiring_pipeline_gates._DEFAULT_VACANCY_STAGES``) without
    #      a ``vacancy_id``, and rejects with HTTP 409 ``{"code":
    #      "stage_blocked_by_vacancy"}``. We bind the candidate to a
    #      vacancy at create time so both PATCH A (default ->
    #      contacted) and PATCH B (contacted -> docs_wait) clear the
    #      gate.
    #
    #  (c) The doc-pipeline forward block is suppressed by default
    #      for these stages on a fresh candidate (no required-doc
    #      summary yet), so we don't need to seed documents here.
    #
    # Sibling tests follow the same prelude pattern — see
    # ``test_pipeline_sync.test_stage_patch_with_vacancy_payload`` and
    # ``test_candidate_doc_pipeline_forward_guard``.

    company_resp = await client.post(
        "/api/v1/companies/",
        headers=manager_headers,
        json={"name": "UosPipelineCo", "country": "PL"},
    )
    assert company_resp.status_code == 200, company_resp.text
    company_id = str(company_resp.json()["id"])

    vacancy_resp = await client.post(
        "/api/v1/vacancies/",
        headers=manager_headers,
        json={"company_id": company_id, "title": "UOS Driver"},
    )
    assert vacancy_resp.status_code == 200, vacancy_resp.text
    vacancy_id = str(vacancy_resp.json()["id"])

    create_resp = await client.post(
        CANDIDATES_BASE,
        headers=manager_headers,
        json={
            "first_name": "UOS",
            "last_name": "StageAuto",
            "email": "uos.stageauto@example.com",
            "vacancy_id": vacancy_id,
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    cand = create_resp.json()
    cid = str(cand["id"])

    # All reminder list queries below use ``assignee_scope=team`` because
    # ``ensure_candidate_stage_follow_up_task`` resolves the auto-reminder
    # assignee from ``candidate.recruiter_id`` first (only falling back to
    # ``actor_id`` when the candidate has no recruiter). Binding a vacancy
    # at create-time auto-resolves a recruiter via the vacancy's recruiter
    # assignment, so the auto-reminder lands on the recruiter, not the
    # admin who fired the PATCH. Default ``assignee_scope=mine`` would
    # therefore show 0 items even though the row is in ``activities``.
    # ``team`` scope is the right lens for "show me what was created on
    # this candidate" regardless of which assignee got it.
    r0 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={
            "entity_type": "candidate",
            "entity_id": cid,
            "type_filter": "uos_candidate_stage_follow_up",
            "assignee_scope": "team",
        },
    )
    assert r0.status_code == 200, r0.text
    assert len(r0.json().get("items") or []) == 0

    patch_a = await client.patch(
        f"{CANDIDATES_BASE}/{cid}",
        headers=manager_headers,
        json={"stage": "contacted"},
    )
    assert patch_a.status_code == 200, patch_a.text

    r_stage = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={
            "entity_type": "candidate",
            "entity_id": cid,
            "type_filter": "uos_candidate_stage_follow_up",
            "assignee_scope": "team",
        },
    )
    assert r_stage.status_code == 200, r_stage.text
    stage_items = r_stage.json().get("items") or []
    assert len(stage_items) == 1
    assert stage_items[0]["type"] == "uos_candidate_stage_follow_up"
    assert stage_items[0]["entity_type"] == "candidate"
    assert stage_items[0]["entity_id"] == cid
    assert "contacted" in (stage_items[0].get("title") or "")
    first_id = stage_items[0]["id"]

    patch_b = await client.patch(
        f"{CANDIDATES_BASE}/{cid}",
        headers=manager_headers,
        json={"stage": "docs_wait"},
    )
    assert patch_b.status_code == 200, patch_b.text

    r_stage2 = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={
            "entity_type": "candidate",
            "entity_id": cid,
            "type_filter": "uos_candidate_stage_follow_up",
            "assignee_scope": "team",
        },
    )
    stage_items2 = r_stage2.json().get("items") or []
    assert len(stage_items2) == 1
    assert stage_items2[0]["id"] == first_id
    assert "docs_wait" in (stage_items2[0].get("title") or "")


@pytest.mark.anyio
async def test_reminders_list_enriches_candidate_name_from_linked_candidate(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    create_resp = await client.post(
        CANDIDATES_BASE,
        headers=manager_headers,
        json={"first_name": "Payload", "last_name": "Enriched"},
    )
    assert create_resp.status_code == 200, create_resp.text
    cid = str(create_resp.json()["id"])

    due = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    mk_resp = await client.post(
        REMINDERS_BASE,
        headers=manager_headers,
        json={
            "title": "Call candidate",
            "entity_type": "candidate",
            "entity_id": cid,
            "type": "custom",
            "due_at": due,
            "remind_at": due,
            "payload": {},
        },
    )
    assert mk_resp.status_code == 201, mk_resp.text
    rid = str(mk_resp.json()["id"])

    list_resp = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "candidate", "entity_id": cid},
    )
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json().get("items") or []
    row = next((it for it in items if str(it.get("id")) == rid), None)
    assert row is not None, "created reminder must appear in list"
    payload = row.get("payload") or {}
    assert payload.get("candidate_name") == "Payload Enriched"


@pytest.mark.anyio
async def test_reminders_list_keeps_existing_candidate_name_payload(
    client: AsyncClient,
    manager_headers: Dict[str, str],
) -> None:
    create_resp = await client.post(
        CANDIDATES_BASE,
        headers=manager_headers,
        json={"first_name": "Original", "last_name": "Name"},
    )
    assert create_resp.status_code == 200, create_resp.text
    cid = str(create_resp.json()["id"])

    due = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
    mk_resp = await client.post(
        REMINDERS_BASE,
        headers=manager_headers,
        json={
            "title": "Do not overwrite payload name",
            "entity_type": "candidate",
            "entity_id": cid,
            "type": "custom",
            "due_at": due,
            "remind_at": due,
            "payload": {"candidate_name": "Manual Alias"},
        },
    )
    assert mk_resp.status_code == 201, mk_resp.text
    rid = str(mk_resp.json()["id"])

    list_resp = await client.get(
        REMINDERS_BASE,
        headers=manager_headers,
        params={"entity_type": "candidate", "entity_id": cid},
    )
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json().get("items") or []
    row = next((it for it in items if str(it.get("id")) == rid), None)
    assert row is not None, "created reminder must appear in list"
    payload = row.get("payload") or {}
    assert payload.get("candidate_name") == "Manual Alias"
