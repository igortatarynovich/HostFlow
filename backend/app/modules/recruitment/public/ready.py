"""Recruitment Ready / Transfer process contract.

Public chain (ADR-042):

  public context / policy selection
    → evaluate_ready_transfer / TransferPolicyResolver.resolve
    → Recruitment-owned composition resolver (private composition)
    → applicable evaluators → canonical Ready verdict
    → transfer_allowed (derived)

Neighbours must not pass internal capability lists. Stable selector:
``ready_composition_id`` (e.g. ``empty`` / ``driver``). Composition
contents stay private.

Eager imports of package readiness / transfer resolver are forbidden here —
cold-process import of this module must succeed without ``process_engine``.
"""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.reference.recruitment_ready_policy import (
    COMPOSITION_DRIVER,
    COMPOSITION_EMPTY,
    DECISION_ALLOWED,
    DECISION_BLOCKED,
    DECISION_MISSING,
    DECISION_UNSUPPORTED,
    READY_COMPOSITION_ID_KEY,
    resolve_ready_composition_v1,
)

__all__ = [
    "COMPOSITION_DRIVER",
    "COMPOSITION_EMPTY",
    "DECISION_ALLOWED",
    "DECISION_BLOCKED",
    "DECISION_MISSING",
    "DECISION_UNSUPPORTED",
    "READY_COMPOSITION_ID_KEY",
    "TransferPolicyResolver",
    "assert_recruitment_package_ready_for_handoff",
    "evaluate_ready_transfer",
    "resolve_ready_composition_v1",
    "resolve_tenant_transfer_policy_summary",
]


def __getattr__(name: str) -> Any:
    if name == "TransferPolicyResolver":
        from backend.app.services.transfer_policy_resolver import TransferPolicyResolver

        return TransferPolicyResolver
    if name == "assert_recruitment_package_ready_for_handoff":
        from backend.app.services.recruitment_package_readiness import (
            assert_recruitment_package_ready_for_handoff,
        )

        return assert_recruitment_package_ready_for_handoff
    if name == "resolve_tenant_transfer_policy_summary":
        from backend.app.services.transfer_policy_resolver import (
            resolve_tenant_transfer_policy_summary,
        )

        return resolve_tenant_transfer_policy_summary
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def evaluate_ready_transfer(
    db: Any,
    *,
    tenant_id: str,
    candidate_id: str,
    ready_context: Mapping[str, Any] | None = None,
    target_stage: str | None = None,
    require_destination: bool = False,
) -> dict[str, Any]:
    """Public Ready process entry: selector/context → canonical verdict.

    Does not accept private capability lists. Pass ``ready_composition_id``
    in ``ready_context`` (e.g. ``empty``) for composition selection.
    """
    from backend.app.services.transfer_policy_resolver import TransferPolicyResolver

    return await TransferPolicyResolver.resolve(
        db,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        target_stage=target_stage,
        require_destination=require_destination,
        ready_context=ready_context,
    )
