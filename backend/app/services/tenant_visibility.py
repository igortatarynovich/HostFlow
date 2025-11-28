from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class TenantVisibility:
    tenant_id: str
    shared_vacancy_ids: Set[str] = field(default_factory=set)
    shared_company_ids: Set[str] = field(default_factory=set)

    def clone(self) -> "TenantVisibility":
        return TenantVisibility(
            tenant_id=self.tenant_id,
            shared_vacancy_ids=set(self.shared_vacancy_ids),
            shared_company_ids=set(self.shared_company_ids),
        )

    def include_vacancies(self, vacancy_ids: Iterable[str]) -> None:
        for vid in vacancy_ids:
            if vid:
                self.shared_vacancy_ids.add(str(vid))

    def include_companies(self, company_ids: Iterable[str]) -> None:
        for cid in company_ids:
            if cid:
                self.shared_company_ids.add(str(cid))


def get_tenant_visibility(db: AsyncSession, tenant_id: str | None = None) -> TenantVisibility:
    """Return TenantVisibility stored on the session, or a default instance."""
    info = getattr(db, "info", {})
    cached = info.get("tenant_visibility") if isinstance(info, dict) else None
    if isinstance(cached, TenantVisibility):
        if tenant_id and cached.tenant_id != tenant_id:
            return TenantVisibility(tenant_id=tenant_id)
        return cached

    fallback_id = tenant_id or str(info.get("tenant_id") or "")
    if not fallback_id:
        fallback_id = "unknown"
    visibility = TenantVisibility(tenant_id=fallback_id)
    if isinstance(info, dict):
        info["tenant_visibility"] = visibility
    return visibility
