"""C2.3 PR-1 — Campaign draft/publish + run snapshot lifecycle.

No HTTP, no audience resolver, no Intent emission, no send path.
Campaign never creates Thread / Message / Delivery here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.communications.campaign.errors import CampaignDomainError
from backend.app.models.communication_campaign import (
    CAMPAIGN_RUN_STATUS_PENDING,
    CAMPAIGN_STATUS_ACTIVE,
    CAMPAIGN_STATUS_ARCHIVED,
    RUN_ITEM_STATUS_EMITTED,
    RUN_ITEM_STATUS_FAILED,
    RUN_ITEM_STATUS_PENDING,
    RUN_ITEM_STATUS_READY,
    RUN_ITEM_STATUS_SKIPPED,
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    CommunicationCampaign,
    CommunicationCampaignAudienceDefinition,
    CommunicationCampaignRecipient,
    CommunicationCampaignRun,
    CommunicationCampaignRunItem,
    CommunicationCampaignVersion,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm_key(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if not key or len(key) > 128:
        raise CampaignDomainError("invalid_campaign_key", "campaign key is required (≤128)")
    return key


def _norm_intent_key(raw: str) -> str:
    intent = str(raw or "").strip()
    if not intent or len(intent) > 128:
        raise CampaignDomainError("invalid_intent_key", "intent_key is required (≤128)")
    return intent


def _norm_idempotency_key(raw: str) -> str:
    key = str(raw or "").strip()
    if not key or len(key) > 128:
        raise CampaignDomainError(
            "invalid_idempotency_key",
            "idempotency_key is required (≤128)",
        )
    return key


def _assert_draft(version: CommunicationCampaignVersion) -> None:
    if not version.is_draft:
        raise CampaignDomainError(
            "version_not_draft",
            "Only draft CampaignVersion is editable",
            details={"version_id": str(version.id), "status": version.status},
        )


def _assert_not_published_mutation(version: CommunicationCampaignVersion) -> None:
    if version.is_published:
        raise CampaignDomainError(
            "published_immutable",
            "Published CampaignVersion is immutable",
            details={"version_id": str(version.id)},
        )


def assert_version_immutable_for_write(version: CommunicationCampaignVersion) -> None:
    """Public guard for callers that must refuse published mutations."""
    _assert_not_published_mutation(version)


async def create_campaign_with_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    key: str,
    name: str,
    description: str | None = None,
    intent_key: str,
    preferred_template_key: str | None = None,
    channel: str | None = None,
    plan: dict[str, Any] | None = None,
    audience_definition_type: str = "filter",
    audience_definition: dict[str, Any] | None = None,
) -> tuple[CommunicationCampaign, CommunicationCampaignVersion]:
    """Create Campaign + initial draft version (version_number=0) + audience definition."""
    tid = str(tenant_id or "").strip()
    if not tid:
        raise CampaignDomainError("tenant_required", "tenant_id is required")
    campaign_key = _norm_key(key)
    campaign_name = str(name or "").strip() or campaign_key
    intent = _norm_intent_key(intent_key)

    exists = (
        await db.execute(
            select(CommunicationCampaign.id).where(
                CommunicationCampaign.tenant_id == tid,
                CommunicationCampaign.key == campaign_key,
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise CampaignDomainError(
            "campaign_key_exists",
            f"Campaign key already exists: {campaign_key}",
            details={"key": campaign_key},
        )

    campaign = CommunicationCampaign(
        id=str(uuid4()),
        tenant_id=tid,
        key=campaign_key,
        name=campaign_name,
        description=(str(description).strip() if description else None),
        status=CAMPAIGN_STATUS_ACTIVE,
    )
    draft = CommunicationCampaignVersion(
        id=str(uuid4()),
        tenant_id=tid,
        campaign_id=campaign.id,
        version_number=0,
        status=VERSION_STATUS_DRAFT,
        intent_key=intent,
        preferred_template_key=(
            str(preferred_template_key).strip() if preferred_template_key else None
        ),
        channel=(str(channel).strip().lower() if channel else None),
        plan=dict(plan or {}),
        meta={},
    )
    audience = CommunicationCampaignAudienceDefinition(
        id=str(uuid4()),
        version_id=draft.id,
        definition_type=str(audience_definition_type or "filter").strip() or "filter",
        definition=dict(audience_definition or {}),
        meta={},
    )
    db.add(campaign)
    db.add(draft)
    db.add(audience)
    await db.flush()
    return campaign, await get_draft_version(db, tenant_id=tid, campaign_id=str(campaign.id))


async def get_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> CommunicationCampaign:
    row = (
        await db.execute(
            select(CommunicationCampaign).where(
                CommunicationCampaign.tenant_id == tenant_id,
                CommunicationCampaign.id == campaign_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise CampaignDomainError(
            "campaign_not_found",
            "Campaign not found",
            details={"campaign_id": campaign_id},
        )
    return row


async def get_draft_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> CommunicationCampaignVersion:
    row = (
        await db.execute(
            select(CommunicationCampaignVersion)
            .options(
                selectinload(CommunicationCampaignVersion.audience_definition),
            )
            .where(
                CommunicationCampaignVersion.tenant_id == tenant_id,
                CommunicationCampaignVersion.campaign_id == campaign_id,
                CommunicationCampaignVersion.status == VERSION_STATUS_DRAFT,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise CampaignDomainError(
            "draft_not_found",
            "Draft CampaignVersion not found",
            details={"campaign_id": campaign_id},
        )
    return row


async def update_draft_content(
    db: AsyncSession,
    *,
    tenant_id: str,
    version: CommunicationCampaignVersion,
    intent_key: str | None = None,
    preferred_template_key: str | None = None,
    channel: str | None = None,
    plan: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    clear_preferred_template_key: bool = False,
    clear_channel: bool = False,
) -> CommunicationCampaignVersion:
    if str(version.tenant_id) != str(tenant_id):
        raise CampaignDomainError("tenant_mismatch", "version tenant mismatch")
    _assert_draft(version)
    _assert_not_published_mutation(version)

    if intent_key is not None:
        version.intent_key = _norm_intent_key(intent_key)
    if clear_preferred_template_key:
        version.preferred_template_key = None
    elif preferred_template_key is not None:
        version.preferred_template_key = str(preferred_template_key).strip() or None
    if clear_channel:
        version.channel = None
    elif channel is not None:
        version.channel = str(channel).strip().lower() or None
    if plan is not None:
        version.plan = dict(plan)
    if meta is not None:
        version.meta = dict(meta)
    await db.flush()
    return version


async def upsert_draft_audience_definition(
    db: AsyncSession,
    *,
    tenant_id: str,
    version: CommunicationCampaignVersion,
    definition_type: str | None = None,
    definition: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> CommunicationCampaignAudienceDefinition:
    """Replace audience *definition* on a draft version (not a recipient snapshot)."""
    if str(version.tenant_id) != str(tenant_id):
        raise CampaignDomainError("tenant_mismatch", "version tenant mismatch")
    _assert_draft(version)
    _assert_not_published_mutation(version)

    row = version.audience_definition
    if row is None:
        row = CommunicationCampaignAudienceDefinition(
            id=str(uuid4()),
            version_id=str(version.id),
            definition_type="filter",
            definition={},
            meta={},
        )
        db.add(row)

    if definition_type is not None:
        row.definition_type = str(definition_type).strip() or "filter"
    if definition is not None:
        row.definition = dict(definition)
    if meta is not None:
        row.meta = dict(meta)
    await db.flush()
    db.expire(version, ["audience_definition"])
    return row


async def publish_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    actor_user_id: str | None = None,
) -> CommunicationCampaignVersion:
    """Publish creates a new immutable CampaignVersion from the current draft.

    Draft remains editable. Published versions are never mutated in place.
    Audience definition is cloned onto the published version.
    """
    draft = await get_draft_version(db, tenant_id=tenant_id, campaign_id=campaign_id)
    _assert_draft(draft)
    if not str(draft.intent_key or "").strip():
        raise CampaignDomainError(
            "intent_key_required",
            "Cannot publish campaign without intent_key",
            details={"campaign_id": campaign_id},
        )
    if draft.audience_definition is None:
        raise CampaignDomainError(
            "audience_definition_required",
            "Cannot publish campaign without audience definition",
            details={"campaign_id": campaign_id},
        )

    max_published = (
        await db.execute(
            select(
                func.coalesce(func.max(CommunicationCampaignVersion.version_number), 0)
            ).where(
                CommunicationCampaignVersion.tenant_id == tenant_id,
                CommunicationCampaignVersion.campaign_id == campaign_id,
                CommunicationCampaignVersion.status == VERSION_STATUS_PUBLISHED,
            )
        )
    ).scalar_one()
    next_number = int(max_published or 0) + 1

    published_id = str(uuid4())
    published = CommunicationCampaignVersion(
        id=published_id,
        tenant_id=tenant_id,
        campaign_id=campaign_id,
        version_number=next_number,
        status=VERSION_STATUS_PUBLISHED,
        intent_key=draft.intent_key,
        preferred_template_key=draft.preferred_template_key,
        channel=draft.channel,
        plan=dict(draft.plan or {}),
        meta=dict(draft.meta or {}),
        published_at=_now(),
        published_by=(str(actor_user_id).strip() if actor_user_id else None),
    )
    db.add(published)

    src_def = draft.audience_definition
    db.add(
        CommunicationCampaignAudienceDefinition(
            id=str(uuid4()),
            version_id=published_id,
            definition_type=src_def.definition_type,
            definition=dict(src_def.definition or {}),
            meta=dict(src_def.meta or {}),
        )
    )
    await db.flush()
    return (
        await db.execute(
            select(CommunicationCampaignVersion)
            .options(selectinload(CommunicationCampaignVersion.audience_definition))
            .where(CommunicationCampaignVersion.id == published_id)
        )
    ).scalar_one()


async def get_latest_published_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> CommunicationCampaignVersion | None:
    return (
        await db.execute(
            select(CommunicationCampaignVersion)
            .options(selectinload(CommunicationCampaignVersion.audience_definition))
            .where(
                CommunicationCampaignVersion.tenant_id == tenant_id,
                CommunicationCampaignVersion.campaign_id == campaign_id,
                CommunicationCampaignVersion.status == VERSION_STATUS_PUBLISHED,
            )
            .order_by(CommunicationCampaignVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def get_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    version_id: str,
) -> CommunicationCampaignVersion:
    row = (
        await db.execute(
            select(CommunicationCampaignVersion)
            .options(selectinload(CommunicationCampaignVersion.audience_definition))
            .where(
                CommunicationCampaignVersion.tenant_id == tenant_id,
                CommunicationCampaignVersion.campaign_id == campaign_id,
                CommunicationCampaignVersion.id == version_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise CampaignDomainError(
            "version_not_found",
            "CampaignVersion not found",
            details={"campaign_id": campaign_id, "version_id": version_id},
        )
    return row


async def archive_campaign(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
) -> CommunicationCampaign:
    campaign = await get_campaign(db, tenant_id=tenant_id, campaign_id=campaign_id)
    campaign.status = CAMPAIGN_STATUS_ARCHIVED
    await db.flush()
    return campaign


async def create_run_with_snapshot(
    db: AsyncSession,
    *,
    tenant_id: str,
    campaign_id: str,
    campaign_version_id: str,
    idempotency_key: str,
    recipients: Sequence[dict[str, Any]],
    audience_snapshot_meta: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> CommunicationCampaignRun:
    """Create a Run pinned to campaign_version_id with a frozen recipient snapshot.

    Idempotent: same tenant + idempotency_key returns the existing run.
    Recipients are stored as CampaignRecipient rows (snapshot), not re-resolved
    from the version's AudienceDefinition. Resolver product logic is PR-2.
    """
    tid = str(tenant_id or "").strip()
    if not tid:
        raise CampaignDomainError("tenant_required", "tenant_id is required")
    idem = _norm_idempotency_key(idempotency_key)

    existing = (
        await db.execute(
            select(CommunicationCampaignRun)
            .options(
                selectinload(CommunicationCampaignRun.recipients),
                selectinload(CommunicationCampaignRun.items),
            )
            .where(
                CommunicationCampaignRun.tenant_id == tid,
                CommunicationCampaignRun.idempotency_key == idem,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    await get_campaign(db, tenant_id=tid, campaign_id=campaign_id)
    version = await get_version(
        db,
        tenant_id=tid,
        campaign_id=campaign_id,
        version_id=campaign_version_id,
    )
    if not version.is_published:
        raise CampaignDomainError(
            "version_not_published",
            "Run must reference a published CampaignVersion",
            details={"campaign_version_id": campaign_version_id},
        )

    frozen_at = _now()
    run = CommunicationCampaignRun(
        id=str(uuid4()),
        tenant_id=tid,
        campaign_id=campaign_id,
        campaign_version_id=str(version.id),
        idempotency_key=idem,
        status=CAMPAIGN_RUN_STATUS_PENDING,
        audience_snapshot={
            "frozen_at": frozen_at.isoformat(),
            "recipient_count": len(list(recipients or [])),
            "definition_fingerprint": {
                "version_id": str(version.id),
                "definition_type": (
                    version.audience_definition.definition_type
                    if version.audience_definition
                    else None
                ),
            },
            **dict(audience_snapshot_meta or {}),
        },
        meta=dict(meta or {}),
    )
    db.add(run)
    await db.flush()

    for raw in recipients or []:
        entity_type = str(raw.get("entity_type") or "").strip()
        entity_id = str(raw.get("entity_id") or "").strip()
        address = str(raw.get("address") or "").strip()
        if not address:
            raise CampaignDomainError(
                "recipient_address_required",
                "Each snapshot recipient requires address",
            )
        recipient = CommunicationCampaignRecipient(
            id=str(uuid4()),
            run_id=str(run.id),
            entity_type=entity_type,
            entity_id=entity_id,
            address=address,
            label=(str(raw["label"]).strip() if raw.get("label") else None),
            snapshot=dict(raw.get("snapshot") or {}),
        )
        db.add(recipient)
        await db.flush()
        db.add(
            CommunicationCampaignRunItem(
                id=str(uuid4()),
                run_id=str(run.id),
                recipient_id=str(recipient.id),
                status=RUN_ITEM_STATUS_PENDING,
                reason_codes=[],
                meta={},
            )
        )

    await db.flush()
    return (
        await db.execute(
            select(CommunicationCampaignRun)
            .options(
                selectinload(CommunicationCampaignRun.recipients),
                selectinload(CommunicationCampaignRun.items),
            )
            .where(CommunicationCampaignRun.id == str(run.id))
        )
    ).scalar_one()


async def mark_run_item_outcome(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
    item_id: str,
    status: str,
    reason_codes: Sequence[Any] | None = None,
    reason_message: str | None = None,
) -> CommunicationCampaignRunItem:
    """Update one item's outcome without affecting sibling items (isolation law)."""
    allowed = {
        RUN_ITEM_STATUS_PENDING,
        RUN_ITEM_STATUS_READY,
        RUN_ITEM_STATUS_EMITTED,
        RUN_ITEM_STATUS_SKIPPED,
        RUN_ITEM_STATUS_FAILED,
    }
    st = str(status or "").strip().lower()
    if st not in allowed:
        raise CampaignDomainError(
            "invalid_run_item_status",
            f"Unknown run item status: {status}",
            details={"allowed": sorted(allowed)},
        )

    run = (
        await db.execute(
            select(CommunicationCampaignRun).where(
                CommunicationCampaignRun.tenant_id == tenant_id,
                CommunicationCampaignRun.id == run_id,
            )
        )
    ).scalar_one_or_none()
    if run is None:
        raise CampaignDomainError(
            "run_not_found",
            "CampaignRun not found",
            details={"run_id": run_id},
        )

    item = (
        await db.execute(
            select(CommunicationCampaignRunItem).where(
                CommunicationCampaignRunItem.id == item_id,
                CommunicationCampaignRunItem.run_id == run_id,
            )
        )
    ).scalar_one_or_none()
    if item is None:
        raise CampaignDomainError(
            "run_item_not_found",
            "CampaignRunItem not found",
            details={"run_id": run_id, "item_id": item_id},
        )

    item.status = st
    item.reason_codes = list(reason_codes or [])
    item.reason_message = (
        str(reason_message).strip() if reason_message is not None else item.reason_message
    )
    await db.flush()
    return item


async def get_run(
    db: AsyncSession,
    *,
    tenant_id: str,
    run_id: str,
) -> CommunicationCampaignRun:
    row = (
        await db.execute(
            select(CommunicationCampaignRun)
            .options(
                selectinload(CommunicationCampaignRun.recipients),
                selectinload(CommunicationCampaignRun.items),
            )
            .where(
                CommunicationCampaignRun.tenant_id == tenant_id,
                CommunicationCampaignRun.id == run_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise CampaignDomainError(
            "run_not_found",
            "CampaignRun not found",
            details={"run_id": run_id},
        )
    return row


__all__ = [
    "assert_version_immutable_for_write",
    "create_campaign_with_draft",
    "get_campaign",
    "get_draft_version",
    "update_draft_content",
    "upsert_draft_audience_definition",
    "publish_draft",
    "get_latest_published_version",
    "get_version",
    "archive_campaign",
    "create_run_with_snapshot",
    "mark_run_item_outcome",
    "get_run",
]
