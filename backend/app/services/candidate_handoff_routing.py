"""Canonical routing: who receives the candidate after «Готов к передаче».

Product source: handoff-contract + HostFlow multi-tenant model (agency / direct employer / client).
This module is pure logic (no DB) so API and workers can share one resolver.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CandidateHandoffRouteKind(str, Enum):
    """Where recruitment should send the dossier next."""

    hr_module = "hr_module"
    client_hostflow = "client_hostflow"
    client_portal_link = "client_portal_link"
    unavailable = "unavailable"


@dataclass(frozen=True)
class CandidateHandoffRouteResolution:
    kind: CandidateHandoffRouteKind
    """Human-readable reason for logs / UI (RU ok)."""
    reason: str = ""


def resolve_candidate_handoff_route(
    *,
    acting_company_business_type: str | None,
    agency_recruiting_for_client: bool,
    client_has_hostflow_account: bool,
    hr_module_enabled_for_receiver: bool,
    client_portal_or_link_available: bool,
) -> CandidateHandoffRouteResolution:
    """Decide the next hop after ``ready_for_handoff`` / ``ready_for_hr``.

    Parameters are intentionally coarse booleans supplied by the caller from
    tenant/company/modules + tenant_links (see ``handoff-contract.md``).

    * ``acting_company_business_type`` — normalized ``company_type`` / business profile
      (e.g. ``agency``, ``direct_employer``, ``services``).
    * ``agency_recruiting_for_client`` — vacancy / application is for a client company
      (агентство ведёт подбор для клиента).
    """
    bt = (acting_company_business_type or "").strip().lower()

    if not agency_recruiting_for_client and bt in ("direct_employer", "employer", "services", ""):
        if hr_module_enabled_for_receiver:
            return CandidateHandoffRouteResolution(
                CandidateHandoffRouteKind.hr_module,
                reason="Прямой работодатель / сервис: передача в HR-модуль",
            )
        return CandidateHandoffRouteResolution(
            CandidateHandoffRouteKind.unavailable,
            reason="HR-модуль не подключён: передача в кадры недоступна",
        )

    if agency_recruiting_for_client:
        if client_has_hostflow_account and hr_module_enabled_for_receiver:
            return CandidateHandoffRouteResolution(
                CandidateHandoffRouteKind.client_hostflow,
                reason="Клиент с HostFlow: контур клиента (Recruitment/HR)",
            )
        if client_has_hostflow_account:
            return CandidateHandoffRouteResolution(
                CandidateHandoffRouteKind.client_hostflow,
                reason="Клиент с HostFlow: клиентский контур / портал",
            )
        if client_portal_or_link_available:
            return CandidateHandoffRouteResolution(
                CandidateHandoffRouteKind.client_portal_link,
                reason="У клиента нет аккаунта: Client Portal / handoff link",
            )
        return CandidateHandoffRouteResolution(
            CandidateHandoffRouteKind.unavailable,
            reason="Нет канала передачи клиенту",
        )

    if bt == "agency" and not agency_recruiting_for_client:
        if hr_module_enabled_for_receiver:
            return CandidateHandoffRouteResolution(
                CandidateHandoffRouteKind.hr_module,
                reason="Агентство как работодатель: внутренний HR",
            )
        return CandidateHandoffRouteResolution(
            CandidateHandoffRouteKind.unavailable,
            reason="HR-модуль не подключён",
        )

    return CandidateHandoffRouteResolution(
        CandidateHandoffRouteKind.unavailable,
        reason="Недостаточно данных для маршрута передачи",
    )


__all__ = [
    "CandidateHandoffRouteKind",
    "CandidateHandoffRouteResolution",
    "resolve_candidate_handoff_route",
]
