"""ADR-024 Stage 3E PR-1 — Acquisition Activity Timeline foundation contracts."""

from __future__ import annotations

import ast
import inspect as py_inspect
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import inspect, select, text

from backend.app.acquisition import append_activity_event, list_activity_events
from backend.app.acquisition.activity import ACTIVITY_EVENT_TYPES, ACTIVITY_LIST_ORDER
from backend.app.acquisition.activity import repository as activity_repository
from backend.app.acquisition.activity.catalog import (
    ACTIVITY_EVENT_CATALOG,
    get_activity_event_contract,
)
from backend.app.acquisition.activity.errors import (
    InvalidActivityPayload,
    UnknownActivityEventType,
    UnsupportedActivityEventVersion,
)
from backend.app.acquisition.activity.repository import get_activity_event
from backend.app.db.session import async_session_maker
from backend.app.models.acquisition_activity_event import (
    ACTOR_TYPE_SYSTEM,
    AcquisitionActivityEvent,
)
from backend.app.models.campaign import Campaign, CampaignRun
from backend.app.models.own_company import OwnCompany
from backend.tests.conftest import _init_data

_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = _REPO_ROOT / "backend"
_VERSIONS = _BACKEND_ROOT / "alembic" / "versions"
_REV = "202607220002_acq_3e_imm"
_PREV_REV = "202607220001_acq_3e_act"
_BEFORE_ACTIVITY = "202607210002_comm_automation_domain_c2_2"


def _alembic_bin() -> str:
    for rel in (".venv312/bin/alembic", ".venv/bin/alembic"):
        candidate = _REPO_ROOT / rel
        if candidate.is_file():
            return str(candidate)
    return "alembic"


