"""C2.2 PR-2 — Pure Rule Evaluator engine.

Public ops: evaluate · dry_run · diagnostics.
No SQL, ORM, Sender, Thread, Campaign, or Intent execute imports.
"""

from __future__ import annotations

from typing import Any

from backend.app.communications.automation.evaluator.conditions import (
    ConditionError,
    evaluate_condition,
    map_variables,
    match_filter,
)
from backend.app.communications.automation.evaluator.types import (
    DIAG_CONDITIONS_UNMATCHED,
    DIAG_INTENT_KEY_MISSING,
    DIAG_INVALID_CONDITIONS,
    DIAG_INVALID_EVENT,
    DIAG_RULE_ARCHIVED,
    DIAG_RULE_DISABLED,
    DIAG_RULE_NOT_PUBLISHED,
    DIAG_TRIGGER_FILTER_MISMATCH,
    DIAG_TRIGGER_MISMATCH,
    OUTCOME_FIRE,
    OUTCOME_SKIP,
    SEVERITY_ERROR,
    SEVERITY_INFO,
    Diagnostic,
    EvaluationResult,
    EventPayload,
    PolicyContext,
    RuleVersionPayload,
)


def _diag(
    code: str,
    message: str,
    *,
    severity: str = SEVERITY_ERROR,
    path: str | None = None,
    details: dict[str, Any] | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        path=path,
        details=details or {},
    )


def _skip(
    rule: RuleVersionPayload,
    event: EventPayload,
    *,
    reason_codes: list[str],
    diagnostics: list[Diagnostic],
    matched_trigger: str | None = None,
    template_variables: dict[str, Any] | None = None,
) -> EvaluationResult:
    return EvaluationResult(
        ok=True,
        outcome=OUTCOME_SKIP,
        rule_id=rule.rule_id,
        rule_version_id=rule.rule_version_id,
        source_event_id=event.event_id,
        event_type=event.event_type,
        intent_key=None,
        preferred_template_key=None,
        channel=None,
        recipient_strategy=None,
        recipient_config={},
        template_variables=dict(template_variables or {}),
        matched_trigger_event_type=matched_trigger,
        reason_codes=tuple(reason_codes),
        diagnostics=tuple(diagnostics),
        correlation_id=event.correlation_id,
    )


