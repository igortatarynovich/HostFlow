"""C2.3 PR-1 — Campaign domain invariants (no UI / no resolver / no send)."""

from __future__ import annotations

import ast
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.communications.campaign import (
    CampaignDomainError,
    create_campaign_with_draft,
    create_run_with_snapshot,
    get_draft_version,
    get_run,
    mark_run_item_outcome,
    publish_draft,
    update_draft_content,
    upsert_draft_audience_definition,
)
from backend.app.communications.campaign.lifecycle import assert_version_immutable_for_write
from backend.app.models.communication_campaign import (
    RUN_ITEM_STATUS_FAILED,
    RUN_ITEM_STATUS_PENDING,
    RUN_ITEM_STATUS_READY,
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    CommunicationCampaignAudienceDefinition,
    CommunicationCampaignRun,
    CommunicationCampaignVersion,
)

REPO = Path(__file__).resolve().parents[2]
CAMPAIGN_PKG = REPO / "app" / "communications" / "campaign"
CAMPAIGN_MODEL = REPO / "app" / "models" / "communication_campaign.py"

FORBIDDEN_MODULE_IMPORT_PREFIXES = (
    "backend.app.modules.recruitment",
    "backend.app.modules.sales",
    "backend.app.modules.hr",
    "backend.app.modules.services",
    "backend.app.modules.finance",
    "app.modules.recruitment",
    "app.modules.sales",
    "app.modules.hr",
    "app.modules.services",
    "app.modules.finance",
)

# emitter.py may call execute_communication_intent (PR-3 platform path).
DOMAIN_SEND_PATH_FILES = frozenset({"lifecycle.py", "errors.py", "payload.py"})
FORBIDDEN_SEND_PATH_TOKENS = (
    "CommunicationSender",
    "execute_communication_intent",
    "dispatch_message",
    "send_email",
    "CommunicationThread",
    "WorkspaceCommand",
)


def _iter_py_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in root.rglob("*.py"):
        yield path


def test_capability_isolation_no_module_imports():
    offenders: list[str] = []
    for path in (*_iter_py_files(CAMPAIGN_PKG), CAMPAIGN_MODEL):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                mod = node.module
                if any(mod == p or mod.startswith(p + ".") for p in FORBIDDEN_MODULE_IMPORT_PREFIXES):
                    offenders.append(f"{path.name}: from {mod}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if any(
                        name == p or name.startswith(p + ".")
                        for p in FORBIDDEN_MODULE_IMPORT_PREFIXES
                    ):
                        offenders.append(f"{path.name}: import {name}")
        if path.name in DOMAIN_SEND_PATH_FILES:
            for token in FORBIDDEN_SEND_PATH_TOKENS:
                if token in text:
                    offenders.append(f"{path.name}: token:{token}")
    assert offenders == [], f"C2.3 capability isolation violated: {offenders}"


def test_orm_tables_use_communication_campaign_prefix():
    text = CAMPAIGN_MODEL.read_text(encoding="utf-8")
    assert '__tablename__ = "communication_campaigns"' in text
    assert '__tablename__ = "communication_campaign_versions"' in text
    assert '__tablename__ = "communication_campaign_audience_definitions"' in text
    assert '__tablename__ = "communication_campaign_recipients"' in text
    assert '__tablename__ = "communication_campaign_runs"' in text
    assert '__tablename__ = "communication_campaign_run_items"' in text