def _run_alembic(*args: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    for key in ("ALEMBIC_DATABASE_URL", "SYNC_DATABASE_URL", "DATABASE_URL"):
        val = env.get(key)
        if val and "@db:" in val:
            env[key] = val.replace("@db:", "@127.0.0.1:")
    return subprocess.run(
        [_alembic_bin(), "-c", str(_BACKEND_ROOT / "alembic.ini"), *args],
        cwd=str(_BACKEND_ROOT),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


async def _own_company_id(db, tenant_id: str) -> str:
    row = await db.execute(
        select(OwnCompany.id)
        .where(OwnCompany.tenant_id == tenant_id, OwnCompany.is_archived.is_(False))
        .order_by(OwnCompany.created_at.asc())
        .limit(1)
    )
    oc = row.scalar_one_or_none()
    if oc is None:
        oc = str(uuid4())
        db.add(OwnCompany(id=oc, tenant_id=tenant_id, name=f"OC {uuid4().hex[:6]}"))
        await db.flush()
    return str(oc)


async def _ensure_tenant(db, tenant_id: str) -> None:
    from backend.app.models.tenant import Tenant

    exists = (
        await db.execute(select(Tenant.id).where(Tenant.id == tenant_id))
    ).scalar_one_or_none()
    if exists is not None:
        return
    suffix = tenant_id.replace("-", "")[:8]
    db.add(
        Tenant(
            id=tenant_id,
            name=f"Tenant {suffix}",
            slug=f"t-{suffix}",
            api_key=f"api-{suffix}-{uuid4().hex[:8]}",
            is_active=True,
        )
    )
    await db.flush()


async def _seed_campaign(db, *, tenant_id: str) -> tuple[Campaign, CampaignRun]:
    await _ensure_tenant(db, tenant_id)
    oc = await _own_company_id(db, tenant_id)
    campaign_id = str(uuid4())
    flight_id = str(uuid4())
    campaign = Campaign(
        id=campaign_id,
        tenant_id=tenant_id,
        own_company_id=oc,
        name=f"Campaign {uuid4().hex[:6]}",
        status="active",
        goal_type="hiring",
        primary_kpi="hires",
        current_flight_id=flight_id,
    )
    flight = CampaignRun(
        id=flight_id,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        code="flight_1",
        name="Flight 1",
        status="active",
    )
    db.add(campaign)
    db.add(flight)
    await db.flush()
    return campaign, flight


def _flight_started_payload(
    *, previous_status: str = "planned", new_status: str = "active"
) -> dict:
    return {"previous_status": previous_status, "new_status": new_status}


def _flight_paused_payload(
    *, previous_status: str = "active", new_status: str = "paused"
) -> dict:
    return {"previous_status": previous_status, "new_status": new_status}


def _flight_resumed_payload(
    *, previous_status: str = "paused", new_status: str = "active"
) -> dict:
    return {"previous_status": previous_status, "new_status": new_status}


def _flight_completed_payload(
    *, previous_status: str = "active", new_status: str = "completed"
) -> dict:
    return {"previous_status": previous_status, "new_status": new_status}


# --- Catalog / versioning -----------------------------------------------------


def test_event_versions_are_per_type_not_catalog_wide() -> None:
    assert not hasattr(ACTIVITY_EVENT_CATALOG, "catalog_version")
    started = get_activity_event_contract("FlightStarted")
    budget = get_activity_event_contract("BudgetChanged")
    assert started is not None and budget is not None
    assert started.event_version == "1"
    assert budget.event_version == "1"
    # Contracts are independent objects — bumping one type does not require shared version.
    assert started.event_type != budget.event_type
    assert "Completed" not in ACTIVITY_EVENT_TYPES
    assert len(ACTIVITY_EVENT_TYPES) == len(ACTIVITY_EVENT_CATALOG) >= 30


def test_activity_model_fk_boundary_and_no_ops_ownership() -> None:
    forbidden_tables = {
        "candidates",
        "recruitment_applications",
        "sales_inquiries",
        "inquiries",
        "client_accounts",
        "companies",
        "leads",
    }
    mapper = inspect(AcquisitionActivityEvent)
    fk_tables = {
        fk.column.table.name for col in mapper.columns for fk in col.foreign_keys
    }
    assert not (fk_tables & forbidden_tables)
    assert fk_tables <= {"acq_campaigns", "acq_campaign_runs"}
    cols = {c.key for c in mapper.columns}
    assert "occurred_at" in cols and "recorded_at" in cols
    assert "updated_at" not in cols
    assert "lead_id" not in cols and "candidate_id" not in cols


def test_public_surface_is_append_and_list_only() -> None:
    import backend.app.acquisition as acq
    import backend.app.acquisition.activity as activity

    assert "append_activity_event" in acq.__all__
    assert "list_activity_events" in acq.__all__
    assert "get_activity_event" not in acq.__all__
    assert "get_by_source_event_id" not in acq.__all__
    assert activity.__all__.count("append_activity_event") == 1
    assert "list_activity_events" in activity.__all__
    # No specialized append_* helpers for PR-2 to multiply.
    append_fns = [
        name
        for name, obj in py_inspect.getmembers(activity, py_inspect.isfunction)
        if name.startswith("append_")
    ]
    assert append_fns == ["append_activity_event"]


def test_repository_has_no_update_or_delete_methods() -> None:
    names = {
        name for name, _ in py_inspect.getmembers(activity_repository, py_inspect.isfunction)
    }
    banned = {
        n
        for n in names
        if n.startswith("update")
        or n.startswith("delete")
        or n.startswith("remove")
        or n.startswith("patch")
    }
    assert not banned
    src = Path(activity_repository.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    order_attrs: list[str] = []
    for node in ast.walk(tree):
        # Match AcquisitionActivityEvent.<col>.asc()/desc()
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"asc", "desc"}
            and isinstance(node.func.value, ast.Attribute)
        ):
            order_attrs.append(node.func.value.attr)
    assert order_attrs == ["occurred_at", "id"]
    assert ACTIVITY_LIST_ORDER == ("occurred_at", "id")
    assert "recorded_at" not in order_attrs
    assert "Never order by" in src


def test_alembic_revision_is_linear_no_merge() -> None:
    path = _VERSIONS / "202607220002_acq_3e_imm_cascade.py"
    text_src = path.read_text(encoding="utf-8")
    assert f'revision: str = "{_REV}"' in text_src
    assert f'down_revision: Union[str, None] = "{_PREV_REV}"' in text_src
    assert "merge" not in path.name.lower()
    assert "no UPDATE of any column" in text_src

    heads = _run_alembic("heads")
    assert heads.returncode == 0, heads.stderr + heads.stdout
    head_lines = [
        line.strip()
        for line in heads.stdout.splitlines()
        if line.strip() and not line.startswith("INFO")
    ]
    assert len(head_lines) == 1
    assert _REV in head_lines[0]


# --- Runtime contracts --------------------------------------------------------


@pytest.mark.asyncio
async def test_append_success_materialises_occurred_at() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    t0 = datetime(2026, 7, 21, 9, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign(db, tenant_id=tenant_id)
        row = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="FlightStarted",
            event_version="1",
            payload=_flight_started_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0,
            correlation_id="corr-ok",
            causation_id="cause-ok",
        )
        assert row.id
        assert row.flight_id == flight.id
        assert row.occurred_at == t0
        assert row.recorded_at is not None
        assert row.occurred_at < row.recorded_at
        assert row.correlation_id == "corr-ok"
        assert row.causation_id == "cause-ok"
        await db.commit()


@pytest.mark.asyncio
async def test_duplicate_append_returns_existing_row() -> None:
    data = await _init_data()
    tenant_a = data["tenant_id"]
    tenant_b = str(uuid4())

    async with async_session_maker() as db:
        camp_a, flight_a = await _seed_campaign(db, tenant_id=tenant_a)
        camp_b, _flight_b = await _seed_campaign(db, tenant_id=tenant_b)

        first = await append_activity_event(
            db,
            tenant_id=tenant_a,
            campaign_id=camp_a.id,
            flight_id=flight_a.id,
            event_type="FlightStarted",
            event_version="1",
            payload=_flight_started_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id="src-flight-start-1",
        )
        second = await append_activity_event(
            db,
            tenant_id=tenant_a,
            campaign_id=camp_a.id,
            flight_id=flight_a.id,
            event_type="FlightStarted",
            event_version="1",
            payload={**_flight_started_payload(), "reason": "retry-must-not-overwrite"},
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id="src-flight-start-1",
        )
        assert isinstance(second, AcquisitionActivityEvent)
        assert second.id == first.id
        assert second.payload == _flight_started_payload()
        assert second.event_type == first.event_type
        assert second.source_event_id == "src-flight-start-1"

        other_tenant = await append_activity_event(
            db,
            tenant_id=tenant_b,
            campaign_id=camp_b.id,
            event_type="CampaignActivated",
            event_version="1",
            payload={},
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id="src-flight-start-1",
        )
        assert other_tenant.id != first.id
        await db.commit()


@pytest.mark.asyncio
async def test_source_event_id_unique_per_tenant() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign(db, tenant_id=tenant_id)
        a = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="FlightPaused",
            event_version="1",
            payload=_flight_paused_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id="uniq-key-1",
        )
        b = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="FlightPaused",
            event_version="1",
            payload=_flight_paused_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id="uniq-key-1",
        )
        assert a.id == b.id
        count = await db.execute(
            text(
                "SELECT count(*) FROM acquisition_activity_events "
                "WHERE tenant_id = :t AND source_event_id = :s"
            ),
            {"t": tenant_id, "s": "uniq-key-1"},
        )
        assert count.scalar() == 1
        await db.commit()


