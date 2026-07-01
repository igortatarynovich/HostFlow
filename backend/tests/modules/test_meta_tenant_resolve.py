"""Unit tests for superadmin → operational tenant Meta remap defaults."""

from __future__ import annotations

import uuid

import pytest

from backend.app.auth.deps import UserCtx
from backend.app.constants.hostflow_canonical_tenants import FOCUS_PERSONNEL_TENANT_ID
from backend.app.db.deps import PUBLIC_LEGACY_DEFAULT_TENANT_UUID
from backend.app.modules.leads import meta_tenant_resolve as mtr

BOOT = str(PUBLIC_LEGACY_DEFAULT_TENANT_UUID)
OTHER = str(uuid.uuid4())


def _ctx(role: str, tenant_id: str = BOOT) -> UserCtx:
    return UserCtx(
        sub="u1",
        email="t@t",
        role=role,
        tenant_id=tenant_id,
        supervisor_id=None,
        raw={},
    )


def test_superadmin_bootstrap_uses_canonical_focus_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mtr.settings, "meta_leads_operational_tenant_id", None)
    assert mtr.resolve_meta_leads_effective_tenant_id(_ctx("superadmin"), BOOT) == FOCUS_PERSONNEL_TENANT_ID


@pytest.mark.parametrize("off_val", ["off", "OFF", "disable", "none", "false", "0"])
def test_disable_sentinels_no_remap(monkeypatch: pytest.MonkeyPatch, off_val: str) -> None:
    monkeypatch.setattr(mtr.settings, "meta_leads_operational_tenant_id", off_val)
    assert mtr.resolve_meta_leads_effective_tenant_id(_ctx("superadmin"), BOOT) == BOOT


def test_explicit_uuid_override(monkeypatch: pytest.MonkeyPatch) -> None:
    custom = str(uuid.uuid4())
    monkeypatch.setattr(mtr.settings, "meta_leads_operational_tenant_id", custom)
    assert mtr.resolve_meta_leads_effective_tenant_id(_ctx("superadmin"), BOOT) == custom


def test_administrator_never_remaps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mtr.settings, "meta_leads_operational_tenant_id", None)
    assert mtr.resolve_meta_leads_effective_tenant_id(_ctx("administrator"), BOOT) == BOOT


def test_superadmin_non_bootstrap_untouched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mtr.settings, "meta_leads_operational_tenant_id", None)
    assert mtr.resolve_meta_leads_effective_tenant_id(_ctx("superadmin"), OTHER) == OTHER