@pytest.mark.asyncio
async def test_publish_creates_immutable_version_and_keeps_draft(db, tenant_id: str):
    campaign, draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_smoke_{uuid4().hex[:8]}",
        name="C2.3 Smoke Campaign",
        intent_key="campaign_outreach",
        preferred_template_key="outreach_email",
        channel="email",
        audience_definition={"segment": "active_candidates"},
    )
    assert draft.status == VERSION_STATUS_DRAFT
    assert draft.version_number == 0
    assert draft.audience_definition is not None
    assert draft.audience_definition.definition["segment"] == "active_candidates"

    published = await publish_draft(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
        actor_user_id="actor-1",
    )
    assert published.status == VERSION_STATUS_PUBLISHED
    assert published.version_number == 1
    assert published.id != draft.id
    assert published.intent_key == "campaign_outreach"
    assert published.published_at is not None
    assert published.audience_definition is not None
    assert published.audience_definition.definition["segment"] == "active_candidates"
    assert published.audience_definition.id != draft.audience_definition.id

    draft2 = await get_draft_version(db, tenant_id=tenant_id, campaign_id=str(campaign.id))
    assert draft2.id == draft.id
    await update_draft_content(
        db,
        tenant_id=tenant_id,
        version=draft2,
        intent_key="manual_outbound",
    )
    assert draft2.intent_key == "manual_outbound"

    with pytest.raises(CampaignDomainError) as exc:
        assert_version_immutable_for_write(published)
    assert exc.value.code == "published_immutable"

    with pytest.raises(CampaignDomainError) as exc2:
        await update_draft_content(
            db,
            tenant_id=tenant_id,
            version=published,
            intent_key="hack",
        )
    assert exc2.value.code == "version_not_draft"

    with pytest.raises(CampaignDomainError) as exc3:
        await upsert_draft_audience_definition(
            db,
            tenant_id=tenant_id,
            version=published,
            definition={"segment": "hacked"},
        )
    assert exc3.value.code == "version_not_draft"

    published2 = await publish_draft(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
    )
    assert published2.version_number == 2
    assert published2.intent_key == "manual_outbound"

    v1 = (
        await db.execute(
            select(CommunicationCampaignVersion).where(
                CommunicationCampaignVersion.id == published.id
            )
        )
    ).scalar_one()
    assert v1.intent_key == "campaign_outreach"
    assert v1.status == VERSION_STATUS_PUBLISHED