@pytest.mark.asyncio
async def test_immutable_update_any_column_rejected() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        dialect = db.bind.dialect.name if db.bind is not None else ""
        if dialect != "postgresql":
            pytest.skip("immutability trigger is PostgreSQL-only")
        camp, flight = await _seed_campaign(db, tenant_id=tenant_id)
        row = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="FlightPaused",
            event_version="1",
            payload=_flight_paused_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id=f"imm-{uuid4().hex}",
        )
        await db.commit()
        event_id = row.id

    forbidden_updates = (
        "UPDATE acquisition_activity_events SET payload = '{}'::jsonb WHERE id = :id",
        "UPDATE acquisition_activity_events SET occurred_at = NOW() WHERE id = :id",
        "UPDATE acquisition_activity_events SET source_event_id = 'x' WHERE id = :id",
        "UPDATE acquisition_activity_events SET tenant_id = :id WHERE id = :id",
        "UPDATE acquisition_activity_events SET event_type = 'FlightStarted' WHERE id = :id",
    )
    for sql in forbidden_updates:
        async with async_session_maker() as db:
            with pytest.raises(Exception):
                await db.execute(text(sql), {"id": event_id})
                await db.commit()
            await db.rollback()

    async with async_session_maker() as db:
        still = await get_activity_event(db, tenant_id=tenant_id, event_id=event_id)
        assert still is not None
        assert still.event_type == "FlightPaused"


