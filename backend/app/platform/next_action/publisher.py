"""Platform Next Action publisher — PI-1 enforce-at-publish."""

from __future__ import annotations

from typing import Mapping, Sequence, TypeVar

from backend.app.platform.next_action.completeness import CompletenessEvaluator
from backend.app.platform.next_action.contracts import (
    NextActionCandidate,
    ReachabilityContext,
    ReachabilityEvaluatorProtocol,
)
from backend.app.platform.next_action.reachability import ReachabilityEvaluator

GateId = TypeVar("GateId", bound=str)


class NextActionPublisher:
    """Single publish point: Reachability (required) then Completeness (extensible)."""

    def __init__(
        self,
        *,
        reachability: ReachabilityEvaluatorProtocol | None = None,
        completeness: CompletenessEvaluator | None = None,
    ) -> None:
        self._reachability = reachability or ReachabilityEvaluator()
        self._completeness = completeness or CompletenessEvaluator()

    def can_publish(self, candidate: NextActionCandidate, ctx: ReachabilityContext) -> bool:
        reach = self._reachability.evaluate(candidate, ctx)
        if not reach.reachable:
            return False
        complete = self._completeness.evaluate(candidate, ctx)
        return complete.complete

    def publish(self, candidate: NextActionCandidate | None, ctx: ReachabilityContext) -> NextActionCandidate | None:
        if candidate is None:
            return None
        if self.can_publish(candidate, ctx):
            return candidate
        return None


def publish_first_reachable_next_action(
    *,
    gate_order: Sequence[GateId],
    gates_by_id: Mapping[GateId, object],
    gate_actions: Mapping[GateId, NextActionCandidate],
    reachability_ctx: ReachabilityContext,
    publisher: NextActionPublisher | None = None,
) -> NextActionCandidate | None:
    """Walk failing gates in order; publish first candidate passing PI-1A (+ 1B stub)."""
    pub = publisher or NextActionPublisher()
    for gate_id in gate_order:
        gate = gates_by_id.get(gate_id)
        if gate is None:
            continue
        status = getattr(gate, "status", None)
        applicable = getattr(gate, "applicable", True)
        if status != "fail" or not applicable:
            continue
        raw = gate_actions.get(gate_id)
        if raw is None:
            continue
        candidate = NextActionCandidate(
            gate_id=str(raw.gate_id if hasattr(raw, "gate_id") else gate_id),
            label_key=str(raw.label_key),
            handler_ref=str(raw.handler_ref),
        )
        published = pub.publish(candidate, reachability_ctx)
        if published is not None:
            return published
    return None
