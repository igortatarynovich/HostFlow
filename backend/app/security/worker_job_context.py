"""SSOT §0b helpers — required fields for background / ARQ jobs."""

from __future__ import annotations

from uuid import UUID


class JobTenantRequiredError(ValueError):
    """Raised when a tenant-scoped job is missing a valid ``tenant_id`` (fail before DB)."""


def parse_required_job_tenant_id(raw: str | None, *, job_name: str = "job") -> UUID:
    """Return a UUID tenant id or raise :class:`JobTenantRequiredError`.

    Workers must call this before opening a tenant-bound session so a missing /
    malformed ``tenant_id`` fails closed without querying tenant tables.
    """
    s = (raw or "").strip()
    if not s:
        raise JobTenantRequiredError(f"{job_name} requires tenant_id")
    try:
        return UUID(s)
    except Exception as exc:
        raise JobTenantRequiredError(f"{job_name} tenant_id must be a UUID, got {raw!r}") from exc


__all__ = [
    "JobTenantRequiredError",
    "parse_required_job_tenant_id",
]
