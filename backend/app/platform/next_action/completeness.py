"""PI-1B — Completeness evaluation (phase 2). Interface present; no-op in phase 1."""

from __future__ import annotations

from backend.app.platform.next_action.contracts import (
    NextActionCandidate,
    NextActionEvaluation,
    ReachabilityContext,
)


class CompletenessEvaluator:
    """Platform Layer: is the published action sufficient for the state transition?"""

    def evaluate(self, candidate: NextActionCandidate, ctx: ReachabilityContext) -> NextActionEvaluation:
        _ = candidate, ctx
        return NextActionEvaluation(reachable=True, complete=True)
