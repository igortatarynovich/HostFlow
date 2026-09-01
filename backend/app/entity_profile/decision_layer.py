"""Entity Profile Decision Layer — ingest envelope → outcome disposition (P4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.modules.leads.duplicate_resolution import (
    LeadDuplicateMatch,
    resolve_lead_duplicate_match,
    stamp_duplicate_review_normalized_v1,
)
from backend.app.modules.outcome_rules.reference import OutcomeEvent, OutcomeRuleType
from backend.app.services.outcome_resolver import OutcomeResolution, resolve_outcomes


class IngestDisposition(str, Enum):
    lead_only = "lead_only"
    create_candidate = "create_candidate"
    create_client = "create_client"
    create_service_order = "create_service_order"
    blocked_duplicate = "blocked_duplicate"
    needs_routing = "needs_routing"
    review_queue = "review_queue"


@dataclass
class DecisionInput:
    tenant_id: str
    source: str
    normalized_payload: dict[str, Any]
    ingest_envelope: dict[str, Any] = field(default_factory=dict)
    entity_profile_code: Optional[str] = None
    route_intent: str = "unknown"
    vacancy_id: Optional[str] = None
    company_id: Optional[str] = None
    force_candidate_conversion: bool = False
    existing_candidate_id: Optional[str] = None
    current_lead_id: Optional[str] = None

    @classmethod
    def from_normalized(
        cls,
        *,
        tenant_id: str,
        source: str,
        normalized: dict[str, Any],
        force_candidate_conversion: bool = False,
        vacancy_id: Optional[str] = None,
        company_id: Optional[str] = None,
        existing_candidate_id: Optional[str] = None,
        current_lead_id: Optional[str] = None,
    ) -> DecisionInput:
        envelope = normalized.get("ingest_envelope_v1")
        if not isinstance(envelope, dict):
            envelope = {}
        entity_profile_code = (
            str(envelope.get("entity_profile_code") or normalized.get("entity_profile_code") or "").strip()
            or None
        )
        route_intent = (
            str(envelope.get("route_intent") or normalized.get("route_intent") or "unknown").strip()
            or "unknown"
        )
        if not vacancy_id:
            vacancy_id = str(normalized.get("resolved_vacancy_id") or normalized.get("vacancy_id") or "").strip() or None
        return cls(
            tenant_id=str(tenant_id),
            source=str(source or "meta"),
            normalized_payload=dict(normalized or {}),
            ingest_envelope=envelope,
            entity_profile_code=entity_profile_code,
            route_intent=route_intent,
            vacancy_id=vacancy_id,
            company_id=str(company_id or "").strip() or None,
            force_candidate_conversion=bool(force_candidate_conversion),
            existing_candidate_id=str(existing_candidate_id or "").strip() or None,
            current_lead_id=str(current_lead_id or "").strip() or None,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "source": self.source,
            "entity_profile_code": self.entity_profile_code,
            "route_intent": self.route_intent,
            "vacancy_id": self.vacancy_id,
            "company_id": self.company_id,
            "force_candidate_conversion": self.force_candidate_conversion,
            "existing_candidate_id": self.existing_candidate_id,
            "ingest_envelope": dict(self.ingest_envelope),
        }


@dataclass
class IngestDecisionContext:
    """Runtime gates computed by lead processing before outcome execution."""

    effective_processing_mode: str = "assisted"
    auto_create_enabled: bool = False
    may_auto_convert: bool = False
    triage_gate_bypass: bool = False
    pool_manual_convert_ready: bool = False
    routing_fit_status: str = "unknown"
    sales_lead_without_candidate: bool = False
    vacancy_resolved: bool = False


@dataclass
class OutcomeDecisionContext:
    """Runtime gates for non-candidate outcome execution (P5B)."""

    client_company_name_present: bool = False
    service_company_resolved: bool = False
    existing_client_id: Optional[str] = None
    existing_service_order_id: Optional[str] = None
    force_outcome_execution: bool = False


@dataclass
class DecisionResult:
    disposition: str
    outcome_resolution: OutcomeResolution
    duplicate_match: LeadDuplicateMatch
    may_create_candidate: bool = False
    may_create_client: bool = False
    may_create_service_order: bool = False
    attach_candidate_id: Optional[str] = None
    attach_client_id: Optional[str] = None
    attach_service_order_id: Optional[str] = None
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        dup = self.duplicate_match
        return {
            "disposition": self.disposition,
            "may_create_candidate": self.may_create_candidate,
            "may_create_client": self.may_create_client,
            "may_create_service_order": self.may_create_service_order,
            "attach_candidate_id": self.attach_candidate_id,
            "attach_client_id": self.attach_client_id,
            "attach_service_order_id": self.attach_service_order_id,
            "entity_profile_code": None,
            "outcome_resolution": self.outcome_resolution.to_dict(),
            "duplicate_match": {
                "level": dup.level,
                "candidate_id": str(dup.candidate.id) if dup.candidate is not None else None,
                "prior_lead_id": str(dup.prior_lead.id) if dup.prior_lead is not None else None,
                "reasons": list(dup.reasons),
                "hr_blockers": list(dup.hr_blockers),
                "needs_duplicate_review": dup.needs_duplicate_review,
            },
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
        }


def stamp_decision_blocks(
    normalized: dict[str, Any],
    decision_input: DecisionInput,
    decision: DecisionResult,
) -> None:
    normalized["decision_input_v1"] = decision_input.to_dict()
    result = decision.to_dict()
    result["entity_profile_code"] = decision_input.entity_profile_code
    normalized["decision_result_v1"] = result
    if decision.duplicate_match.needs_duplicate_review:
        stamp_duplicate_review_normalized_v1(
            normalized,
            match=decision.duplicate_match,
            error_code="DUPLICATE_REVIEW_PENDING",
        )


def _outcome_action_codes(outcome_resolution: OutcomeResolution) -> tuple[str, ...]:
    return tuple(action.code for action in outcome_resolution.actions)


async def evaluate_outcome_event_decision(
    db: AsyncSession,
    decision_input: DecisionInput,
    *,
    outcome_event: str,
    ctx: OutcomeDecisionContext,
    email: Optional[str] = None,
    phone: Optional[str] = None,
) -> DecisionResult:
    """Evaluate outcome disposition for a lifecycle event (ingest, qualified, won)."""
    outcome_resolution = resolve_outcomes(decision_input.route_intent, outcome_event)
    outcome_actions = _outcome_action_codes(outcome_resolution)
    warnings: list[str] = list(outcome_resolution.warnings)
    blocking: list[str] = list(outcome_resolution.blocking_reasons)
    empty_duplicate = LeadDuplicateMatch(level="none", candidate=None, reasons=[], hr_blockers=[])

    if OutcomeRuleType.create_client.value in outcome_actions:
        if ctx.existing_client_id:
            return DecisionResult(
                disposition=IngestDisposition.create_client.value,
                outcome_resolution=outcome_resolution,
                duplicate_match=empty_duplicate,
                may_create_client=True,
                attach_client_id=str(ctx.existing_client_id),
                warnings=warnings + ["idempotent_client_replay"],
                blocking_reasons=blocking,
            )
        if not ctx.client_company_name_present and not ctx.force_outcome_execution:
            blocking.append("client_company_name_missing")
            return DecisionResult(
                disposition=IngestDisposition.needs_routing.value,
                outcome_resolution=outcome_resolution,
                duplicate_match=empty_duplicate,
                may_create_client=False,
                blocking_reasons=blocking,
                warnings=warnings,
            )
        return DecisionResult(
            disposition=IngestDisposition.create_client.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=empty_duplicate,
            may_create_client=True,
            warnings=warnings,
            blocking_reasons=blocking,
        )

    if OutcomeRuleType.create_service_order.value in outcome_actions:
        if ctx.existing_service_order_id:
            return DecisionResult(
                disposition=IngestDisposition.create_service_order.value,
                outcome_resolution=outcome_resolution,
                duplicate_match=empty_duplicate,
                may_create_service_order=True,
                attach_service_order_id=str(ctx.existing_service_order_id),
                warnings=warnings + ["idempotent_service_order_replay"],
                blocking_reasons=blocking,
            )
        if not ctx.service_company_resolved and not ctx.force_outcome_execution:
            blocking.append("service_company_not_resolved")
            return DecisionResult(
                disposition=IngestDisposition.needs_routing.value,
                outcome_resolution=outcome_resolution,
                duplicate_match=empty_duplicate,
                may_create_service_order=False,
                blocking_reasons=blocking,
                warnings=warnings,
            )
        return DecisionResult(
            disposition=IngestDisposition.create_service_order.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=empty_duplicate,
            may_create_service_order=True,
            warnings=warnings,
            blocking_reasons=blocking,
        )

    if OutcomeRuleType.create_candidate.value in outcome_actions:
        return await evaluate_ingest_decision(
            db,
            decision_input,
            ctx=IngestDecisionContext(
                may_auto_convert=True,
                triage_gate_bypass=True,
                vacancy_resolved=bool(decision_input.vacancy_id),
                pool_manual_convert_ready=ctx.force_outcome_execution,
            ),
            email=email,
            phone=phone,
        )

    if OutcomeRuleType.review_queue.value in outcome_actions:
        return DecisionResult(
            disposition=IngestDisposition.review_queue.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=empty_duplicate,
            blocking_reasons=blocking + ["review_queue_outcome"],
            warnings=warnings,
        )

    return DecisionResult(
        disposition=IngestDisposition.lead_only.value,
        outcome_resolution=outcome_resolution,
        duplicate_match=empty_duplicate,
        warnings=warnings,
        blocking_reasons=blocking,
    )


async def evaluate_ingest_decision(
    db: AsyncSession,
    decision_input: DecisionInput,
    *,
    ctx: IngestDecisionContext,
    email: Optional[str],
    phone: Optional[str],
) -> DecisionResult:
    """Evaluate Decision Layer disposition from ingest envelope + outcome rules + dedup."""
    if decision_input.existing_candidate_id:
        outcome_resolution = resolve_outcomes(decision_input.route_intent, OutcomeEvent.ingest.value)
        return DecisionResult(
            disposition=IngestDisposition.lead_only.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=LeadDuplicateMatch(level="none", candidate=None, reasons=[], hr_blockers=[]),
            may_create_candidate=False,
            warnings=["public_intake_existing_candidate_session"],
        )

    outcome_resolution = resolve_outcomes(decision_input.route_intent, OutcomeEvent.ingest.value)
    outcome_actions = tuple(action.code for action in outcome_resolution.actions)
    outcome_wants_candidate = OutcomeRuleType.create_candidate.value in outcome_actions

    duplicate_match = await resolve_lead_duplicate_match(
        db,
        tenant_id=decision_input.tenant_id,
        company_id=decision_input.company_id,
        normalized=decision_input.normalized_payload,
        email=email,
        phone=phone,
        exclude_lead_id=decision_input.current_lead_id,
    )

    warnings: list[str] = list(outcome_resolution.warnings)
    blocking: list[str] = list(outcome_resolution.blocking_reasons)

    if ctx.sales_lead_without_candidate:
        return DecisionResult(
            disposition=IngestDisposition.lead_only.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=duplicate_match,
            may_create_candidate=False,
            warnings=warnings,
            blocking_reasons=blocking,
        )

    if duplicate_match.level == "exact" and duplicate_match.candidate is not None:
        if duplicate_match.needs_duplicate_review:
            blocking.append("duplicate_review")
            return DecisionResult(
                disposition=IngestDisposition.review_queue.value,
                outcome_resolution=outcome_resolution,
                duplicate_match=duplicate_match,
                may_create_candidate=False,
                blocking_reasons=blocking,
                warnings=warnings,
            )
        if outcome_wants_candidate or decision_input.force_candidate_conversion:
            return DecisionResult(
                disposition=IngestDisposition.blocked_duplicate.value,
                outcome_resolution=outcome_resolution,
                duplicate_match=duplicate_match,
                may_create_candidate=False,
                attach_candidate_id=str(duplicate_match.candidate.id),
                blocking_reasons=blocking + ["exact_duplicate"],
                warnings=warnings,
            )

    if (
        duplicate_match.level == "exact"
        and duplicate_match.prior_lead is not None
        and duplicate_match.candidate is None
    ):
        return DecisionResult(
            disposition=IngestDisposition.blocked_duplicate.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=duplicate_match,
            may_create_candidate=False,
            blocking_reasons=blocking + ["exact_duplicate_lead"],
            warnings=warnings,
        )

    if duplicate_match.needs_duplicate_review:
        blocking.append("duplicate_review")
        return DecisionResult(
            disposition=IngestDisposition.review_queue.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=duplicate_match,
            may_create_candidate=False,
            blocking_reasons=blocking,
            warnings=warnings,
        )

    if OutcomeRuleType.review_queue.value in outcome_actions:
        return DecisionResult(
            disposition=IngestDisposition.review_queue.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=duplicate_match,
            may_create_candidate=False,
            blocking_reasons=blocking + ["review_queue_outcome"],
            warnings=warnings,
        )

    if not outcome_wants_candidate and not decision_input.force_candidate_conversion:
        return DecisionResult(
            disposition=IngestDisposition.lead_only.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=duplicate_match,
            may_create_candidate=False,
            warnings=warnings,
            blocking_reasons=blocking,
        )

    gates_ok = (
        decision_input.force_candidate_conversion
        or ctx.pool_manual_convert_ready
        or (
            ctx.may_auto_convert
            and (ctx.triage_gate_bypass or ctx.routing_fit_status not in ("no_fit", "needs_info"))
        )
    )

    if outcome_wants_candidate and not ctx.vacancy_resolved and not ctx.pool_manual_convert_ready:
        if not decision_input.force_candidate_conversion:
            blocking.append("vacancy_not_resolved")
            return DecisionResult(
                disposition=IngestDisposition.needs_routing.value,
                outcome_resolution=outcome_resolution,
                duplicate_match=duplicate_match,
                may_create_candidate=False,
                blocking_reasons=blocking,
                warnings=warnings,
            )

    if outcome_wants_candidate and not gates_ok:
        blocking.append("auto_convert_gated")
        return DecisionResult(
            disposition=IngestDisposition.needs_routing.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=duplicate_match,
            may_create_candidate=False,
            blocking_reasons=blocking,
            warnings=warnings,
        )

    if (
        not ctx.triage_gate_bypass
        and ctx.may_auto_convert
        and ctx.routing_fit_status in ("no_fit", "needs_info")
        and not decision_input.force_candidate_conversion
        and not ctx.pool_manual_convert_ready
    ):
        blocking.append(f"lead_fit_{ctx.routing_fit_status}")
        return DecisionResult(
            disposition=IngestDisposition.needs_routing.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=duplicate_match,
            may_create_candidate=False,
            blocking_reasons=blocking,
            warnings=warnings,
        )

    if decision_input.force_candidate_conversion or (outcome_wants_candidate and gates_ok):
        return DecisionResult(
            disposition=IngestDisposition.create_candidate.value,
            outcome_resolution=outcome_resolution,
            duplicate_match=duplicate_match,
            may_create_candidate=True,
            warnings=warnings,
            blocking_reasons=blocking,
        )

    return DecisionResult(
        disposition=IngestDisposition.lead_only.value,
        outcome_resolution=outcome_resolution,
        duplicate_match=duplicate_match,
        may_create_candidate=False,
        warnings=warnings,
        blocking_reasons=blocking,
    )