@pytest.mark.asyncio
async def test_immutable_delete_rejected() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        dialect = db.bind.dialect.name if db.bind is not None else ""
        if dialect != "postgresql":
            pytest.skip("immutability trigger is PostgreSQL-only")
        camp, flight = await _seed_campaign(db, tenant_id=tenant_id)
        row = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="FlightResumed",
            event_version="1",
            payload=_flight_resumed_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        await db.commit()
        event_id = row.id

    async with async_session_maker() as db:
        with pytest.raises(Exception):
            await db.execute(
                text("DELETE FROM acquisition_activity_events WHERE id = :id"),
                {"id": event_id},
            )
            await db.commit()
        await db.rollback()

    async with async_session_maker() as db:
        still = await get_activity_event(db, tenant_id=tenant_id, event_id=event_id)
        assert still is not None


@pytest.mark.asyncio
async def test_tenant_isolation_on_query() -> None:
    data = await _init_data()
    tenant_a = data["tenant_id"]
    tenant_b = str(uuid4())

    async with async_session_maker() as db:
        camp_a, flight_a = await _seed_campaign(db, tenant_id=tenant_a)
        camp_b, flight_b = await _seed_campaign(db, tenant_id=tenant_b)
        await append_activity_event(
            db,
            tenant_id=tenant_a,
            campaign_id=camp_a.id,
            flight_id=flight_a.id,
            event_type="FlightStarted",
            event_version="1",
            payload=_flight_started_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id=f"iso-a-{uuid4().hex}",
        )
        await append_activity_event(
            db,
            tenant_id=tenant_b,
            campaign_id=camp_b.id,
            flight_id=flight_b.id,
            event_type="FlightStarted",
            event_version="1",
            payload=_flight_started_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            source_event_id=f"iso-b-{uuid4().hex}",
        )
        rows_a = await list_activity_events(db, tenant_id=tenant_a, campaign_id=camp_a.id)
        rows_b = await list_activity_events(db, tenant_id=tenant_b, campaign_id=camp_b.id)
        assert all(r.tenant_id == tenant_a for r in rows_a)
        assert all(r.tenant_id == tenant_b for r in rows_b)
        assert not ({r.id for r in rows_a} & {r.id for r in rows_b})
        await db.commit()


@pytest.mark.asyncio
async def test_ordering_occurred_at_then_id_only() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]
    t0 = datetime(2026, 7, 21, 9, 0, tzinfo=timezone.utc)

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign(db, tenant_id=tenant_id)
        # Insert out of chronological order; list must still sort by occurred_at, id.
        mid = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="BudgetChanged",
            event_version="1",
            payload={"currency": "EUR", "amount": 100},
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(minutes=3),
        )
        early = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="FlightStarted",
            event_version="1",
            payload=_flight_started_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0,
        )
        late = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="FlightCompleted",
            event_version="1",
            payload=_flight_completed_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=t0 + timedelta(minutes=15),
        )
        rows = await list_activity_events(db, tenant_id=tenant_id, campaign_id=camp.id)
        subset = [r for r in rows if r.id in {early.id, mid.id, late.id}]
        assert [r.id for r in subset] == [early.id, mid.id, late.id]
        assert ACTIVITY_LIST_ORDER == ("occurred_at", "id")
        await db.commit()


