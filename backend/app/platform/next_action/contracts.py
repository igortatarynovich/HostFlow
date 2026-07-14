"""Platform Next Action contract types (PI-1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class NextActionCandidate:
    gate_id: str
    label_key: str
    handler_ref: str


@dataclass(frozen=True)
class ReachabilityContext:
    """User/session context for PI-1A evaluation at publish time."""

    setup_ready: bool
    tenant_status: str | None = None
    is_superadmin: bool = False


@dataclass(frozen=True)
class NextActionEvaluation:
    reachable: bool
    complete: bool
    reason_code: str | None = None


class ReachabilityEvaluatorProtocol(Protocol):
    def evaluate(self, candidate: NextActionCandidate, ctx: ReachabilityContext) -> NextActionEvaluation: ...


class CompletenessEvaluatorProtocol(Protocol):
    def evaluate(self, candidate: NextActionCandidate, ctx: ReachabilityContext) -> NextActionEvaluation: ...
