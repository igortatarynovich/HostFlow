# Canonical Campaign registries — loaded from shared/campaign_registries.json (ADR-024 §3A).
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Final


def _registry_path_candidates() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    return (
        here.parents[3] / "shared" / "campaign_registries.json",
        here.parents[2] / "shared" / "campaign_registries.json",
        Path("/shared/campaign_registries.json"),
        Path("/opt/HostFlow/shared/campaign_registries.json"),
    )


def resolve_campaign_registries_path() -> Path:
    for candidate in _registry_path_candidates():
        if candidate.is_file():
            return candidate
    tried = ", ".join(str(p) for p in _registry_path_candidates())
    raise FileNotFoundError(f"shared/campaign_registries.json not found (tried: {tried})")


@lru_cache(maxsize=1)
def load_campaign_registries() -> dict[str, Any]:
    return json.loads(resolve_campaign_registries_path().read_text(encoding="utf-8"))


def goal_type_codes() -> frozenset[str]:
    return frozenset(str(row["code"]) for row in load_campaign_registries()["goal_types"])


def primary_kpi_codes() -> frozenset[str]:
    return frozenset(str(row["code"]) for row in load_campaign_registries()["primary_kpis"])


def goal_kpi_pairs() -> frozenset[tuple[str, str]]:
    return frozenset(
        (str(row["goal_type"]), str(row["primary_kpi"]))
        for row in load_campaign_registries()["goal_kpi_pairs"]
    )


def is_valid_goal_kpi_pair(goal_type: str, primary_kpi: str) -> bool:
    return (str(goal_type).strip(), str(primary_kpi).strip()) in goal_kpi_pairs()


def promotion_targets_by_type() -> dict[str, dict[str, Any]]:
    return {
        str(row["target_type"]): dict(row)
        for row in load_campaign_registries()["promotion_targets"]
    }


def resolve_promotion_target(target_type: str) -> dict[str, Any] | None:
    return promotion_targets_by_type().get(str(target_type).strip())


def canonical_target_module(target_type: str) -> str | None:
    row = resolve_promotion_target(target_type)
    if not row:
        return None
    return str(row["target_module"])


def allowed_route_intents_for_target(target_type: str) -> frozenset[str]:
    row = resolve_promotion_target(target_type)
    if not row:
        return frozenset()
    return frozenset(str(x) for x in (row.get("allowed_route_intents") or []))


GOAL_TYPE_CODES: Final[frozenset[str]] = goal_type_codes()
PRIMARY_KPI_CODES: Final[frozenset[str]] = primary_kpi_codes()