@pytest.mark.asyncio
async def test_run_idempotency_and_pins_version(db, tenant_id: str):
    campaign, _draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_run_{uuid4().hex[:8]}",
        name="run idem",
        intent_key="campaign_outreach",
        audience_definition={"filter": "x"},
    )
    published = await publish_draft(db, tenant_id=tenant_id, campaign_id=str(campaign.id))
    idem = f"run-{uuid4().hex}"

    recipients = [
        {
            "entity_type": "candidate",
            "entity_id": "c-1",
            "address": "a@example.com",
            "label": "A",
            "snapshot": {"name": "A"},
        },
        {
            "entity_type": "candidate",
            "entity_id": "c-2",
            "address": "b@example.com",
            "snapshot": {"name": "B"},
        },
    ]
    run1 = await create_run_with_snapshot(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
        campaign_version_id=str(published.id),
        idempotency_key=idem,
        recipients=recipients,
    )
    run2 = await create_run_with_snapshot(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
        campaign_version_id=str(published.id),
        idempotency_key=idem,
        recipients=[
            {
                "entity_type": "candidate",
                "entity_id": "c-999",
                "address": "other@example.com",
            }
        ],
    )
    assert run1.id == run2.id
    assert run1.campaign_version_id == published.id
    assert len(run2.recipients) == 2

    rows = (
        await db.execute(
            select(CommunicationCampaignRun).where(
                CommunicationCampaignRun.tenant_id == tenant_id,
                CommunicationCampaignRun.idempotency_key == idem,
            )
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_audience_snapshot_independent_of_definition_mutation(db, tenant_id: str):
    campaign, draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_snap_{uuid4().hex[:8]}",
        name="snapshot law",
        intent_key="campaign_outreach",
        audience_definition={"segment": "cohort_a"},
    )
    published = await publish_draft(db, tenant_id=tenant_id, campaign_id=str(campaign.id))

    run = await create_run_with_snapshot(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
        campaign_version_id=str(published.id),
        idempotency_key=f"snap-{uuid4().hex}",
        recipients=[
            {
                "entity_type": "candidate",
                "entity_id": "frozen-1",
                "address": "frozen@example.com",
                "snapshot": {"cohort": "a"},
            }
        ],
    )
    frozen_addresses = {r.address for r in run.recipients}
    assert frozen_addresses == {"frozen@example.com"}

    # Mutating draft definition must not change historical run recipients.
    await upsert_draft_audience_definition(
        db,
        tenant_id=tenant_id,
        version=draft,
        definition={"segment": "cohort_b"},
    )
    reloaded = await get_run(db, tenant_id=tenant_id, run_id=str(run.id))
    assert {r.address for r in reloaded.recipients} == {"frozen@example.com"}
    assert reloaded.recipients[0].snapshot["cohort"] == "a"

    # Published version definition remains the one cloned at publish time.
    pub_def = (
        await db.execute(
            select(CommunicationCampaignAudienceDefinition).where(
                CommunicationCampaignAudienceDefinition.version_id == published.id
            )
        )
    ).scalar_one()
    assert pub_def.definition["segment"] == "cohort_a"


@pytest.mark.asyncio
async def test_one_failed_item_does_not_block_siblings(db, tenant_id: str):
    campaign, _draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_iso_{uuid4().hex[:8]}",
        name="item isolation",
        intent_key="campaign_outreach",
        audience_definition={"segment": "all"},
    )
    published = await publish_draft(db, tenant_id=tenant_id, campaign_id=str(campaign.id))
    run = await create_run_with_snapshot(
        db,
        tenant_id=tenant_id,
        campaign_id=str(campaign.id),
        campaign_version_id=str(published.id),
        idempotency_key=f"iso-{uuid4().hex}",
        recipients=[
            {"entity_type": "candidate", "entity_id": "1", "address": "one@example.com"},
            {"entity_type": "candidate", "entity_id": "2", "address": "two@example.com"},
        ],
    )
    items = sorted(run.items, key=lambda i: i.recipient_id)
    assert len(items) == 2
    assert all(i.status == RUN_ITEM_STATUS_PENDING for i in items)

    failed = await mark_run_item_outcome(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        item_id=str(items[0].id),
        status=RUN_ITEM_STATUS_FAILED,
        reason_codes=["invalid_address"],
        reason_message="bad mailbox",
    )
    ready = await mark_run_item_outcome(
        db,
        tenant_id=tenant_id,
        run_id=str(run.id),
        item_id=str(items[1].id),
        status=RUN_ITEM_STATUS_READY,
        reason_codes=[],
    )
    assert failed.status == RUN_ITEM_STATUS_FAILED
    assert failed.reason_codes == ["invalid_address"]
    assert ready.status == RUN_ITEM_STATUS_READY

    reloaded = await get_run(db, tenant_id=tenant_id, run_id=str(run.id))
    by_id = {i.id: i for i in reloaded.items}
    assert by_id[failed.id].status == RUN_ITEM_STATUS_FAILED
    assert by_id[ready.id].status == RUN_ITEM_STATUS_READY


@pytest.mark.asyncio
async def test_cannot_run_against_draft_version(db, tenant_id: str):
    campaign, draft = await create_campaign_with_draft(
        db,
        tenant_id=tenant_id,
        key=f"c2_3_draft_run_{uuid4().hex[:8]}",
        name="draft run blocked",
        intent_key="campaign_outreach",
        audience_definition={"segment": "x"},
    )
    with pytest.raises(CampaignDomainError) as exc:
        await create_run_with_snapshot(
            db,
            tenant_id=tenant_id,
            campaign_id=str(campaign.id),
            campaign_version_id=str(draft.id),
            idempotency_key=f"draft-{uuid4().hex}",
            recipients=[
                {"entity_type": "candidate", "entity_id": "1", "address": "x@example.com"}
            ],
        )
    assert exc.value.code == "version_not_published"
