"""Contract: client handoff checkbox must persist false for write-capable users."""

from __future__ import annotations

from pathlib import Path


def test_update_tenant_link_allows_trust_write_not_only_admin() -> None:
    source = Path("backend/app/api/v1/tenants/router.py").read_text(encoding="utf-8")
    start = source.index("async def update_tenant_link")
    decorator = source[source.rfind("@router.patch", 0, start) : start]
    assert "require_trust_write()" in decorator
    assert "require_trust_admin()" not in decorator


def test_update_tenant_link_flags_features_json_for_false() -> None:
    source = Path("backend/app/api/v1/tenants/router.py").read_text(encoding="utf-8")
    start = source.index("async def update_tenant_link")
    chunk = source[start : start + 3200]
    assert 'features["handoff_enabled"] = bool(updates["handoff_enabled"])' in chunk
    assert 'flag_modified(link, "features_json")' in chunk
