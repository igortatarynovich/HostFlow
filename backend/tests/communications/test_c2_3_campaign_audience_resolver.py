"""C2.3 PR-2 — Pure Audience Resolver contract tests."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.communications.campaign import (
    DEFINITION_TYPE_FILTER,
    DEFINITION_TYPE_STATIC_LIST,
    AudienceDefinitionPayload,
    CampaignDomainError,
    EntityCandidate,
    ResolveContext,
    create_campaign_with_draft,
    create_run_from_audience,
    dry_run,
    publish_draft,
    resolve,
)
from backend.app.communications.campaign.audience.types import (
    DIAG_EMPTY_AUDIENCE,
    DIAG_ENTITY_POOL_REQUIRED,
    DIAG_UNKNOWN_DEFINITION_TYPE,
)

AUDIENCE_DIR = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "communications"
    / "campaign"
    / "audience"
)

FORBIDDEN_IMPORT_PREFIXES = (
    "sqlalchemy",
    "backend.app.db",
    "app.db",
    "backend.app.models",
    "app.models",
    "backend.app.communications.workspace_commands",
    "backend.app.communications.send_communication",
    "backend.app.communications.execute_intent",
    "backend.app.modules",
    "app.modules",
)


def test_pure_audience_resolver_import_gate():
    offenders: list[str] = []
    for path in AUDIENCE_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            if isinstance(node, ast.Import):
                mods.extend(a.name for a in node.names)
            for mod in mods:
                if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_IMPORT_PREFIXES):
                    offenders.append(f"{path.name}: {mod}")
    assert offenders == [], f"Pure audience resolver gate violated: {offenders}"


def test_static_list_resolve_deterministic_and_dedupes():
    definition = AudienceDefinitionPayload(
        definition_type=DEFINITION_TYPE_STATIC_LIST,
        definition={
            "recipients": [
                {
                    "entity_type": "candidate",
                    "entity_id": "b",
                    "address": "b@example.com",
                },
                {
                    "entity_type": "candidate",
                    "entity_id": "a",
                    "address": "a@example.com",
                    "label": "Ada",
                },
                {
                    "entity_type": "candidate",
                    "entity_id": "a",
                    "address": "a@example.com",
                },
                {
                    "entity_type": "candidate",
                    "entity_id": "c",
                    "address": "",
                },
            ]
        },
        version_id="ver-1",
    )
    r1 = resolve(definition)
    r2 = dry_run(definition)
    assert r1.ok is True
    assert r2.recipients == r1.recipients
    assert [x.address for x in r1.recipients] == ["a@example.com", "b@example.com"]
    assert len(r1.skipped) == 2
    assert r1.to_snapshot_meta()["resolver"] == "communication.campaign.audience.v1"


def test_filter_resolve_matches_pool_without_module_imports():
    definition = AudienceDefinitionPayload(
        definition_type=DEFINITION_TYPE_FILTER,
        definition={"filter": {"op": "eq", "path": "stage", "value": "interview"}},
        version_id="ver-2",
    )
    ctx = ResolveContext(
        entities=(
            EntityCandidate(
                entity_type="candidate",
                entity_id="1",
                address="yes@example.com",
                attributes={"stage": "interview", "name": "Yes"},
            ),
            EntityCandidate(
                entity_type="candidate",
                entity_id="2",
                address="no@example.com",
                attributes={"stage": "applied"},
            ),
            EntityCandidate(
                entity_type="candidate",
                entity_id="3",
                address=None,
                attributes={"stage": "interview"},
            ),
        )
    )
    result = resolve(definition, ctx)
    assert result.ok is True
    assert len(result.recipients) == 1
    assert result.recipients[0].address == "yes@example.com"
    assert result.recipients[0].snapshot["name"] == "Yes"
    assert any("address_required" in s.reason_codes for s in result.skipped)


def test_unknown_definition_type_fails():
    result = resolve(
        AudienceDefinitionPayload(definition_type="magic_query", definition={})
    )
    assert result.ok is False
    assert any(d.code == DIAG_UNKNOWN_DEFINITION_TYPE for d in result.diagnostics)


def test_require_entity_pool_flag():
    definition = AudienceDefinitionPayload(
        definition_type=DEFINITION_TYPE_FILTER,
        definition={"filter": {}},
    )
    result = resolve(
        definition,
        ResolveContext(entities=(), extras={"require_entity_pool": True}),
    )
    assert result.ok is False
    assert any(d.code == DIAG_ENTITY_POOL_REQUIRED for d in result.diagnostics)


def test_empty_static_list_ok_with_info_diag():
    result = resolve(
        AudienceDefinitionPayload(
            definition_type=DEFINITION_TYPE_STATIC_LIST,
            definition={"recipients": []},
        )
    )
    assert result.ok is True
    assert result.recipients == ()
    assert any(d.code == DIAG_EMPTY_AUDIENCE for d in result.diagnostics)


@pytest.mark.asyncio
async def test_create_run_from_audience_freezes_snapshot(db, tenant_id: str):
    campaign, _draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_aud_{uuid4().hex[:8]}",
        name="audience resolve",
        intent_key="campaign_outreach",
        audience_definition_type=DEFINITION_TYPE_STATIC_LIST,
        audience_definition={
            "recipients": [
                {
                    "entity_type": "candidate",
                    "entity_id": "x1",
                    "address": "x1@example.com",
                    "snapshot": {"wave": 1},
                }
            ]
        },
    )
    published = await publish_draft(db, tenant_id=tenant_id, campaign_id=str(campaign.id))
    run = await create_run_from_audience(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
        campaign_version_id=str(published.id),
        idempotency_key=f"aud-{uuid4().hex}",
    )
    assert len(run.recipients) == 1
    assert run.recipients[0].address == "x1@example.com"
    assert run.recipients[0].snapshot["wave"] == 1
    assert run.audience_snapshot.get("resolver") == "communication.campaign.audience.v1"
    assert run.campaign_version_id == published.id


@pytest.mark.asyncio
async def test_create_run_from_audience_filter_pool(db, tenant_id: str):
    campaign, _draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_filt_{uuid4().hex[:8]}",
        name="filter pool",
        intent_key="campaign_outreach",
        audience_definition_type=DEFINITION_TYPE_FILTER,
        audience_definition={
            "filter": {"op": "eq", "path": "locale", "value": "pl"},
        },
    )
    published = await publish_draft(db, tenant_id=tenant_id, campaign_id=str(campaign.id))
    run = await create_run_from_audience(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
        campaign_version_id=str(published.id),
        idempotency_key=f"filt-{uuid4().hex}",
        resolve_context=ResolveContext(
            entities=(
                EntityCandidate(
                    entity_type="lead",
                    entity_id="L1",
                    address="pl@example.com",
                    attributes={"locale": "pl"},
                ),
                EntityCandidate(
                    entity_type="lead",
                    entity_id="L2",
                    address="de@example.com",
                    attributes={"locale": "de"},
                ),
            )
        ),
    )
    assert {r.address for r in run.recipients} == {"pl@example.com"}


@pytest.mark.asyncio
async def test_create_run_from_audience_rejects_bad_definition(db, tenant_id: str):
    campaign, draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_bad_{uuid4().hex[:8]}",
        name="bad def",
        intent_key="campaign_outreach",
        audience_definition_type="not_a_real_type",
        audience_definition={},
    )
    # Force publish by temporarily using a valid type, then mutate published? —
    # published is immutable; instead publish valid then we can't change type.
    # Create with invalid type: publish still allowed (PR-1 only checks presence).
    published = await publish_draft(db, tenant_id=tenant_id, campaign_id=str(campaign.id))
    assert published.audience_definition.definition_type == "not_a_real_type"
    with pytest.raises(CampaignDomainError) as exc:
        await create_run_from_audience(
            db,
            tenant_id=tenant_id,
            campaign_id=str(campaign.id),
            campaign_version_id=str(published.id),
            idempotency_key=f"bad-{uuid4().hex}",
        )
    assert exc.value.code == "audience_resolve_failed"
    assert draft.id != published.id