@pytest.mark.asyncio
async def test_payload_validation_semantic_allowlist() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign(db, tenant_id=tenant_id)

        # Foreign fields from another event type rejected.
        with pytest.raises(InvalidActivityPayload, match="unknown payload fields"):
            await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                flight_id=flight.id,
                event_type="FlightStarted",
                event_version="1",
                payload={**_flight_started_payload(), "currency": "EUR", "amount": 10},
                actor_type=ACTOR_TYPE_SYSTEM,
            )

        # Envelope flight_id required for FlightStarted.
        with pytest.raises(InvalidActivityPayload, match="flight_id is required"):
            await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                event_type="FlightStarted",
                event_version="1",
                payload=_flight_started_payload(),
                actor_type=ACTOR_TYPE_SYSTEM,
            )

        # BudgetChanged requires semantic amount fields.
        with pytest.raises(InvalidActivityPayload):
            await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                flight_id=flight.id,
                event_type="BudgetChanged",
                event_version="1",
                payload={"currency": "EUR"},
                actor_type=ACTOR_TYPE_SYSTEM,
            )

        ok = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            event_type="FlightStarted",
            event_version="1",
            payload=_flight_started_payload(),
            actor_type=ACTOR_TYPE_SYSTEM,
            occurred_at=datetime(2026, 7, 21, 9, 0, tzinfo=timezone.utc),
        )
        assert ok.flight_id == flight.id
        assert ok.occurred_at is not None
        await db.commit()


@pytest.mark.asyncio
async def test_version_validation_per_event_type() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign(db, tenant_id=tenant_id)
        with pytest.raises(UnsupportedActivityEventVersion):
            await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                flight_id=flight.id,
                event_type="FlightStarted",
                event_version="99",
                payload=_flight_started_payload(),
                actor_type=ACTOR_TYPE_SYSTEM,
            )
        with pytest.raises(UnknownActivityEventType):
            await append_activity_event(
                db,
                tenant_id=tenant_id,
                campaign_id=camp.id,
                event_type="NotARealEvent",
                event_version="1",
                payload={},
                actor_type=ACTOR_TYPE_SYSTEM,
            )
        await db.commit()


@pytest.mark.asyncio
async def test_nullable_references_and_external_entity_refs() -> None:
    data = await _init_data()
    tenant_id = data["tenant_id"]

    async with async_session_maker() as db:
        camp, flight = await _seed_campaign(db, tenant_id=tenant_id)
        # Campaign-level event: flight/endpoint/submission/result/outcome may be null.
        created = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            event_type="CampaignCreated",
            event_version="1",
            payload={},
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        assert created.flight_id is None
        assert created.endpoint_id is None
        assert created.submission_id is None
        assert created.result_id is None
        assert created.outcome_id is None

        lead_id = str(uuid4())
        submission_id = str(uuid4())
        lead = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            submission_id=submission_id,
            event_type="LeadCreated",
            event_version="1",
            payload={
                "lead_id": lead_id,
                "submission_id": submission_id,
                "module_owner": "recruitment",
            },
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        assert lead.payload["lead_id"] == lead_id
        assert lead.submission_id == submission_id
        model_cols = {c.key for c in inspect(AcquisitionActivityEvent).columns}
        assert "lead_id" not in model_cols
        assert "candidate_id" not in model_cols

        endpoint = await append_activity_event(
            db,
            tenant_id=tenant_id,
            campaign_id=camp.id,
            flight_id=flight.id,
            endpoint_id="ep-form-1",
            event_type="EndpointChanged",
            event_version="1",
            payload={"endpoint_id": "ep-form-1", "change_kind": "primary"},
            actor_type=ACTOR_TYPE_SYSTEM,
        )
        assert endpoint.endpoint_id == "ep-form-1"
        await db.commit()


@pytest.mark.asyncio
async def test_alembic_downgrade_upgrade_roundtrip() -> None:
    up = _run_alembic("upgrade", "head")
    assert up.returncode == 0, up.stderr + up.stdout

    down = _run_alembic("downgrade", _BEFORE_ACTIVITY)
    assert down.returncode == 0, down.stderr + down.stdout

    async with async_session_maker() as session:
        present = await session.execute(
            text("SELECT to_regclass('public.acquisition_activity_events')")
        )
        assert present.scalar() is None

    up2 = _run_alembic("upgrade", "head")
    assert up2.returncode == 0, up2.stderr + up2.stdout

    async with async_session_maker() as session:
        present = await session.execute(
            text("SELECT to_regclass('public.acquisition_activity_events')")
        )
        assert present.scalar() == "acquisition_activity_events"
