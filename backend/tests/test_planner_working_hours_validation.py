"""G-4 stage 3 — planner POST/PATCH server-side working-hours
validation.

Contract under test:
  * Tenant setting `planner.enforce_working_hours` defaults OFF; when
    OFF the helper is a no-op.
  * When ON: scheduling a planner event for a time outside the
    assignee's `working_hours_v1` schedule raises HTTP 422 with
    `code=outside_working_hours` and the offending field in `field`.
  * When ON: passing `allow_outside_hours=True` overrides the check
    (operator-acknowledged after-hours interview).
  * When ON: end_at is also validated, not just start_at — e.g. a
    meeting starting at 16:30 and running to 18:30 must be flagged.
  * No assignee → no validation (org-wide / unassigned slot).
  * Assignee without a schedule → no validation (don't punish operators
    for someone else's missing config).

Tests exercise the helper directly. The HTTP wrapping is trivial — the
helper is the unit where the contract lives.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.api.v1.communications.routes.planner import (
    _assert_within_working_hours_or_overridden,
)
from backend.app.models.tenant import Tenant
from backend.app.models.user import User
from backend.app.services.working_hours_presets import preset_to_working_hours_v1


pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers (mirror the test_reminder_working_hours_shift conventions).
# ---------------------------------------------------------------------------


async def _enable_planner_enforcement(db, tenant_id: str) -> None:
    tenant = await db.get(Tenant, tenant_id)
    assert tenant is not None
    settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    planner = dict(settings.get("planner") or {})
    planner["enforce_working_hours"] = True
    settings["planner"] = planner
    tenant.settings = settings
    await db.commit()


async def _clear_planner_enforcement(db, tenant_id: str) -> None:
    tenant = await db.get(Tenant, tenant_id)
    assert tenant is not None
    settings = dict(tenant.settings or {}) if isinstance(tenant.settings, dict) else {}
    planner = dict(settings.get("planner") or {})
    planner.pop("enforce_working_hours", None)
    if planner:
        settings["planner"] = planner
    else:
        settings.pop("planner", None)
    tenant.settings = settings
    await db.commit()


async def _set_user_working_hours(db, user_id: str) -> None:
    user = await db.get(User, user_id)
    assert user is not None
    extra = dict(user.extra or {}) if isinstance(user.extra, dict) else {}
    sched = preset_to_working_hours_v1("weekdays_9_17")
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


def _next_target_monday() -> datetime:
    """Same convention as test_reminder_working_hours_shift — anchor on
    a future Monday so the validation tests are time-stable."""
    now = datetime.now(timezone.utc)
    days_ahead = (7 - now.weekday()) % 7 or 7
    days_ahead += 7
    target = now + timedelta(days=days_ahead)
    return target.replace(hour=0, minute=0, second=0, microsecond=0)


def _warsaw_at(monday_utc_midnight: datetime, hour: int, minute: int = 0) -> datetime:
    """Return UTC instant for `hour:minute` Warsaw on the same Monday.
    Avoids hard-coding UTC offsets which differ between CET/CEST."""
    local = monday_utc_midnight.astimezone(ZoneInfo("Europe/Warsaw")).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return local.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_no_enforcement_when_setting_off(db, tenant_id: str) -> None:
    """Default tenant config: helper must not raise even for clearly
    out-of-hours times. Existing tenants don't see behaviour changes."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _clear_planner_enforcement(db, tenant_id)

    monday = _next_target_monday()
    start = _warsaw_at(monday, 3)
    end = _warsaw_at(monday, 4)
    # Should not raise.
    await _assert_within_working_hours_or_overridden(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_at=start,
        end_at=end,
        allow_outside_hours=False,
    )


async def test_enforce_blocks_start_outside_hours(db, tenant_id: str) -> None:
    """Setting on + assignee schedule + start_at at 03:00 local → 422
    with code=outside_working_hours, field=start_at."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _enable_planner_enforcement(db, tenant_id)

    monday = _next_target_monday()
    start = _warsaw_at(monday, 3)
    end = _warsaw_at(monday, 4)
    with pytest.raises(HTTPException) as ei:
        await _assert_within_working_hours_or_overridden(
            db,
            tenant_id=tenant_id,
            assignee_id=user_id,
            start_at=start,
            end_at=end,
            allow_outside_hours=False,
        )
    assert ei.value.status_code == 422
    detail = ei.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "outside_working_hours"
    assert detail["field"] == "start_at"


async def test_enforce_blocks_end_outside_hours_when_start_inside(
    db, tenant_id: str
) -> None:
    """Meeting starts at 16:30 (inside) but ends at 18:30 (outside) →
    422 with field=end_at. Catches the partially-out-of-hours case."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _enable_planner_enforcement(db, tenant_id)

    monday = _next_target_monday()
    start = _warsaw_at(monday, 16, 30)
    end = _warsaw_at(monday, 18, 30)
    with pytest.raises(HTTPException) as ei:
        await _assert_within_working_hours_or_overridden(
            db,
            tenant_id=tenant_id,
            assignee_id=user_id,
            start_at=start,
            end_at=end,
            allow_outside_hours=False,
        )
    detail = ei.value.detail
    assert detail["field"] == "end_at"


async def test_enforce_passes_when_start_and_end_inside(db, tenant_id: str) -> None:
    """Both endpoints in window → no raise."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _enable_planner_enforcement(db, tenant_id)

    monday = _next_target_monday()
    start = _warsaw_at(monday, 10)
    end = _warsaw_at(monday, 12)
    await _assert_within_working_hours_or_overridden(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_at=start,
        end_at=end,
        allow_outside_hours=False,
    )


async def test_allow_outside_hours_overrides_check(db, tenant_id: str) -> None:
    """Operator passes the explicit override → no raise even when both
    times are outside hours. The override is the deliberate-decision
    escape hatch (after-hours interview, weekend shift cover)."""
    user_id = await _first_user_id(db, tenant_id)
    await _set_user_working_hours(db, user_id)
    await _enable_planner_enforcement(db, tenant_id)

    monday = _next_target_monday()
    # Saturday — entire day outside hours.
    saturday_start = monday + timedelta(days=5)
    start = _warsaw_at(saturday_start, 10)
    end = _warsaw_at(saturday_start, 11)
    await _assert_within_working_hours_or_overridden(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_at=start,
        end_at=end,
        allow_outside_hours=True,
    )


async def test_no_assignee_skips_validation(db, tenant_id: str) -> None:
    """Org-wide planner event (no assignee) — helper is a no-op."""
    await _enable_planner_enforcement(db, tenant_id)
    monday = _next_target_monday()
    # Should not raise even though it's 03:00 local.
    await _assert_within_working_hours_or_overridden(
        db,
        tenant_id=tenant_id,
        assignee_id=None,
        start_at=_warsaw_at(monday, 3),
        end_at=_warsaw_at(monday, 4),
        allow_outside_hours=False,
    )


async def test_assignee_without_schedule_skips_validation(
    db, tenant_id: str
) -> None:
    """Assignee never configured working hours → no validation. We
    don't want operators getting 422 because someone on the team
    didn't set their hours yet."""
    user_id = await _first_user_id(db, tenant_id)
    await _clear_user_working_hours(db, user_id)
    await _enable_planner_enforcement(db, tenant_id)

    monday = _next_target_monday()
    await _assert_within_working_hours_or_overridden(
        db,
        tenant_id=tenant_id,
        assignee_id=user_id,
        start_at=_warsaw_at(monday, 3),
        end_at=_warsaw_at(monday, 4),
        allow_outside_hours=False,
    )
