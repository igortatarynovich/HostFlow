#!/usr/bin/env python3
"""Execute questionnaire staging runbook via API and print evidence lines."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

sys.path.insert(0, "/app")

from backend.app.entity_profile.seed import ensure_tenant_entity_profile_defaults
from backend.app.entity_profile.seed_targeted_advertising_form import ensure_tenant_targeted_advertising_intake_form
from backend.app.main import app
from backend.app.modules.leads import crud as leads_crud
from backend.app.db.session import async_session_maker
from backend.app.models.lead_questionnaire_invite import LeadQuestionnaireInvite
from backend.app.models.own_company import OwnCompany
from sqlalchemy import func, select

TENANT = "11111111-1111-1111-1111-111111111111"
PREFIX = "service_sales.targeted_advertising."


async def manager_headers() -> dict[str, str]:
    from backend.tests.conftest import DEFAULT_TENANT_ID, _build_token, _init_data

    data = await _init_data()
    token = _build_token(data["manager_id"], data["manager_email"], "manager", DEFAULT_TENANT_ID)
    return {"Authorization": f"Bearer {token}", "X-Tenant-Id": DEFAULT_TENANT_ID}


def log(key: str, value: object) -> None:
    print(f"EVIDENCE|{key}|{json.dumps(value, ensure_ascii=False, default=str)}")


def _mask_token(token: str) -> str:
    token = str(token or "")
    if len(token) <= 10:
        return "***"
    return f"{token[:6]}…{token[-4:]}"


async def main() -> None:
    headers = await manager_headers()
    run_at = datetime.now(timezone.utc).isoformat()
    log("run_at_utc", run_at)
    log("tenant_id", TENANT)

    async with async_session_maker() as db:
        await ensure_tenant_entity_profile_defaults(db, TENANT)
        await ensure_tenant_targeted_advertising_intake_form(db, TENANT)
        own_company_id = await db.scalar(
            select(OwnCompany.id).where(OwnCompany.tenant_id == TENANT, OwnCompany.is_archived.is_(False)).limit(1)
        )
        lead = await leads_crud.create_lead(
            db,
            tenant_id=TENANT,
            own_company_id=str(own_company_id),
            company_id=None,
            vacancy_id=None,
            source="meta_ads",
            external_id=f"staging-runbook-{uuid4().hex[:10]}",
            payload={"phone": "+48***", "full_name": "Staging Runbook"},
            normalized={
                "full_name": "Staging Runbook",
                "phone": "+48***",
                "company_name": "Staging Runbook Sp. z o.o.",
                "email": "staging-***@example.com",
            },
            lead_type="client",
            lead_target_type="client_lead",
        )
        await db.commit()
        lead_id = str(lead.id)

    log("lead_id", lead_id)
    log("sales_inquiry_path", f"/app/sales/inquiries/{lead_id}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        lead_before = await client.get(f"/api/v1/leads/{lead_id}", headers=headers)
        log("step3_lead_status_before_send", (lead_before.json().get("normalized") or {}).get("sales_questionnaire_status"))

        pre_invite = await client.post(
            f"/api/v1/leads/{lead_id}/questionnaire-invite",
            headers=headers,
            json={"mark_sent": False},
        )
        log("step3_pre_send_post_status", pre_invite.status_code)
        log("step3_pre_send_post_detail", pre_invite.json().get("detail") if pre_invite.status_code != 200 else None)

        send = await client.post(
            f"/api/v1/leads/{lead_id}/questionnaire-invite",
            headers=headers,
            json={"mark_sent": True},
        )
        send_body = send.json()
        token = send_body["token"]
        apply_url = send_body.get("apply_url") or f"/public/apply/{token}"
        log("step4_send_status", send.status_code)
        log("step4_invite_token", _mask_token(token))
        log("step4_apply_url", "/public/apply/{token}")
        log("step4_invite_status", send_body.get("status"))
        log("step4_sent_at", send_body.get("sent_at"))

        refresh = await client.post(
            f"/api/v1/leads/{lead_id}/questionnaire-invite",
            headers=headers,
            json={"mark_sent": False},
        )
        refresh_body = refresh.json()
        log("step5_refresh_post_status", refresh.status_code)
        log("step5_token_stable", refresh_body.get("token") == token)
        log("step5_refresh_token", _mask_token(refresh_body.get("token", "")))

        public_get = await client.get(f"/api/v1/public/apply/{token}")
        fp = public_get.json().get("form_presentation") or {}
        field_count = len(fp.get("fields") or [])
        select_fields = [f for f in fp.get("fields", []) if f.get("field_type") in ("single_select", "multi_select")]
        log("step6_public_field_count", field_count)
        log("step6_select_field_count", len(select_fields))
        log("step6_api_options_null", all(f.get("options") is None for f in select_fields))

        ca_eval = await client.post(
            f"/api/v1/public/apply/{token}/evaluate-presentation",
            json={"presentation_values": {f"{PREFIX}need_type": "client_acquisition"}},
        )
        er_eval = await client.post(
            f"/api/v1/public/apply/{token}/evaluate-presentation",
            json={"presentation_values": {f"{PREFIX}need_type": "employee_recruitment"}},
        )
        ca_vis = [
            f["qualified_code"].split(".")[-1]
            for f in (ca_eval.json().get("fields") or [])
            if (f.get("evaluated") or {}).get("visible")
        ]
        er_vis = [
            f["qualified_code"].split(".")[-1]
            for f in (er_eval.json().get("fields") or [])
            if (f.get("evaluated") or {}).get("visible")
        ]
        log("step8_branch_client_acquisition_visible", ca_vis)
        log("step8_branch_employee_recruitment_visible", er_vis)

        presentation_values = {
            f"{PREFIX}need_type": "client_acquisition",
            f"{PREFIX}primary_outcome": "more_inquiries",
            f"{PREFIX}promotion_subject": "service",
            f"{PREFIX}industry": "transport",
            f"{PREFIX}client_geo_scope": "poland",
            f"{PREFIX}conversion_destination": "whatsapp",
            f"{PREFIX}offer_ready": "ready",
            f"{PREFIX}marketing_materials": ["photos", "logo"],
            f"{PREFIX}prior_ads_experience": "no",
            f"{PREFIX}monthly_ad_budget": "2000_5000",
            f"{PREFIX}start_timeline": "two_weeks",
            f"{PREFIX}decision_maker": "owner",
            f"{PREFIX}contact_full_name": "Staging Runbook",
            f"{PREFIX}contact_company_name": "Staging Runbook Sp. z o.o.",
            f"{PREFIX}contact_phone": "+48***",
            f"{PREFIX}contact_email": "staging-***@example.com",
            f"{PREFIX}recruitment_roles": ["driver_ce"],
        }
        log("step9_submit_payload_presentation_values", presentation_values)

        await client.put(
            f"/api/v1/public/apply/{token}",
            json={"data": {"presentation_values": presentation_values, "application_kind": "client"}},
        )
        submit = await client.post(
            f"/api/v1/public/apply/{token}/submit",
            json={
                "consents": {"general": True, "employer_share": True, "terms_acceptance": True},
                "cookies_accepted": True,
            },
        )
        log("step9_submit_status", submit.status_code)

        lead_after = await client.get(f"/api/v1/leads/{lead_id}", headers=headers)
        normalized_after = lead_after.json().get("normalized") or {}
        sq = normalized_after.get("sales_questionnaire") or {}
        log("step10_lead_questionnaire_status", normalized_after.get("sales_questionnaire_status"))
        log("step10_sales_questionnaire_summary", sq)
        log("step10_hidden_recruitment_roles_absent", "recruitment_roles" not in sq)

        async with async_session_maker() as db:
            invite_count_before = await db.scalar(
                select(func.count()).select_from(LeadQuestionnaireInvite).where(LeadQuestionnaireInvite.lead_id == lead_id)
            )

        post_submit_hydrate = await client.post(
            f"/api/v1/leads/{lead_id}/questionnaire-invite",
            headers=headers,
            json={"mark_sent": False},
        )
        log("step10_post_submit_hydrate_status", post_submit_hydrate.status_code)

        async with async_session_maker() as db:
            invite_count_after = await db.scalar(
                select(func.count()).select_from(LeadQuestionnaireInvite).where(LeadQuestionnaireInvite.lead_id == lead_id)
            )
        log("step10_invite_row_count_unchanged", invite_count_before == invite_count_after)
        log("step10_invite_row_count", invite_count_after)

        # Product convert requires SalesInquiry + confirmed Flights ledger + Review stamp.
        # Lead convert-client is a compatibility facade over convert_sales_inquiry_mapping.
        from backend.tests.api._sales_convert_readiness import ensure_product_convert_readiness

        async with async_session_maker() as db:
            si_id = await ensure_product_convert_readiness(db, tenant_id=TENANT, lead_id=lead_id)
        log("step10b_convert_readiness_sales_inquiry_id", si_id)

        conv1 = await client.post(f"/api/v1/leads/{lead_id}/convert-client", headers=headers)
        conv1_body = conv1.json()
        client_id_1 = conv1_body.get("converted_client_id")
        log("step11_convert1_status", conv1.status_code)
        log("step11_convert1_client_id", client_id_1)

        # Replay via canonical Sales entrypoint must yield the same ClientAccount.
        sales_replay = await client.post(
            f"/api/v1/sales/inquiries/{lead_id}/convert-client",
            headers=headers,
        )
        sales_body = sales_replay.json()
        sales_client_id = sales_body.get("outcome_entity_id") or (sales_body.get("client_account_id"))
        log("step11b_sales_replay_status", sales_replay.status_code)
        log("step11b_sales_replay_client_id", sales_client_id)

        conv2 = await client.post(f"/api/v1/leads/{lead_id}/convert-client", headers=headers)
        conv2_body = conv2.json()
        client_id_2 = conv2_body.get("converted_client_id")
        log("step12_convert2_status", conv2.status_code)
        log("step12_convert2_client_id", client_id_2)
        log("step12_convert_idempotent", client_id_1 == client_id_2 and client_id_1 is not None)
        log(
            "step12_sales_lead_same_client",
            client_id_1 == sales_client_id and client_id_1 is not None,
        )

        defects: list[str] = []
        if pre_invite.status_code != 404:
            defects.append(f"step3: expected 404 pre-send POST, got {pre_invite.status_code}")
        if send.status_code != 200:
            defects.append(f"step4: send failed {send.status_code}")
        if refresh_body.get("token") != token:
            defects.append("step5: token changed after refresh")
        if submit.status_code != 200:
            defects.append(f"step9: submit failed {submit.status_code}")
        if normalized_after.get("sales_questionnaire_status") != "submitted":
            defects.append(f"step10: expected submitted, got {normalized_after.get('sales_questionnaire_status')}")
        if "recruitment_roles" in sq:
            defects.append("step10: hidden recruitment_roles leaked into summary")
        if invite_count_before != invite_count_after:
            defects.append("step10: new invite row created after submit")
        if post_submit_hydrate.status_code == 200:
            defects.append("step10: POST hydrate succeeded after submitted (should be skipped in UI; API may 404)")
        if conv1.status_code != 200 or not client_id_1:
            defects.append(f"step11: convert failed {conv1.status_code}")
        if sales_replay.status_code != 200 or sales_client_id != client_id_1:
            defects.append(
                f"step11b: sales replay mismatch status={sales_replay.status_code} "
                f"sales={sales_client_id} lead={client_id_1}"
            )
        if client_id_1 != client_id_2:
            defects.append("step12: convert not idempotent")

        log("defects", defects)
        log("staging_pass", len(defects) == 0)


if __name__ == "__main__":
    asyncio.run(main())
