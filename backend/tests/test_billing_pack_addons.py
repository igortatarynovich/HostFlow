"""billing_pack_addons: merge + read pack add-on counters."""

from __future__ import annotations

from backend.app.services.billing_pack_addons import (
    LEAD_FORMS_ACTIVE_CAP,
    MONTHLY_LEADS_CAP,
    merge_pack_addon_into_settings,
    pack_addon_int,
)


def test_merge_and_read_pack_addon() -> None:
    st = merge_pack_addon_into_settings({}, MONTHLY_LEADS_CAP, 500)
    st = merge_pack_addon_into_settings(st, MONTHLY_LEADS_CAP, 200)
    assert pack_addon_int(st, MONTHLY_LEADS_CAP) == 700


def test_merge_lead_forms_pack_addon() -> None:
    st = merge_pack_addon_into_settings({}, LEAD_FORMS_ACTIVE_CAP, 5)
    assert pack_addon_int(st, LEAD_FORMS_ACTIVE_CAP) == 5
