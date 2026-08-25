"""Registry validation for Campaign Goal / KPI / Target (ADR-024 Stage 3A)."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.constants.campaign_registries import (
    allowed_route_intents_for_target,
    canonical_target_module,
    is_valid_goal_kpi_pair,
    resolve_promotion_target,
)


class CampaignValidationError(ValueError):
    def __init__(self, detail: str, *, status_code: int = 422):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class ValidatedTarget:
    target_type: str
    target_id: str
    target_module: str
    route_intent: str
    role: str
    sort_order: int


def validate_goal_kpi_pair(goal_type: str, primary_kpi: str) -> tuple[str, str]:
    gt = str(goal_type or "").strip().lower()
    pk = str(primary_kpi or "").strip().lower()
    if not gt or not pk:
        raise CampaignValidationError("goal_type and primary_kpi are required")
    if not is_valid_goal_kpi_pair(gt, pk):
        raise CampaignValidationError(
            f"Invalid goal_type/primary_kpi pair: {gt!r} + {pk!r}",
        )
    return gt, pk


def validate_promotion_target(
    *,
    target_type: str,
    target_id: str,
    route_intent: str,
    role: str = "primary",
    sort_order: int = 0,
    client_target_module: str | None = None,
) -> ValidatedTarget:
    """
    Validate target against promotion registry.

    ``target_module`` is always taken from the registry. If the client sends a
    module, it must match the canonical value (defense in depth) — otherwise 422.
    """
    tt = str(target_type or "").strip().lower()
    tid = str(target_id or "").strip()
    ri = str(route_intent or "").strip().lower()
    role_n = str(role or "primary").strip().lower() or "primary"
    if role_n not in {"primary", "context"}:
        raise CampaignValidationError("role must be 'primary' or 'context'")
    if not tt or not tid:
        raise CampaignValidationError("target_type and target_id are required")
    if not ri:
        raise CampaignValidationError("route_intent is required")

    row = resolve_promotion_target(tt)
    if row is None:
        raise CampaignValidationError(f"Unknown promotion target_type: {tt!r}")

    module = canonical_target_module(tt)
    assert module is not None
    if client_target_module is not None and str(client_target_module).strip():
        client_mod = str(client_target_module).strip().lower()
        if client_mod != module:
            raise CampaignValidationError(
                f"target_module must be canonical {module!r} for target_type {tt!r} "
                f"(got {client_mod!r})",
            )

    allowed = allowed_route_intents_for_target(tt)
    if ri not in allowed:
        raise CampaignValidationError(
            f"route_intent {ri!r} is not allowed for target_type {tt!r}",
        )

    return ValidatedTarget(
        target_type=tt,
        target_id=tid,
        target_module=module,
        route_intent=ri,
        role=role_n,
        sort_order=int(sort_order or 0),
    )