def evaluate(
    rule: RuleVersionPayload,
    event: EventPayload,
    *,
    policy: PolicyContext | None = None,
) -> EvaluationResult:
    """Evaluate whether this rule should fire an Intent for the event.

    Deterministic: same inputs → identical EvaluationResult.
    Does not create Intent, send, or touch Thread.
    """
    _ = policy or PolicyContext()
    diags: list[Diagnostic] = []

    if not str(event.event_id or "").strip() or not str(event.event_type or "").strip():
        diags.append(
            _diag(DIAG_INVALID_EVENT, "event_id and event_type are required")
        )
        return EvaluationResult(
            ok=False,
            outcome=OUTCOME_SKIP,
            rule_id=rule.rule_id,
            rule_version_id=rule.rule_version_id,
            source_event_id=str(event.event_id or ""),
            event_type=str(event.event_type or ""),
            intent_key=None,
            preferred_template_key=None,
            channel=None,
            recipient_strategy=None,
            recipient_config={},
            template_variables={},
            matched_trigger_event_type=None,
            reason_codes=(DIAG_INVALID_EVENT,),
            diagnostics=tuple(diags),
            correlation_id=event.correlation_id,
        )

    if str(rule.version_status) != "published":
        diags.append(
            _diag(
                DIAG_RULE_NOT_PUBLISHED,
                "Only published rule versions may fire",
                details={"status": rule.version_status},
            )
        )
        return _skip(rule, event, reason_codes=[DIAG_RULE_NOT_PUBLISHED], diagnostics=diags)

    if str(rule.rule_status) == "archived":
        diags.append(_diag(DIAG_RULE_ARCHIVED, "Rule is archived"))
        return _skip(rule, event, reason_codes=[DIAG_RULE_ARCHIVED], diagnostics=diags)

    if not rule.enabled:
        diags.append(_diag(DIAG_RULE_DISABLED, "Rule is disabled", severity=SEVERITY_INFO))
        return _skip(rule, event, reason_codes=[DIAG_RULE_DISABLED], diagnostics=diags)

    event_type = str(event.event_type).strip()
    matched = None
    for trigger in rule.triggers:
        if str(trigger.event_type).strip() != event_type:
            continue
        if not match_filter(trigger.event_filter, event.data):
            diags.append(
                _diag(
                    DIAG_TRIGGER_FILTER_MISMATCH,
                    "Trigger event_filter did not match",
                    severity=SEVERITY_INFO,
                    details={"event_type": event_type},
                )
            )
            return _skip(
                rule,
                event,
                reason_codes=[DIAG_TRIGGER_FILTER_MISMATCH],
                diagnostics=diags,
                matched_trigger=event_type,
            )
        matched = event_type
        break

    if matched is None:
        diags.append(
            _diag(
                DIAG_TRIGGER_MISMATCH,
                "No trigger matches event_type",
                severity=SEVERITY_INFO,
                details={"event_type": event_type},
            )
        )
        return _skip(rule, event, reason_codes=[DIAG_TRIGGER_MISMATCH], diagnostics=diags)

    try:
        conditions_ok = evaluate_condition(dict(rule.conditions or {}), dict(event.data or {}))
    except ConditionError as exc:
        diags.append(
            _diag(
                DIAG_INVALID_CONDITIONS,
                exc.message,
                path=exc.path,
            )
        )
        return EvaluationResult(
            ok=False,
            outcome=OUTCOME_SKIP,
            rule_id=rule.rule_id,
            rule_version_id=rule.rule_version_id,
            source_event_id=event.event_id,
            event_type=event.event_type,
            intent_key=None,
            preferred_template_key=None,
            channel=None,
            recipient_strategy=None,
            recipient_config={},
            template_variables={},
            matched_trigger_event_type=matched,
            reason_codes=(DIAG_INVALID_CONDITIONS,),
            diagnostics=tuple(diags),
            correlation_id=event.correlation_id,
        )

    if not conditions_ok:
        diags.append(
            _diag(
                DIAG_CONDITIONS_UNMATCHED,
                "Rule conditions did not match event data",
                severity=SEVERITY_INFO,
            )
        )
        return _skip(
            rule,
            event,
            reason_codes=[DIAG_CONDITIONS_UNMATCHED],
            diagnostics=diags,
            matched_trigger=matched,
        )

    intent_key = str(rule.intent_key or "").strip()
    if not intent_key:
        diags.append(_diag(DIAG_INTENT_KEY_MISSING, "Published rule missing intent_key"))
        return EvaluationResult(
            ok=False,
            outcome=OUTCOME_SKIP,
            rule_id=rule.rule_id,
            rule_version_id=rule.rule_version_id,
            source_event_id=event.event_id,
            event_type=event.event_type,
            intent_key=None,
            preferred_template_key=None,
            channel=None,
            recipient_strategy=None,
            recipient_config={},
            template_variables={},
            matched_trigger_event_type=matched,
            reason_codes=(DIAG_INTENT_KEY_MISSING,),
            diagnostics=tuple(diags),
            correlation_id=event.correlation_id,
        )

    variables = map_variables(rule.variables_mapping, dict(event.data or {}))
    return EvaluationResult(
        ok=True,
        outcome=OUTCOME_FIRE,
        rule_id=rule.rule_id,
        rule_version_id=rule.rule_version_id,
        source_event_id=event.event_id,
        event_type=event.event_type,
        intent_key=intent_key,
        preferred_template_key=rule.preferred_template_key,
        channel=rule.channel,
        recipient_strategy=rule.recipient_strategy,
        recipient_config=dict(rule.recipient_config or {}),
        template_variables=variables,
        matched_trigger_event_type=matched,
        reason_codes=("matched",),
        diagnostics=(),
        correlation_id=event.correlation_id,
    )


def dry_run(
    rule: RuleVersionPayload,
    event: EventPayload,
    *,
    policy: PolicyContext | None = None,
) -> EvaluationResult:
    """Alias of evaluate — same engine, no side effects (already pure)."""
    return evaluate(rule, event, policy=policy)


def diagnostics(
    rule: RuleVersionPayload,
    event: EventPayload,
    *,
    policy: PolicyContext | None = None,
) -> tuple[Diagnostic, ...]:
    return evaluate(rule, event, policy=policy).diagnostics


__all__ = ["evaluate", "dry_run", "diagnostics"]
