"""C2.2 PR-1 — Automation draft/publish lifecycle (no HTTP, no evaluator, no send)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence
from uuid import uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.communications.automation.errors import AutomationDomainError
from backend.app.models.communication_automation import (
    DECISION_OUTCOME_FIRE,
    DECISION_OUTCOME_SKIP,
    RECIPIENT_STRATEGIES,
    RULE_STATUS_ACTIVE,
    RULE_STATUS_ARCHIVED,
    VERSION_STATUS_DRAFT,
    VERSION_STATUS_PUBLISHED,
    CommunicationAutomationDecision,
    CommunicationAutomationRule,
    CommunicationAutomationRuleVersion,
    CommunicationAutomationTrigger,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _norm_key(raw: str) -> str:
    key = str(raw or "").strip().lower()
    if not key or len(key) > 128:
        raise AutomationDomainError("invalid_rule_key", "rule key is required (≤128)")
    return key


def _norm_event_type(raw: str) -> str:
    event = str(raw or "").strip()
    if not event or len(event) > 128:
        raise AutomationDomainError("invalid_event_type", "event_type is required (≤128)")
    return event


def _norm_intent_key(raw: str) -> str:
    intent = str(raw or "").strip()
    if not intent or len(intent) > 128:
        raise AutomationDomainError("invalid_intent_key", "intent_key is required (≤128)")
    return intent


def _norm_recipient_strategy(raw: str | None) -> str:
    strategy = str(raw or "origin_primary").strip().lower() or "origin_primary"
    if strategy not in RECIPIENT_STRATEGIES:
        raise AutomationDomainError(
            "invalid_recipient_strategy",
            f"Unknown recipient_strategy: {raw}",
            details={"allowed": sorted(RECIPIENT_STRATEGIES)},
        )
    return strategy


def _assert_draft(version: CommunicationAutomationRuleVersion) -> None:
    if not version.is_draft:
        raise AutomationDomainError(
            "version_not_draft",
            "Only draft AutomationRuleVersion is editable",
            details={"version_id": str(version.id), "status": version.status},
        )


def _assert_not_published_mutation(version: CommunicationAutomationRuleVersion) -> None:
    if version.is_published:
        raise AutomationDomainError(
            "published_immutable",
            "Published AutomationRuleVersion is immutable",
            details={"version_id": str(version.id)},
        )


def assert_version_immutable_for_write(version: CommunicationAutomationRuleVersion) -> None:
    """Public guard for callers that must refuse published mutations."""
    _assert_not_published_mutation(version)


async def create_rule_with_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    key: str,
    name: str,
    description: str | None = None,
    enabled: bool = True,
    priority: int = 0,
    intent_key: str,
    preferred_template_key: str | None = None,
    channel: str | None = None,
    recipient_strategy: str = "origin_primary",
    recipient_config: dict[str, Any] | None = None,
    conditions: dict[str, Any] | None = None,
    variables_mapping: dict[str, Any] | None = None,
    event_types: Sequence[str] = (),
    event_filters: dict[str, dict[str, Any]] | None = None,
) -> tuple[CommunicationAutomationRule, CommunicationAutomationRuleVersion]:
    """Create AutomationRule + initial draft version (version_number=0)."""
    tid = str(tenant_id or "").strip()
    if not tid:
        raise AutomationDomainError("tenant_required", "tenant_id is required")
    rule_key = _norm_key(key)
    rule_name = str(name or "").strip() or rule_key
    intent = _norm_intent_key(intent_key)

    exists = (
        await db.execute(
            select(CommunicationAutomationRule.id).where(
                CommunicationAutomationRule.tenant_id == tid,
                CommunicationAutomationRule.key == rule_key,
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise AutomationDomainError(
            "rule_key_exists",
            f"Automation rule key already exists: {rule_key}",
            details={"key": rule_key},
        )

    rule = CommunicationAutomationRule(
        id=str(uuid4()),
        tenant_id=tid,
        key=rule_key,
        name=rule_name,
        description=(str(description).strip() if description else None),
        status=RULE_STATUS_ACTIVE,
        enabled=bool(enabled),
        priority=int(priority or 0),
    )
    draft = CommunicationAutomationRuleVersion(
        id=str(uuid4()),
        tenant_id=tid,
        rule_id=rule.id,
        version_number=0,
        status=VERSION_STATUS_DRAFT,
        conditions=dict(conditions or {}),
        intent_key=intent,
        preferred_template_key=(
            str(preferred_template_key).strip() if preferred_template_key else None
        ),
        channel=(str(channel).strip().lower() if channel else None),
        recipient_strategy=_norm_recipient_strategy(recipient_strategy),
        recipient_config=dict(recipient_config or {}),
        variables_mapping=dict(variables_mapping or {}),
        meta={},
    )
    db.add(rule)
    db.add(draft)
    await db.flush()

    if event_types:
        await replace_draft_triggers(
            db,
            tenant_id=tid,
            version=draft,
            event_types=event_types,
            event_filters=event_filters,
        )

    await db.flush()
    return rule, await get_draft_version(db, tenant_id=tid, rule_id=str(rule.id))


async def get_rule(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
) -> CommunicationAutomationRule:
    row = (
        await db.execute(
            select(CommunicationAutomationRule).where(
                CommunicationAutomationRule.tenant_id == tenant_id,
                CommunicationAutomationRule.id == rule_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise AutomationDomainError(
            "rule_not_found",
            "AutomationRule not found",
            details={"rule_id": rule_id},
        )
    return row


async def get_draft_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
) -> CommunicationAutomationRuleVersion:
    row = (
        await db.execute(
            select(CommunicationAutomationRuleVersion)
            .options(selectinload(CommunicationAutomationRuleVersion.triggers))
            .where(
                CommunicationAutomationRuleVersion.tenant_id == tenant_id,
                CommunicationAutomationRuleVersion.rule_id == rule_id,
                CommunicationAutomationRuleVersion.status == VERSION_STATUS_DRAFT,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise AutomationDomainError(
            "draft_not_found",
            "Draft AutomationRuleVersion not found",
            details={"rule_id": rule_id},
        )
    return row


async def update_draft_content(
    db: AsyncSession,
    *,
    tenant_id: str,
    version: CommunicationAutomationRuleVersion,
    intent_key: str | None = None,
    preferred_template_key: str | None = None,
    channel: str | None = None,
    recipient_strategy: str | None = None,
    recipient_config: dict[str, Any] | None = None,
    conditions: dict[str, Any] | None = None,
    variables_mapping: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    clear_preferred_template_key: bool = False,
    clear_channel: bool = False,
) -> CommunicationAutomationRuleVersion:
    if str(version.tenant_id) != str(tenant_id):
        raise AutomationDomainError("tenant_mismatch", "version tenant mismatch")
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
    if recipient_strategy is not None:
        version.recipient_strategy = _norm_recipient_strategy(recipient_strategy)
    if recipient_config is not None:
        version.recipient_config = dict(recipient_config)
    if conditions is not None:
        version.conditions = dict(conditions)
    if variables_mapping is not None:
        version.variables_mapping = dict(variables_mapping)
    if meta is not None:
        version.meta = dict(meta)
    await db.flush()
    return version


async def replace_draft_triggers(
    db: AsyncSession,
    *,
    tenant_id: str,
    version: CommunicationAutomationRuleVersion,
    event_types: Sequence[str],
    event_filters: dict[str, dict[str, Any]] | None = None,
) -> list[CommunicationAutomationTrigger]:
    if str(version.tenant_id) != str(tenant_id):
        raise AutomationDomainError("tenant_mismatch", "version tenant mismatch")
    _assert_draft(version)
    _assert_not_published_mutation(version)

    await db.execute(
        delete(CommunicationAutomationTrigger).where(
            CommunicationAutomationTrigger.version_id == str(version.id)
        )
    )
    await db.flush()

    filters = event_filters or {}
    created: list[CommunicationAutomationTrigger] = []
    seen: set[str] = set()
    for raw in event_types:
        event_type = _norm_event_type(raw)
        if event_type in seen:
            raise AutomationDomainError(
                "duplicate_event_type",
                f"Duplicate event_type: {event_type}",
                details={"event_type": event_type},
            )
        seen.add(event_type)
        row = CommunicationAutomationTrigger(
            id=str(uuid4()),
            version_id=str(version.id),
            event_type=event_type,
            event_filter=dict(filters.get(event_type) or {}),
        )
        db.add(row)
        created.append(row)
    await db.flush()
    db.expire(version, ["triggers"])
    return created


def _clone_triggers_to_version(
    *,
    source: CommunicationAutomationRuleVersion,
    target_id: str,
) -> list[CommunicationAutomationTrigger]:
    return [
        CommunicationAutomationTrigger(
            id=str(uuid4()),
            version_id=target_id,
            event_type=t.event_type,
            event_filter=dict(t.event_filter or {}),
        )
        for t in (source.triggers or [])
    ]


async def publish_draft(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
    actor_user_id: str | None = None,
) -> CommunicationAutomationRuleVersion:
    """Publish creates a new immutable RuleVersion from the current draft.

    Draft remains editable. Published versions are never mutated in place.
    """
    draft = await get_draft_version(db, tenant_id=tenant_id, rule_id=rule_id)
    _assert_draft(draft)
    if not str(draft.intent_key or "").strip():
        raise AutomationDomainError(
            "intent_key_required",
            "Cannot publish rule without intent_key",
            details={"rule_id": rule_id},
        )
    if not (draft.triggers or []):
        raise AutomationDomainError(
            "trigger_required",
            "Cannot publish rule without at least one trigger",
            details={"rule_id": rule_id},
        )

    max_published = (
        await db.execute(
            select(
                func.coalesce(func.max(CommunicationAutomationRuleVersion.version_number), 0)
            ).where(
                CommunicationAutomationRuleVersion.tenant_id == tenant_id,
                CommunicationAutomationRuleVersion.rule_id == rule_id,
                CommunicationAutomationRuleVersion.status == VERSION_STATUS_PUBLISHED,
            )
        )
    ).scalar_one()
    next_number = int(max_published or 0) + 1

    published_id = str(uuid4())
    published = CommunicationAutomationRuleVersion(
        id=published_id,
        tenant_id=tenant_id,
        rule_id=rule_id,
        version_number=next_number,
        status=VERSION_STATUS_PUBLISHED,
        conditions=dict(draft.conditions or {}),
        intent_key=draft.intent_key,
        preferred_template_key=draft.preferred_template_key,
        channel=draft.channel,
        recipient_strategy=draft.recipient_strategy,
        recipient_config=dict(draft.recipient_config or {}),
        variables_mapping=dict(draft.variables_mapping or {}),
        meta=dict(draft.meta or {}),
        published_at=_now(),
        published_by=(str(actor_user_id).strip() if actor_user_id else None),
    )
    db.add(published)
    for row in _clone_triggers_to_version(source=draft, target_id=published_id):
        db.add(row)
    await db.flush()
    return (
        await db.execute(
            select(CommunicationAutomationRuleVersion)
            .options(selectinload(CommunicationAutomationRuleVersion.triggers))
            .where(CommunicationAutomationRuleVersion.id == published_id)
        )
    ).scalar_one()


async def set_rule_enabled(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
    enabled: bool,
) -> CommunicationAutomationRule:
    rule = await get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
    rule.enabled = bool(enabled)
    await db.flush()
    return rule


async def archive_rule(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
) -> CommunicationAutomationRule:
    rule = await get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
    rule.status = RULE_STATUS_ARCHIVED
    rule.enabled = False
    await db.flush()
    return rule


async def get_latest_published_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
) -> CommunicationAutomationRuleVersion | None:
    return (
        await db.execute(
            select(CommunicationAutomationRuleVersion)
            .options(selectinload(CommunicationAutomationRuleVersion.triggers))
            .where(
                CommunicationAutomationRuleVersion.tenant_id == tenant_id,
                CommunicationAutomationRuleVersion.rule_id == rule_id,
                CommunicationAutomationRuleVersion.status == VERSION_STATUS_PUBLISHED,
            )
            .order_by(CommunicationAutomationRuleVersion.version_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def list_rules(
    db: AsyncSession,
    *,
    tenant_id: str,
    include_archived: bool = False,
) -> list[CommunicationAutomationRule]:
    stmt = select(CommunicationAutomationRule).where(
        CommunicationAutomationRule.tenant_id == tenant_id
    )
    if not include_archived:
        stmt = stmt.where(CommunicationAutomationRule.status == RULE_STATUS_ACTIVE)
    stmt = stmt.order_by(
        CommunicationAutomationRule.priority.desc(),
        CommunicationAutomationRule.key.asc(),
    )
    return list((await db.execute(stmt)).scalars().all())


async def list_versions(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
) -> list[CommunicationAutomationRuleVersion]:
    await get_rule(db, tenant_id=tenant_id, rule_id=rule_id)
    rows = (
        await db.execute(
            select(CommunicationAutomationRuleVersion)
            .options(selectinload(CommunicationAutomationRuleVersion.triggers))
            .where(
                CommunicationAutomationRuleVersion.tenant_id == tenant_id,
                CommunicationAutomationRuleVersion.rule_id == rule_id,
            )
            .order_by(CommunicationAutomationRuleVersion.version_number.asc())
        )
    ).scalars().all()
    return list(rows)


async def get_version(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
    version_id: str,
) -> CommunicationAutomationRuleVersion:
    row = (
        await db.execute(
            select(CommunicationAutomationRuleVersion)
            .options(selectinload(CommunicationAutomationRuleVersion.triggers))
            .where(
                CommunicationAutomationRuleVersion.tenant_id == tenant_id,
                CommunicationAutomationRuleVersion.rule_id == rule_id,
                CommunicationAutomationRuleVersion.id == version_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise AutomationDomainError(
            "version_not_found",
            "AutomationRuleVersion not found",
            details={"rule_id": rule_id, "version_id": version_id},
        )
    return row


async def list_decisions(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str | None = None,
    limit: int = 50,
) -> list[CommunicationAutomationDecision]:
    lim = max(1, min(int(limit or 50), 200))
    stmt = select(CommunicationAutomationDecision).where(
        CommunicationAutomationDecision.tenant_id == tenant_id
    )
    if rule_id:
        stmt = stmt.where(CommunicationAutomationDecision.rule_id == rule_id)
    stmt = stmt.order_by(CommunicationAutomationDecision.created_at.desc()).limit(lim)
    return list((await db.execute(stmt)).scalars().all())


async def record_decision(
    db: AsyncSession,
    *,
    tenant_id: str,
    rule_id: str,
    rule_version_id: str,
    source_event_id: str,
    event_type: str,
    outcome: str,
    reason_codes: Sequence[Any] | None = None,
    trigger_id: str | None = None,
    intent_key: str | None = None,
    intent_request_snapshot: dict[str, Any] | None = None,
    correlation_id: str | None = None,
    meta: dict[str, Any] | None = None,
) -> CommunicationAutomationDecision:
    """Persist a durable evaluate outcome (PR-1 storage; evaluator lands in PR-2)."""
    tid = str(tenant_id or "").strip()
    if not tid:
        raise AutomationDomainError("tenant_required", "tenant_id is required")
    out = str(outcome or "").strip().lower()
    if out not in {DECISION_OUTCOME_FIRE, DECISION_OUTCOME_SKIP}:
        raise AutomationDomainError(
            "invalid_decision_outcome",
            f"outcome must be fire|skip, got {outcome!r}",
        )
    event = _norm_event_type(event_type)
    source = str(source_event_id or "").strip()
    if not source:
        raise AutomationDomainError("source_event_required", "source_event_id is required")

    row = CommunicationAutomationDecision(
        id=str(uuid4()),
        tenant_id=tid,
        rule_id=str(rule_id),
        rule_version_id=str(rule_version_id),
        trigger_id=(str(trigger_id) if trigger_id else None),
        source_event_id=source,
        event_type=event,
        outcome=out,
        reason_codes=list(reason_codes or []),
        intent_key=(str(intent_key).strip() if intent_key else None),
        intent_request_snapshot=(
            dict(intent_request_snapshot) if intent_request_snapshot is not None else None
        ),
        correlation_id=(str(correlation_id).strip() if correlation_id else None),
        meta=dict(meta or {}),
    )
    db.add(row)
    await db.flush()
    return row


__all__ = [
    "assert_version_immutable_for_write",
    "create_rule_with_draft",
    "get_rule",
    "get_draft_version",
    "update_draft_content",
    "replace_draft_triggers",
    "publish_draft",
    "set_rule_enabled",
    "archive_rule",
    "get_latest_published_version",
    "list_rules",
    "list_versions",
    "get_version",
    "list_decisions",
    "record_decision",
]
