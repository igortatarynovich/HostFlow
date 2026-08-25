"""C2.2 PR-2 — Pure Rule Evaluator.

Public ops: evaluate · dry_run · diagnostics.
No SQL, ORM, Sender, Thread, Campaign, or Intent execute.
"""

from backend.app.communications.automation.evaluator.engine import (
    diagnostics,
    dry_run,
    evaluate,
)
from backend.app.communications.automation.evaluator.types import (
    CONDITION_OPS,
    OUTCOME_FIRE,
    OUTCOME_SKIP,
    Diagnostic,
    EvaluationResult,
    EventPayload,
    PolicyContext,
    RuleVersionPayload,
    TriggerSpec,
)

__all__ = [
    "CONDITION_OPS",
    "OUTCOME_FIRE",
    "OUTCOME_SKIP",
    "TriggerSpec",
    "RuleVersionPayload",
    "EventPayload",
    "PolicyContext",
    "Diagnostic",
    "EvaluationResult",
    "evaluate",
    "dry_run",
    "diagnostics",
]
