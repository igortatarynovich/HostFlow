"""G-4.5 — outbound dispatch working-hours gate.

Contract under test: ``_maybe_defer_outbound_for_working_hours`` in
``backend/app/api/v1/communications/_helpers/dispatch.py``. The helper
is the single source of truth for "should this queued outbound message
wait until morning?" — it's wired into ``dispatch_queued_messages``
before any channel adapter runs.

Gate policy (G-4.5):
  * Default (no tenant setting): return None, behaviour unchanged.
  * ``tenant.settings.communications.defer_outside_working_hours =
    True``:
      - Thread has assignee + assignee has ``working_hours_v1`` +
        ``now`` is outside → return deferral target, mutate
        ``msg.payload.dispatch`` with
        ``{status: deferred_working_hours, next_retry_at,
        deferred_until, deferral_reason, deferred_count, …}``.
        attempt_count untouched (a deferral is not a failed retry —
        lumping them together would eventually mark healthy messages
        ``failed`` after 5 deferrals).
      - No assignee → skip (can't pick whose hours to respect).
      - Assignee has no schedule → skip (mirrors reminder-shift
        policy, so operators don't get different behaviour per
        per-user schedule configuration).
      - ``now`` already inside window → skip.

Tests hit the service function directly (no HTTP), same pattern as
``test_reminder_working_hours_shift.py`` so they're independent of
the dispatch-queued request schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Tuple

import pytest
from sqlalchemy import select

from backend.app.api.v1.communications._helpers.dispatch import (
    _maybe_defer_outbound_for_working_hours,
    _tenant_defers_outbound_outside_working_hours,
)
from backend.app.models.communication import (
    CommunicationMessage,
    CommunicationThread,
)
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.services.working_hours_presets import preset_to_working_hours_v1


pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _enable_defer_on_tenant(db, tenant_id: str) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    assert tenant is not None
    settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    comms = dict(settings.get("communications") or {})
    comms["defer_outside_working_hours"] = True
    settings["communications"] = comms
    tenant.settings = settings
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def _clear_defer_on_tenant(db, tenant_id: str) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    assert tenant is not None
    settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    comms = dict(settings.get("communications") or {})
    comms.pop("defer_outside_working_hours", None)
    if comms:
        settings["communications"] = comms
    else:
        settings.pop("communications", None)
    tenant.settings = settings
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def _set_user_working_hours(db, user_id: str, preset: str = "weekdays_9_17") -> None:
    user = await db.get(User, user_id)
    assert user is not None
    extra = dict(user.extra or {}) if isinstance(user.extra, dict) else {}
    sched = preset_to_working_hours_v1(preset)
    assert sched is not None
    extra["working_hours_v1"] = sched
    user.extra = extra
    await db.commit()


async def _clear_user_working_hours(db, user_id: str) -> None:
    user = await db.get(User, user_id)
    assert user is not None
    extra = dict(user.extra or {}) if isinstance(user.extra, dict) else {}
    extra.pop("working_hours_v1", None)
    user.extra = extra
    await db.commit()


async def _first_user_id(db, tenant_id: str) -> str:
    uid = await db.scalar(select(User.id).where(User.tenant_id == tenant_id).limit(1))
    assert uid is not None
    return uid


async def _create_thread_and_message(
    db,
    *,
    tenant_id: str,
    assignee_id: str | None,
) -> Tuple[CommunicationThread, CommunicationMessage]:
    thread = CommunicationThread(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        channel="mock",
        status="open",
        assignee_id=assignee_id,
    )
    db.add(thread)
    await db.flush()
    msg = CommunicationMessage(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        thread_id=thread.id,
        channel="mock",
        message_type="text",
        direction="outbound",
        body_text="Hello",
        delivery_status="queued",
        is_internal_note=False,
        payload={"dispatch": {"attempt_count": 0}},
    )
    db.add(msg)
    await db.commit()
    await db.refresh(thread)
    await db.refresh(msg)
    return thread, msg


def _next_monday_01_utc() -> datetime:
    """Compute next Monday at 01:00 UTC — outside Warsaw 9-17 either way."""
    now = datetime.now(timezone.utc)
    days_ahead = (7 - now.weekday()) % 7 or 7
    days_ahead += 7
    target = now + timedelta(days=days_ahead)
    return target.replace(hour=1, minute=0, second=0, microsecond=0)


def _same_day_12_warsaw(anchor_utc: datetime) -> datetime:
    from zoneinfo import ZoneInfo

    local = anchor_utc.astimezone(ZoneInfo("Europe/Warsaw")).replace(
        hour=12, minute=0, second=0, microsecond=0
    )
    return local.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Flag reader
# ---------------------------------------------------------------------------


async def test_tenant_flag_reader_default_off(db, tenant_id: str) -> None:
    """No ``communications.defer_outside_working_hours`` setting → False.
    Pre-existing tenants must see zero behavioural change."""
    await _clear_defer_on_tenant(db, tenant_id)
    tenant = await db.get(Tenant, tenant_id)
    assert _tenant_defers_outbound_outside_working_hours(tenant) is False


async def test_tenant_flag_reader_opt_in_on(db, tenant_id: str) -> None:
    tenant = await _enable_defer_on_tenant(db, tenant_id)
    assert _tenant_defers_outbound_outside_working_hours(tenant) is True


# ---------------------------------------------------------------------------
# Gate helper
# ---------------------------------------------------------------------------


async def test_no_defer_when_flag_off(db, tenant_id: str) -> None:
    """Default tenant config: helper is no-op even when the assignee has
    hours and ``now`` is outside them."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    tenant = await _clear_defer_on_tenant(db, tenant_id)
    thread, msg = await _create_thread_and_message(
        db, tenant_id=tenant_id, assignee_id=user_id
    )
    outside = _next_monday_01_utc()

    result = await _maybe_defer_outbound_for_working_hours(
        db, tenant=tenant, thread=thread, msg=msg, now=outside
    )
    assert result is None
    # Nothing stashed either.
    assert "deferred_until" not in (msg.payload or {}).get("dispatch", {})


