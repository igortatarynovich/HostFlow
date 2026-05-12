"""AsyncSession subclass: fail closed on Postgres when tenant RLS context is missing."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class TenantEnforcingAsyncSession(AsyncSession):
    """Enforces tenant_rls_enforcement + rls_tenant_bound at execute/stream boundary (Postgres only)."""

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.info.setdefault("tenant_rls_enforcement", False)

    def _tenant_guard_allow(self) -> bool:
        if not self.info.get("tenant_rls_enforcement"):
            return True
        if self.info.get("_binding_tenant_context"):
            return True
        if self.info.get("rls_tenant_bound"):
            return True
        return False

    def _dialect_name(self) -> str | None:
        try:
            bind = self.get_bind()
            dialect = getattr(bind, "dialect", None)
            return str(getattr(dialect, "name", "") or "") or None
        except Exception:
            return None

    def _assert_tenant_rls(self) -> None:
        if self._tenant_guard_allow():
            return
        if (self._dialect_name() or "") != "postgresql":
            return
        from backend.app.security.canonical_emit import emit_security_event_v1
        from backend.app.security.event_taxonomy import EVENT_RLS_TENANT_CONTEXT_EXECUTE_DENIED

        emit_security_event_v1(
            event_type=EVENT_RLS_TENANT_CONTEXT_EXECUTE_DENIED,
            result="denied",
            severity="high",
            source="db:tenant_enforcing_async_session",
            tenant_id=str(self.info.get("tenant_id") or "") or None,
            access_kind=str(self.info.get("security_access_kind") or "") or None,
            extra={"dialect": self._dialect_name()},
            extra_allowlist=frozenset({"dialect"}),
        )
        raise RuntimeError(
            "HostFlow: enforced DB session attempted SQL without bound RLS tenant context "
            "(use bind_tenant_context_to_session or tenant_rls_enforcement=False).",
        )

    async def execute(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
        self._assert_tenant_rls()
        return await super().execute(statement, *args, **kwargs)

    async def stream(self, statement, *args, **kwargs):  # type: ignore[no-untyped-def]
        self._assert_tenant_rls()
        return await super().stream(statement, *args, **kwargs)
