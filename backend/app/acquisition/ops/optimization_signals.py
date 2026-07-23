"""Stage 5 PR-1 — Flight optimization signals (read-only).

Compose Stage 4 runtime snapshot + Live Intake Monitor counters + allowlisted
Timeline events into typed recommendations. No auto Pause/Resume writes.

Canon: docs/specs/tasks/acquisition-stage-5-optimization.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RecommendedAction = Literal["none", "suggest_pause"]


@dataclass(frozen=True)
class OptimizationSignal:
    code: str
    severity: Literal["info", "warn", "critical"]
    message: str


@dataclass(frozen=True)
class FlightOptimizationSnapshot:
    campaign_id: str
    flight_id: str
    signals: tuple[OptimizationSignal, ...]
    recommended_action: RecommendedAction
    reason_codes: tuple[str, ...]


# Implementation lands in follow-up commits on this branch (thresholds + HTTP).
