"""HR operational alerts service (v1) — dry-run and throttled dispatch."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.app.db.session import async_session_maker
from backend.app.models.notification import Notification
from backend.app.services.hr_operational_alerts import dispatch_hr_operational_alerts
from backend.tests.api.test_hr_documents_queue import _internal_hr_handoff_accepted
from backend.tests.conftest import _init_data, _set_tenant

_HR_ALERT_EVENTS = (
    "hr_compliance_risk_alert",
    "hr_compliance_risk_reminder",
    "hr_handoff_sla_alert",
    "hr_onboarding_task_reminder",
    "hr_workforce_inactivity_alert",
)


async def _count_hr_operational_alert_notifications_since(
    session, *, tenant_id: str, since: datetime
) -> int:
    return int(
        (
            await session.execute(
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.tenant_id == tenant_id,
                    Notification.type.in_(list(_HR_ALERT_EVENTS)),
                    Notification.related_entity_type == "hr_operational_alert",
                    Notification.created_at >= since,
                )
            )
        ).scalar_one()
        or 0
    )


@pytest.mark.anyio
async def test_hr_operational_alerts_dry_run_counts_slots(
    client: AsyncClient,
    bootstrap: dict[str, str],
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    candidate_id, hid, _ = await _internal_hr_handoff_accepted(
        client,
        manager_headers=manager_headers,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        tenant_id=tenant_id,
        company_id=company_id,
    )
    lst = await client.get(
        "/api/v1/documents/",
        headers=manager_headers,
        params={"candidate_id": candidate_id},
    )
    code95_id = next(x["id"] for x in lst.json() if str(x.get("type") or "") == "code95")
    await client.patch(
        f"/api/v1/documents/{code95_id}",
        headers=manager_headers,
        json={"status": "rejected"},
    )

    async with async_session_maker() as session:
        await _set_tenant(session, tenant_id)
        out = await dispatch_hr_operational_alerts(
            session,
            tenant_id=tenant_id,
            viewer_id=bootstrap["hr_officer_id"],
            viewer_role="employee",
            preset_id="hr",
            dry_run=True,
            actor_id=bootstrap["hr_officer_id"],
        )
        await session.commit()

    assert out["dry_run"] is True
    assert out["risk_items_examined"] >= 1
    assert out["would_notify_slots"] >= 1
    assert out["audit_rows_written"] == 1


@pytest.mark.anyio
async def test_hr_operational_alerts_dispatch_idempotent_window(
    client: AsyncClient,
    bootstrap: dict[str, str],
    manager_headers: dict[str, str],
    recruiter_headers: dict[str, str],
    hr_officer_headers: dict[str, str],
) -> None:
    tenant_id = bootstrap["tenant_id"]
    company_id = bootstrap["company_id"]
    await client.patch(
        "/api/v1/settings/team/modules",
        headers=manager_headers,
        json={"hr": True},
    )
    candidate_id, _, _ = await _internal_hr_handoff_accepted(
        client,
        manager_headers=manager_headers,
        recruiter_headers=recruiter_headers,
        hr_officer_headers=hr_officer_headers,
        tenant_id=tenant_id,
        company_id=company_id,
    )
    lst = await client.get(
        "/api/v1/documents/",
        headers=manager_headers,
        params={"candidate_id": candidate_id},
    )
    code95_id = next(x["id"] for x in lst.json() if str(x.get("type") or "") == "code95")
    await client.patch(
        f"/api/v1/documents/{code95_id}",
        headers=manager_headers,
        json={"status": "rejected"},
    )

    t0 = datetime.now(timezone.utc)

    async with async_session_maker() as s1:
        await _set_tenant(s1, tenant_id)
        r1 = await dispatch_hr_operational_alerts(
            s1,
            tenant_id=tenant_id,
            viewer_id=bootstrap["hr_officer_id"],
            viewer_role="employee",
            preset_id="hr",
            dry_run=False,
            actor_id=bootstrap["hr_officer_id"],
        )
        await s1.commit()

    async with async_session_maker() as s2:
        await _set_tenant(s2, tenant_id)
        n_after_first = await _count_hr_operational_alert_notifications_since(
            s2, tenant_id=tenant_id, since=t0
        )
        r2 = await dispatch_hr_operational_alerts(
            s2,
            tenant_id=tenant_id,
            viewer_id=bootstrap["hr_officer_id"],
            viewer_role="employee",
            preset_id="hr",
            dry_run=False,
            actor_id=bootstrap["hr_officer_id"],
        )
        await s2.commit()

    async with async_session_maker() as s3:
        await _set_tenant(s3, tenant_id)
        n_after_second = await _count_hr_operational_alert_notifications_since(
            s3, tenant_id=tenant_id, since=t0
        )

    assert r1["notifications_returned"] >= 1
    assert n_after_first >= 1
    assert r2.get("suppressed_pre_check", 0) >= 1
    assert n_after_second == n_after_first, "second pass must not insert duplicate HR alert notifications"
