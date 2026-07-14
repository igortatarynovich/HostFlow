"""PI-1A — Reachability evaluation before Next Action publication."""

from __future__ import annotations

from backend.app.platform.next_action.contracts import (
    NextActionCandidate,
    NextActionEvaluation,
    ReachabilityContext,
)
from backend.app.platform.next_action.setup_activation_policy import (
    is_handler_allowed_during_setup_activation_lock,
    is_handler_blocked_for_guided_trial,
)


class ReachabilityEvaluator:
    """Platform Layer: can the user open the handler in the current state?"""

    def evaluate(self, candidate: NextActionCandidate, ctx: ReachabilityContext) -> NextActionEvaluation:
        handler = str(candidate.handler_ref or "").strip()
        if not handler:
            return NextActionEvaluation(reachable=False, complete=True, reason_code="missing_handler")

        if ctx.is_superadmin:
            return NextActionEvaluation(reachable=True, complete=True)

        if ctx.setup_ready:
            return NextActionEvaluation(reachable=True, complete=True)

        if not is_handler_allowed_during_setup_activation_lock(handler):
            return NextActionEvaluation(reachable=False, complete=True, reason_code="setup_activation_lock")

        if is_handler_blocked_for_guided_trial(handler, tenant_status=ctx.tenant_status):
            return NextActionEvaluation(reachable=False, complete=True, reason_code="guided_trial_settings")

        return NextActionEvaluation(reachable=True, complete=True)