async def test_no_defer_when_thread_has_no_assignee(db, tenant_id: str) -> None:
    """Can't pick whose hours to respect → skip silently."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    tenant = await _enable_defer_on_tenant(db, tenant_id)
    thread, msg = await _create_thread_and_message(
        db, tenant_id=tenant_id, assignee_id=None
    )
    outside = _next_monday_01_utc()

    result = await _maybe_defer_outbound_for_working_hours(
        db, tenant=tenant, thread=thread, msg=msg, now=outside
    )
    assert result is None


async def test_no_defer_when_assignee_has_no_schedule(db, tenant_id: str) -> None:
    """Mirrors reminder-shift policy: no schedule means the operator
    never configured their hours → treat as "anytime is fine"."""
    user_id = await _first_user_id(db, tenant_id)
    await _clear_user_working_hours(db, user_id)
    tenant = await _enable_defer_on_tenant(db, tenant_id)
    thread, msg = await _create_thread_and_message(
        db, tenant_id=tenant_id, assignee_id=user_id
    )
    outside = _next_monday_01_utc()

    result = await _maybe_defer_outbound_for_working_hours(
        db, tenant=tenant, thread=thread, msg=msg, now=outside
    )
    assert result is None


async def test_no_defer_when_inside_window(db, tenant_id: str) -> None:
    """Assignee scheduled 9-17 + now=12:00 Warsaw → send through."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    tenant = await _enable_defer_on_tenant(db, tenant_id)
    thread, msg = await _create_thread_and_message(
        db, tenant_id=tenant_id, assignee_id=user_id
    )
    inside = _same_day_12_warsaw(_next_monday_01_utc())

    result = await _maybe_defer_outbound_for_working_hours(
        db, tenant=tenant, thread=thread, msg=msg, now=inside
    )
    assert result is None


async def test_defers_when_outside_and_stashes_diag(db, tenant_id: str) -> None:
    """Outside window + flag on + schedule present → defer.

    Helper MUST stash diagnostic block on payload so the generic
    ``dispatch.next_retry_at`` loop naturally picks the message up at
    the window start on a later scheduler tick, and so G-10
    explainability can show operators *why* the send was delayed.
    """
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    tenant = await _enable_defer_on_tenant(db, tenant_id)
    thread, msg = await _create_thread_and_message(
        db, tenant_id=tenant_id, assignee_id=user_id
    )
    outside = _next_monday_01_utc()

    result = await _maybe_defer_outbound_for_working_hours(
        db, tenant=tenant, thread=thread, msg=msg, now=outside
    )
    assert result is not None
    assert result > outside, "deferral target must be strictly in the future"

    dispatch: Dict = (msg.payload or {}).get("dispatch") or {}
    assert dispatch["status"] == "deferred_working_hours"
    assert dispatch["deferral_reason"] == "outside_assignee_working_hours"
    assert dispatch["next_retry_at"] == result.isoformat()
    assert dispatch["deferred_until"] == result.isoformat()
    assert dispatch["last_deferred_at"] == outside.isoformat()
    assert dispatch["deferred_count"] == 1
    # attempt_count MUST be untouched — a deferral is not a retry, and
    # conflating them would hit max_attempts after 5 deferrals and flag
    # healthy messages as ``failed``.
    assert dispatch.get("attempt_count", 0) == 0
    # Message stays queued.
    assert msg.delivery_status == "queued"


async def test_defer_increments_counter_on_repeat(db, tenant_id: str) -> None:
    """Calling the helper twice in a row (e.g. scheduler ticked too
    early after the previous deferral wrote ``next_retry_at``) bumps
    ``deferred_count`` and leaves ``attempt_count`` at zero."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    tenant = await _enable_defer_on_tenant(db, tenant_id)
    thread, msg = await _create_thread_and_message(
        db, tenant_id=tenant_id, assignee_id=user_id
    )
    outside = _next_monday_01_utc()

    first = await _maybe_defer_outbound_for_working_hours(
        db, tenant=tenant, thread=thread, msg=msg, now=outside
    )
    assert first is not None
    second_outside = outside + timedelta(minutes=5)
    second = await _maybe_defer_outbound_for_working_hours(
        db, tenant=tenant, thread=thread, msg=msg, now=second_outside
    )
    assert second is not None

    dispatch: Dict = (msg.payload or {}).get("dispatch") or {}
    assert dispatch["deferred_count"] == 2
    assert dispatch.get("attempt_count", 0) == 0
