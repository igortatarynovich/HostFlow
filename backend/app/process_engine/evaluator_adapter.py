"""Transition evaluator adapter — canonical Process Engine runtime entry (P2 facade)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.process_engine.constants import (
    EVALUATOR_HOOK_RECRUITMENT_TRANSFER_POLICY,
    RECRUITMENT_MODULE,
)
from backend.app.process_engine.profile_resolver import (
    effective_process_profile_to_dict,
    resolve_effective_process_profile_for_candidate_id,
)
from backend.app.process_engine.pipeline_mapping import (
    infer_pe_system_stage_code,
    resolve_qualified_system_stage_for_candidate,
)
from backend.app.services.transfer_policy_resolver import TransferPolicyResolver


class TransitionEvaluatorAdapter:
    """Process Engine runtime facade — API/service layer must call this, not TransferPolicyResolver."""

    @classmethod
    async def _apply_ready_for_handoff_requirement_gate(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        candidate_id: str,
        target_stage: str | None,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        from backend.app.requirement_rules.transition_bridge import (
            evaluate_ready_for_handoff_requirement_gate,
            is_ready_for_handoff_gate,
            merge_transition_requirement_gate,
        )

        if not is_ready_for_handoff_gate(target_stage):
            return report
        gate = await evaluate_ready_for_handoff_requirement_gate(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
        )
        if gate is None:
            return report
        return merge_transition_requirement_gate(report, gate)

    @classmethod
    async def _resolve_recruitment_transfer_report(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        candidate_id: str,
        target_stage: str | None,
        require_destination: bool,
    ) -> dict[str, Any]:
        report = await TransferPolicyResolver.resolve(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            target_stage=target_stage,
            require_destination=require_destination,
        )
        return await cls._apply_ready_for_handoff_requirement_gate(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            target_stage=target_stage,
            report=report,
        )

    @classmethod
    async def _resolve_recruitment_target_system_stage(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        candidate_id: str,
        legacy_stage_code: str | None,
    ) -> str | None:
        legacy = str(legacy_stage_code or "").strip().lower()
        if not legacy:
            return None
        qualified = await resolve_qualified_system_stage_for_candidate(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            legacy_stage_code=legacy,
        )
        if qualified is not None:
            return qualified.code
        return infer_pe_system_stage_code(legacy) or legacy

    @classmethod
    async def evaluate_transition(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        module: str,
        entity_type: str,
        entity_id: str,
        target_system_stage: str | None = None,
        require_destination: bool = False,
        evaluator_hook: str | None = None,
        include_engine_metadata: bool = True,
    ) -> dict[str, Any]:
        hook = evaluator_hook or cls._default_hook(module, entity_type, target_system_stage)
        if hook == EVALUATOR_HOOK_RECRUITMENT_TRANSFER_POLICY or (
            module == RECRUITMENT_MODULE and entity_type == "candidate"
        ):
            # P4: resolve legacy funnel stage → qualified PE system stage before transfer policy.
            target_stage = target_system_stage
            if target_system_stage:
                target_stage = await cls._resolve_recruitment_target_system_stage(
                    db,
                    tenant_id=tenant_id,
                    candidate_id=entity_id,
                    legacy_stage_code=target_system_stage,
                )
            # Compatibility: recruitment transfer policy still lives in TransferPolicyResolver (P2).
            report = await cls._resolve_recruitment_transfer_report(
                db,
                tenant_id=tenant_id,
                candidate_id=entity_id,
                target_stage=target_stage,
                require_destination=require_destination,
            )
            if not include_engine_metadata:
                return report
            return {
                **report,
                "allowed": bool(report.get("transfer_allowed")),
                "evaluation_kind": "transition",
                "evaluator_hook": EVALUATOR_HOOK_RECRUITMENT_TRANSFER_POLICY,
            }
        return {
            "allowed": True,
            "evaluation_kind": "transition",
            "evaluator_hook": hook or "noop",
            "policy_version": "process_engine_v1",
            "blocking_reasons": [],
            "warnings": [{"code": "evaluator_not_implemented", "message": f"No evaluator for hook {hook}", "source_layer": "process_engine"}],
        }

    @classmethod
    async def assert_transition_allowed(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        module: str,
        entity_type: str,
        entity_id: str,
        target_system_stage: str | None = None,
        require_destination: bool = False,
        evaluator_hook: str | None = None,
    ) -> dict[str, Any]:
        if module == RECRUITMENT_MODULE and entity_type == "candidate":
            target_stage = target_system_stage
            if target_system_stage:
                target_stage = await cls._resolve_recruitment_target_system_stage(
                    db,
                    tenant_id=tenant_id,
                    candidate_id=entity_id,
                    legacy_stage_code=target_system_stage,
                )
            # Compatibility: recruitment transfer policy still lives in TransferPolicyResolver (P2).
            report = await cls._resolve_recruitment_transfer_report(
                db,
                tenant_id=tenant_id,
                candidate_id=entity_id,
                target_stage=target_stage,
                require_destination=require_destination,
            )
            allowed = report.get("handoff_create_allowed") if require_destination else report.get("transfer_allowed")
            if allowed:
                return {}
            return {
                "code": "transfer_blocked",
                "message": "Transfer is blocked by transfer policy",
                "policy_version": report.get("policy_version"),
                "blocking_reasons": report.get("blocking_reasons") or [],
                "missing_types": sorted(
                    set(
                        [
                            *(report.get("missing_documents") or []),
                            *(report.get("pending_verification_documents") or []),
                        ]
                    )
                ),
                "missing_data_fields": report.get("missing_data_fields") or [],
                "blocking_blocks": report.get("blocking_blocks") or [],
                "required_confirmations": report.get("required_confirmations") or [],
                "package_blocks": report.get("package_blocks") or [],
                "eligibility_status": report.get("eligibility_status"),
                "destinations_allowed": report.get("destinations_allowed") or [],
                "approved_overrides": report.get("approved_overrides") or [],
                "source_layers": report.get("source_layers") or [],
            }
        report = await cls.evaluate_transition(
            db,
            tenant_id=tenant_id,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            target_system_stage=target_system_stage,
            require_destination=require_destination,
            evaluator_hook=evaluator_hook,
        )
        if report.get("allowed"):
            return {}
        return {
            "code": "transition_blocked",
            "message": "Transition is blocked by process engine",
            "blocking_reasons": report.get("blocking_reasons") or [],
        }

    @classmethod
    async def evaluate_handoff(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        candidate_id: str,
        system_stage: str | None = "ready_for_handoff",
        module: str = RECRUITMENT_MODULE,
    ) -> dict[str, Any]:
        """P5: canonical handoff destination evaluation via PE Handoff Rule Registry."""
        from backend.app.process_engine.handoff_evaluator import (
            evaluate_handoff_destinations_for_candidate_id,
            handoff_evaluation_to_dict,
        )

        evaluation = await evaluate_handoff_destinations_for_candidate_id(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            system_stage=str(system_stage or "ready_for_handoff"),
            module=module,
        )
        if evaluation is None:
            return {
                "destinations_allowed": [],
                "handoff_create_allowed": False,
                "handoff_mode": "none",
                "active_handoff_rules": [],
                "routing_source": "process_engine_handoff_rules",
                "warnings": [
                    {
                        "code": "candidate_not_found",
                        "message": "Candidate not found",
                        "source_layer": "process_engine_handoff_rules",
                    }
                ],
            }
        payload = handoff_evaluation_to_dict(evaluation)
        payload["handoff_create_allowed"] = bool(evaluation.destinations_allowed)
        return payload

    @classmethod
    async def resolve_hiring_pipeline_gates(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        candidate_id: str,
    ) -> dict[str, Any]:
        """P6: profile-scoped hiring pipeline gates via pe_transition_rules."""
        from backend.app.process_engine.transition_rules_adapter import (
            resolve_hiring_pipeline_gates_for_candidate,
        )
        from backend.app.services.hiring_pipeline_gates import serialize_gates_public

        gates, meta = await resolve_hiring_pipeline_gates_for_candidate(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
        )
        return {**serialize_gates_public(gates), "resolution": meta}

    @classmethod
    async def resolve_effective_process_profile_for_candidate_id(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        candidate_id: str,
        module: str = RECRUITMENT_MODULE,
    ) -> dict[str, Any] | None:
        """P3: effective process profile for candidate stage logic (via vacancy binding)."""
        resolved = await resolve_effective_process_profile_for_candidate_id(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            module=module,
        )
        if resolved is None:
            return None
        return effective_process_profile_to_dict(resolved)

    @staticmethod
    def _default_hook(
        module: str,
        entity_type: str,
        target_system_stage: Optional[str],
    ) -> str | None:
        if module == RECRUITMENT_MODULE and entity_type == "candidate":
            if str(target_system_stage or "").strip().lower() in {"", "ready_for_handoff"}:
                return EVALUATOR_HOOK_RECRUITMENT_TRANSFER_POLICY
        return None
