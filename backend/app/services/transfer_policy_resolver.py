"""Transfer Policy — canonical readiness decision for candidate handoff.

Pipeline (ADR-042 / recruitment-ready-policy-composition-separation):

  public context / policy selection
    → resolve_ready_composition_v1  (separate authority)
    → private composition (may be [])
    → applicable evaluators only
    → aggregate_ready_verdict_v1 → canonical Ready verdict
    → transfer_allowed = (decision == allowed)

Routing / destinations remain topology (not Ready policy requirements).
Legacy ruleset is not a handoff-gate source of truth.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.tenant import TenantLink
from backend.app.reference.recruitment_ready_policy import (
    CAP_DOCUMENT_PACKS,
    CAP_FIELD_REQUIREMENTS,
    CAP_OPERATIONAL_REQUIREMENTS,
    CAP_RECRUITER_CONFIRMATION,
    CAP_RECRUITMENT_PACKAGE,
    CAP_REQUIREMENT_ENGINE,
    COMPOSITION_EMPTY,
    DECISION_ALLOWED,
    DECISION_BLOCKED,
    READY_COMPOSITION_ID_KEY,
    aggregate_ready_verdict_v1,
    resolve_ready_composition_v1,
    unsupported_ready_verdict_v1,
)
from backend.app.services.hiring_pipeline_gates import resolve_hiring_pipeline_gates
from backend.app.services.reference_service_facade import ReferenceContext, ReferenceServiceFacade
from backend.app.services.tenant_links import get_tenant_link, list_links_for_agency
from backend.app.modules.workforce.public.ops import (
    WorkforceEligibilityContext,
    resolve_workforce_eligibility_via_contract,
)

RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY = "recruitment_dossier_confirmed_blocks"
READY_FOR_HANDOFF_STAGE = "ready_for_handoff"
POLICY_VERSION = "transfer_policy_v1"


def _read_confirmed_blocks(extra: dict[str, Any] | None) -> list[str]:
    raw = (extra or {}).get(RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY)
    if not isinstance(raw, list):
        return []
    return [str(x or "").strip() for x in raw if str(x or "").strip()]


def _candidate_extra(candidate: Candidate) -> dict[str, Any]:
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    return extra if isinstance(extra, dict) else {}


def _candidate_personal(candidate: Candidate) -> dict[str, Any]:
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    return personal if isinstance(personal, dict) else {}


def _eligibility_context(candidate: Candidate, tenant_id: str, *, stage: str | None = None) -> WorkforceEligibilityContext:
    extra = _candidate_extra(candidate)
    personal = _candidate_personal(candidate)
    return WorkforceEligibilityContext(
        tenant_id=tenant_id,
        candidate_id=str(candidate.id),
        citizenship=extra.get("citizenship") or personal.get("citizenship"),
        work_country=extra.get("work_country") or personal.get("work_country"),
        residence_status=extra.get("poland_stay_basis") or personal.get("residency_status"),
        position_category=extra.get("position_category") or extra.get("profession"),
        employment_type=extra.get("employment_type"),
        stage=stage or str(getattr(candidate, "stage", "") or "").strip().lower() or None,
        client_id=str(getattr(candidate, "own_company_id", "") or "").strip() or None,
        vacancy_id=str(getattr(candidate, "vacancy_id", "") or "").strip() or None,
    )


def _blocking_reason(
    *,
    code: str,
    message: str,
    source_layer: str,
    **extra: Any,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "code": code,
        "message": message,
        "source_layer": source_layer,
    }
    row.update(extra)
    return row


def _resolve_destinations_from_link(link: TenantLink | None) -> list[str]:
    if link is None or not link.get_handoff_enabled():
        return []
    out: list[str] = []
    if link.get_handoff_to_internal_hr():
        out.append("internal_hr")
    if link.get_handoff_to_client():
        out.append("client")
    return out


async def _resolve_destinations_for_candidate(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> tuple[list[str], TenantLink | None, dict[str, Any]]:
    """P5: Process Engine handoff evaluator (compat mock target for regression tests)."""
    return await _evaluate_handoff_routing(
        db,
        tenant_id=tenant_id,
        candidate=candidate,
    )


async def _evaluate_handoff_routing(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
) -> tuple[list[str], TenantLink | None, dict[str, Any]]:
    from backend.app.process_engine.handoff_evaluator import evaluate_handoff_destinations

    evaluation = await evaluate_handoff_destinations(
        db,
        tenant_id=str(tenant_id),
        candidate=candidate,
        system_stage=READY_FOR_HANDOFF_STAGE,
    )
    meta = {
        "handoff_mode": evaluation.handoff_mode,
        "active_handoff_rules": evaluation.active_handoff_rules,
        "routing_source": evaluation.routing_source,
        "installed_modules": sorted(evaluation.installed_modules),
        "warnings": evaluation.warnings,
    }
    return evaluation.destinations_allowed, evaluation.tenant_link, meta


def _pending_confirmations(
    blocks: list[dict[str, Any]],
    confirmed: list[str],
) -> list[dict[str, Any]]:
    confirmed_set = set(confirmed)
    pending: list[dict[str, Any]] = []
    for block in blocks:
        key = str(block.get("document_key") or block.get("label") or "").strip()
        if not key:
            continue
        if str(block.get("status") or "").lower() != "ready":
            continue
        if key in confirmed_set:
            continue
        pending.append(
            {
                "block_key": key,
                "confirmed_by_role": "recruiter",
            }
        )
    return pending


class TransferPolicyResolver:
    """Canonical transfer readiness resolver — single decision contract."""

    @classmethod
    async def resolve(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        candidate_id: str,
        target_stage: str | None = None,
        require_destination: bool = False,
        ready_context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        cand = (
            await db.execute(
                select(Candidate).where(
                    Candidate.id == str(candidate_id).strip(),
                    Candidate.tenant_id == str(tenant_id).strip(),
                    Candidate.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if cand is None:
            return {
                "candidate_id": str(candidate_id),
                "policy_version": POLICY_VERSION,
                "decision": DECISION_BLOCKED,
                "transfer_allowed": False,
                "next_action": {
                    "code": "candidate_not_found",
                    "message": "Candidate not found",
                },
                "composition_id": None,
                "destinations_allowed": [],
                "blocking_reasons": [
                    _blocking_reason(
                        code="candidate_not_found",
                        message="Candidate not found",
                        source_layer="transfer_policy",
                    )
                ],
                "required_documents": [],
                "missing_documents": [],
                "pending_verification_documents": [],
                "missing_data_fields": [],
                "required_confirmations": [],
                "approved_overrides": [],
                "source_layers": [],
                "primary_item": {
                    "code": "candidate_not_found",
                    "kind": "blocker",
                    "message": "Candidate not found",
                },
            }

        stage_code = str(target_stage or getattr(cand, "stage", "") or "").strip().lower()
        extra = _candidate_extra(cand)
        confirmed_blocks = _read_confirmed_blocks(extra)
        source_layers: set[str] = set()
        blocking_reasons: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []

        # --- composition authority (separate from evaluate) ---
        composition_ctx: dict[str, Any] = {}
        if isinstance(ready_context, Mapping):
            composition_ctx.update(dict(ready_context))
        # Candidate extra may carry an explicit selector; public callers pass ready_context.
        if READY_COMPOSITION_ID_KEY not in composition_ctx and extra.get(READY_COMPOSITION_ID_KEY):
            composition_ctx[READY_COMPOSITION_ID_KEY] = extra.get(READY_COMPOSITION_ID_KEY)
        resolution = resolve_ready_composition_v1(composition_ctx)
        if not resolution.get("resolved"):
            verdict = unsupported_ready_verdict_v1(reason=str(resolution.get("reason") or ""))
            return {
                "candidate_id": str(candidate_id),
                "policy_version": POLICY_VERSION,
                "decision": verdict["decision"],
                "transfer_allowed": False,
                "handoff_create_allowed": False,
                "composition_id": None,
                "next_action": verdict.get("next_action"),
                "primary_item": verdict.get("primary_item"),
                "destinations_allowed": [],
                "blocking_reasons": [
                    _blocking_reason(
                        code="unsupported_context",
                        message=str(
                            (verdict.get("next_action") or {}).get("message")
                            or "Ready composition unresolved"
                        ),
                        source_layer="ready_composition",
                    )
                ],
                "warnings": [],
                "required_documents": [],
                "transfer_operation_documents": [],
                "missing_documents": [],
                "pending_verification_documents": [],
                "missing_data_fields": [],
                "required_confirmations": [],
                "approved_overrides": [],
                "source_layers": ["ready_composition"],
                "eligibility_status": None,
                "handoff_allowed": False,
                "package_ready": False,
                "package_blocks": [],
                "blocking_blocks": [],
                "stage_gate": {},
                "tenant_link": {},
                "handoff_routing": {},
                "ready": False,
                "blocks": [],
                "resolve_reason": resolution.get("reason"),
            }

        composition_id = str(resolution.get("composition_id") or "")
        capabilities = {
            str(c) for c in (resolution.get("capabilities") or []) if str(c).strip()
        }
        source_layers.add("ready_composition")

        from backend.app.api.v1.candidates.pipeline_overrides_service import (
            approved_handoff_relaxed_types,
        )

        approved_overrides = sorted(
            await approved_handoff_relaxed_types(
                db,
                tenant_id=tenant_id,
                candidate_id=str(candidate_id),
            )
        )
        if approved_overrides:
            source_layers.add("pipeline_override")

        # Defaults when capabilities are not applicable (empty composition).
        handoff_allowed = True
        readiness_ok = True
        docs_ready = True
        ops_ready = True
        package_ready = True
        required_documents: list[str] = []
        transfer_operation_documents: list[str] = []
        missing_documents: list[str] = []
        pending_verification: list[str] = []
        missing_data_fields: list[dict[str, Any]] = []
        required_confirmations: list[dict[str, Any]] = []
        package_blocks: list[dict[str, Any]] = []
        blocking_blocks: list[Any] = []
        eligibility: dict[str, Any] = {}
        pkg: dict[str, Any] = {
            "ready": True,
            "blocks": [],
            "blocking_blocks": [],
            "missing_data_fields": [],
        }

        if CAP_DOCUMENT_PACKS in capabilities:
            eligibility = await resolve_workforce_eligibility_via_contract(
                db,
                context=_eligibility_context(
                    cand, tenant_id, stage=stage_code or READY_FOR_HANDOFF_STAGE
                ),
            )
            source_layers.add(CAP_DOCUMENT_PACKS)

            ctx = _eligibility_context(
                cand, tenant_id, stage=stage_code or READY_FOR_HANDOFF_STAGE
            )
            expected_docs = await ReferenceServiceFacade.get_applicable_documents(
                db,
                context=ReferenceContext(
                    tenant_id=tenant_id,
                    module="hr",
                    entity_type="candidate",
                    entity_id=str(candidate_id),
                    candidate_id=str(candidate_id),
                    citizenship=ctx.citizenship,
                    work_country=ctx.work_country,
                    residence_status=ctx.residence_status,
                    position_category=ctx.position_category,
                    employment_type=ctx.employment_type,
                    stage=ctx.stage,
                    client_id=ctx.client_id,
                    vacancy_id=ctx.vacancy_id,
                ),
            )
            from backend.app.reference.document_policy_overlay_store import (
                load_persisted_tenant_delta,
            )
            from backend.app.reference.requirement_policy_consumer_parity import (
                r5_required_set,
            )

            tenant_delta = await load_persisted_tenant_delta(db, tenant_id)
            owner_ctx = {
                "citizenship": ctx.citizenship,
                "work_country": ctx.work_country,
                "residency_status": ctx.residence_status,
                "position_category": ctx.position_category,
                "employment_type": ctx.employment_type,
                "stage": ctx.stage,
                "client_id": ctx.client_id,
                "vacancy_id": ctx.vacancy_id,
                "candidate_id": str(candidate_id),
            }
            r5_required = r5_required_set(owner_ctx, tenant_delta)
            required_documents = sorted(r5_required)
            pack_claimed_required = {
                str(row.get("document_code") or "").strip()
                for row in expected_docs
                if bool(row.get("required")) and str(row.get("document_code") or "").strip()
            }
            transfer_operation_documents = sorted(
                pack_claimed_required - set(required_documents)
            )

            ops = dict(eligibility.get("allowed_operations") or {})
            handoff_allowed = bool(ops.get("handoff_to_hr", ops.get("hr_handoff", True)))

            missing_documents = [
                str(x) for x in (eligibility.get("missing_documents") or []) if str(x).strip()
            ]
            pending_verification = [
                str(x)
                for x in (eligibility.get("pending_verification_documents") or [])
                if str(x).strip()
            ]
            if approved_overrides:
                missing_documents = [m for m in missing_documents if m not in approved_overrides]
                pending_verification = [
                    m for m in pending_verification if m not in approved_overrides
                ]

            docs_ready = not missing_documents and not pending_verification
            if approved_overrides and docs_ready:
                handoff_allowed = True

            for blocker in eligibility.get("blocking_reasons") or []:
                if not isinstance(blocker, dict):
                    continue
                doc_code = str(blocker.get("document_code") or "").strip()
                if doc_code and doc_code in approved_overrides:
                    continue
                blocking_reasons.append(
                    _blocking_reason(
                        code=str(blocker.get("code") or "eligibility_blocked"),
                        message=str(
                            blocker.get("reason")
                            or blocker.get("message")
                            or "Eligibility blocked"
                        ),
                        source_layer=CAP_DOCUMENT_PACKS,
                        document_code=doc_code or None,
                        severity=blocker.get("severity"),
                        domain=blocker.get("domain"),
                    )
                )

            if not handoff_allowed and not any(
                b.get("code")
                in {
                    "missing_required_document",
                    "pending_document_verification",
                    "expired_required_document",
                }
                for b in blocking_reasons
            ):
                blocking_reasons.append(
                    _blocking_reason(
                        code="eligibility_blocked",
                        message="Workforce eligibility blocks transfer",
                        source_layer=CAP_DOCUMENT_PACKS,
                        eligibility_status=eligibility.get("eligibility_status"),
                    )
                )

            profiles = dict(eligibility.get("readiness_profiles") or {})

            def _profile_ready(name: str) -> bool:
                profile = profiles.get(name)
                if isinstance(profile, dict):
                    return str(profile.get("status") or "").strip().lower() in {
                        "ready",
                        "warning",
                    }
                return bool(profile)

            readiness_ok = _profile_ready("hr_ready") or _profile_ready("recruitment_ready")
            if approved_overrides and docs_ready:
                readiness_ok = True
            if not readiness_ok:
                blocking_reasons.append(
                    _blocking_reason(
                        code="readiness_not_ready",
                        message="Readiness profiles are not ready",
                        source_layer=CAP_DOCUMENT_PACKS,
                    )
                )
            if not docs_ready and not any(
                b.get("code")
                in {
                    "missing_required_document",
                    "pending_document_verification",
                    "expired_required_document",
                }
                for b in blocking_reasons
            ):
                for doc in missing_documents:
                    blocking_reasons.append(
                        _blocking_reason(
                            code="missing_required_document",
                            message=f"Missing required document: {doc}",
                            source_layer=CAP_DOCUMENT_PACKS,
                            document_code=doc,
                        )
                    )
                for doc in pending_verification:
                    blocking_reasons.append(
                        _blocking_reason(
                            code="pending_document_verification",
                            message=f"Pending verification: {doc}",
                            source_layer=CAP_DOCUMENT_PACKS,
                            document_code=doc,
                        )
                    )

        if CAP_RECRUITMENT_PACKAGE in capabilities:
            from backend.app.services.recruitment_package_readiness import (
                evaluate_recruitment_package,
            )

            pkg = await evaluate_recruitment_package(
                db,
                tenant_id=tenant_id,
                candidate_id=str(candidate_id),
                relaxed_doc_types=set(approved_overrides),
            )
            source_layers.add(CAP_RECRUITMENT_PACKAGE)
            package_blocks = list(pkg.get("blocks") or [])
            blocking_blocks = list(pkg.get("blocking_blocks") or [])
            for block_key in blocking_blocks:
                blocking_reasons.append(
                    _blocking_reason(
                        code="package_block_incomplete",
                        message=f"Dossier block incomplete: {block_key}",
                        source_layer=CAP_RECRUITMENT_PACKAGE,
                        block_key=str(block_key),
                    )
                )
            if not missing_data_fields:
                missing_data_fields = list(pkg.get("missing_data_fields") or [])
            for field in missing_data_fields:
                label = str(field.get("label") or field.get("field_code") or "field")
                if any(
                    b.get("source_layer") == CAP_FIELD_REQUIREMENTS
                    and b.get("field_code") == field.get("field_code")
                    for b in blocking_reasons
                ):
                    continue
                blocking_reasons.append(
                    _blocking_reason(
                        code="missing_data_field",
                        message=f"Missing required data: {label}",
                        source_layer=CAP_RECRUITMENT_PACKAGE,
                        field_code=field.get("field_code"),
                        label=label,
                    )
                )
            package_ready = bool(pkg.get("ready"))

        if CAP_FIELD_REQUIREMENTS in capabilities:
            from backend.app.field_registry.requirement_evaluator import (
                evaluate_field_requirements_for_candidate,
            )

            field_requirement_eval = await evaluate_field_requirements_for_candidate(
                db,
                tenant_id=tenant_id,
                candidate=cand,
                context="transition",
                system_stage=READY_FOR_HANDOFF_STAGE,
            )
            source_layers.add(CAP_FIELD_REQUIREMENTS)
            for reason in field_requirement_eval.get("blocking_reasons") or []:
                blocking_reasons.append(
                    _blocking_reason(
                        code=str(reason.get("code") or "missing_data_field"),
                        message=str(reason.get("message") or "Missing required field"),
                        source_layer=CAP_FIELD_REQUIREMENTS,
                        field_code=reason.get("field_code"),
                        qualified_code=reason.get("qualified_code"),
                        label=reason.get("label"),
                        requirement_code=reason.get("requirement_code"),
                    )
                )
            field_missing = list(field_requirement_eval.get("missing_fields") or [])
            if field_missing:
                missing_data_fields = field_missing

        if CAP_REQUIREMENT_ENGINE in capabilities:
            req_engine = pkg.get("requirement_engine") or {}
            if req_engine.get("applied"):
                source_layers.add(CAP_REQUIREMENT_ENGINE)
                from backend.app.requirement_rules.readiness_bridge import (
                    map_requirement_evaluation_to_package_fragments,
                )

                req_fragments = map_requirement_evaluation_to_package_fragments(req_engine)
                for reason in req_fragments.get("blocking_reasons") or []:
                    blocking_reasons.append(reason)
                for warning in req_fragments.get("warnings") or []:
                    warnings.append(warning)
                for doc_code in req_fragments.get("missing_documents") or []:
                    norm = str(doc_code or "").strip()
                    if not norm or norm in approved_overrides:
                        continue
                    if norm not in missing_documents:
                        missing_documents.append(norm)
                missing_documents = sorted(set(missing_documents))
                if req_fragments.get("missing_data_fields"):
                    seen_field_codes = {
                        str(f.get("field_code") or "") for f in missing_data_fields
                    }
                    for field in req_fragments["missing_data_fields"]:
                        fc = str(field.get("field_code") or "")
                        if fc and fc not in seen_field_codes:
                            missing_data_fields.append(field)
                            seen_field_codes.add(fc)

        if CAP_OPERATIONAL_REQUIREMENTS in capabilities:
            from backend.app.requirement_rules.readiness_bridge import (
                resolve_entity_profile_code_for_candidate,
            )
            from backend.app.services.operational_requirements_service import (
                evaluate_operational_requirements_for_candidate,
                operational_requirement_blocking_reasons,
            )

            entity_profile_code = await resolve_entity_profile_code_for_candidate(
                db,
                tenant_id=tenant_id,
                candidate=cand,
            )
            operational_rows = await evaluate_operational_requirements_for_candidate(
                db,
                tenant_id=tenant_id,
                candidate=cand,
                entity_profile_code=entity_profile_code,
            )
            ops_blockers = operational_requirement_blocking_reasons(operational_rows)
            if ops_blockers:
                source_layers.add(CAP_OPERATIONAL_REQUIREMENTS)
            for reason in ops_blockers:
                blocking_reasons.append(
                    _blocking_reason(
                        code=str(reason.get("code") or "operational_requirement_open"),
                        message=str(
                            reason.get("message") or "Operational requirement open"
                        ),
                        source_layer=CAP_OPERATIONAL_REQUIREMENTS,
                        requirement_code=reason.get("requirement_code"),
                        requirement_type=reason.get("requirement_type"),
                    )
                )
            ops_ready = not ops_blockers

        if CAP_RECRUITER_CONFIRMATION in capabilities:
            required_confirmations = _pending_confirmations(
                package_blocks, confirmed_blocks
            )
            if required_confirmations:
                source_layers.add(CAP_RECRUITER_CONFIRMATION)
                for item in required_confirmations:
                    key = str(item.get("block_key") or "")
                    blocking_reasons.append(
                        _blocking_reason(
                            code="unconfirmed_block",
                            message=f"Recruiter must confirm reviewed block: {key}",
                            source_layer=CAP_RECRUITER_CONFIRMATION,
                            block_key=key,
                            confirmed_by_role="recruiter",
                        )
                    )
            package_ready = bool(pkg.get("ready")) and not required_confirmations

        # Topology / routing — not Ready policy requirements.
        destinations_allowed, tenant_link, handoff_meta = await _resolve_destinations_for_candidate(
            db,
            tenant_id=tenant_id,
            candidate=cand,
        )
        source_layers.add("process_engine_handoff_rules")
        source_layers.add("tenant_link")
        for warning in handoff_meta.get("warnings") or []:
            warnings.append(warning)
        destination_block: dict[str, Any] | None = None
        if not destinations_allowed:
            destination_block = _blocking_reason(
                code="no_destination",
                message="No handoff destination enabled (handoff rules + tenant link)",
                source_layer="process_engine_handoff_rules",
                severity="warning",
                handoff_mode=handoff_meta.get("handoff_mode"),
                active_handoff_rules=handoff_meta.get("active_handoff_rules") or [],
            )
            if require_destination:
                blocking_reasons.append(destination_block)
            else:
                warnings.append(destination_block)

        hiring_gates = await resolve_hiring_pipeline_gates(
            db, tenant_id, candidate_id=str(candidate_id)
        )
        source_layers.add("hiring_pipeline_gates")
        stage_gate = {
            "target_stage": READY_FOR_HANDOFF_STAGE,
            "requires_recruitment_package": CAP_RECRUITMENT_PACKAGE in capabilities,
            "hiring_pipeline_gates_key": "hiring_stage_gates_v1",
            "stages_without_doc_pipeline_block": sorted(
                hiring_gates.stages_without_doc_pipeline_block
            ),
        }

        # Policy conjuncts that still apply under driver composition.
        if CAP_DOCUMENT_PACKS in capabilities:
            if not handoff_allowed:
                pass  # already in blocking_reasons
            if not docs_ready:
                pass
            if not readiness_ok:
                pass
        if CAP_RECRUITMENT_PACKAGE in capabilities and not bool(pkg.get("ready")):
            if not any(b.get("code") == "package_block_incomplete" for b in blocking_reasons):
                blocking_reasons.append(
                    _blocking_reason(
                        code="package_block_incomplete",
                        message="Recruitment package is not ready",
                        source_layer=CAP_RECRUITMENT_PACKAGE,
                    )
                )
        if CAP_OPERATIONAL_REQUIREMENTS in capabilities and not ops_ready:
            pass  # ops blockers already recorded
        if CAP_RECRUITER_CONFIRMATION in capabilities and required_confirmations:
            pass

        # Destination is topology — never a Ready policy requirement.
        # It may appear in blocking_reasons when require_destination (for assert_transfer_allowed
        # / handoff_create_allowed), but must not drive Ready decision / transfer_allowed.
        policy_reasons = [
            r
            for r in blocking_reasons
            if not (
                r.get("code") == "no_destination"
                and r.get("source_layer") == "process_engine_handoff_rules"
            )
        ]

        verdict = aggregate_ready_verdict_v1(
            composition_id=composition_id,
            capabilities=sorted(capabilities),
            blocking_reasons=policy_reasons,
        )
        transfer_allowed = bool(verdict["transfer_allowed"]) and verdict["decision"] == DECISION_ALLOWED
        # Empty composition: no policy requirements invoked → allowed on same aggregator path.
        if composition_id == COMPOSITION_EMPTY and not capabilities:
            assert verdict["decision"] == DECISION_ALLOWED
            transfer_allowed = True

        handoff_create_allowed = transfer_allowed and bool(destinations_allowed)

        return {
            "candidate_id": str(candidate_id),
            "policy_version": POLICY_VERSION,
            "decision": verdict["decision"],
            "transfer_allowed": transfer_allowed,
            "next_action": verdict.get("next_action"),
            "primary_item": verdict.get("primary_item"),
            "composition_id": composition_id,
            "active_missing": verdict.get("active_missing") or [],
            "handoff_create_allowed": handoff_create_allowed,
            "destinations_allowed": destinations_allowed,
            "blocking_reasons": blocking_reasons,
            "warnings": warnings,
            "required_documents": required_documents,
            "transfer_operation_documents": transfer_operation_documents,
            "missing_documents": missing_documents,
            "pending_verification_documents": pending_verification,
            "missing_data_fields": missing_data_fields,
            "required_confirmations": required_confirmations,
            "approved_overrides": approved_overrides,
            "source_layers": sorted(source_layers),
            "eligibility_status": eligibility.get("eligibility_status"),
            # Evidence / compatibility fields — not peer process authorities.
            "handoff_allowed": handoff_allowed,
            "package_ready": package_ready,
            "package_blocks": package_blocks,
            "blocking_blocks": blocking_blocks,
            "stage_gate": stage_gate,
            "tenant_link": {
                "handoff_enabled": bool(tenant_link.get_handoff_enabled())
                if tenant_link
                else False,
                "handoff_to_client": bool(tenant_link.get_handoff_to_client())
                if tenant_link
                else False,
                "handoff_to_internal_hr": bool(tenant_link.get_handoff_to_internal_hr())
                if tenant_link
                else False,
                "workforce_handoff_on_ready_for_handoff_stage": bool(
                    tenant_link.get_workforce_handoff_on_ready_for_handoff_stage()
                )
                if tenant_link
                else False,
            },
            "handoff_routing": {
                "handoff_mode": handoff_meta.get("handoff_mode"),
                "active_handoff_rules": handoff_meta.get("active_handoff_rules") or [],
                "routing_source": handoff_meta.get("routing_source"),
                "installed_modules": handoff_meta.get("installed_modules") or [],
            },
            # Backward-compatible recruitment-package fields (evidence only).
            "ready": package_ready and handoff_allowed and transfer_allowed,
            "blocks": package_blocks,
        }

    @classmethod
    async def assert_transfer_allowed(
        cls,
        db: AsyncSession,
        *,
        tenant_id: str,
        candidate_id: str,
        target_stage: str | None = None,
        require_destination: bool = False,
    ) -> dict[str, Any]:
        """Return error detail dict when transfer blocked; empty dict when OK."""
        report = await cls.resolve(
            db,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
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


async def resolve_tenant_transfer_policy_summary(
    db: AsyncSession,
    *,
    tenant_id: str,
) -> dict[str, Any]:
    """Aggregated tenant-level transfer policy view for Settings → Transfer Policy."""
    gates = await resolve_hiring_pipeline_gates(db, tenant_id)

    enabled_pack_codes = await ReferenceServiceFacade.list_enabled_document_pack_codes(
        db,
        tenant_id=str(tenant_id).strip(),
    )

    links = await list_links_for_agency(db, str(tenant_id).strip())
    link_summaries = []
    for link in links:
        if not link.get_handoff_enabled():
            continue
        link_summaries.append(
            {
                "client_company_id": link.client_company_id,
                "client_tenant_id": link.client_tenant_id,
                "destinations_allowed": _resolve_destinations_from_link(link),
                "workforce_handoff_on_ready_for_handoff_stage": link.get_workforce_handoff_on_ready_for_handoff_stage(),
            }
        )

    return {
        "policy_version": POLICY_VERSION,
        "layers": {
            "document_packs": {
                "storage": "ref_packs + tenant_document_pack_enablements + tenant_document_type_overrides",
                "enabled_packs": [{"code": code} for code in enabled_pack_codes],
            },
            "hiring_pipeline_gates": {
                "storage": 'tenants.settings["hiring_stage_gates_v1"]',
                "stages_without_doc_pipeline_block": sorted(gates.stages_without_doc_pipeline_block),
                "stages_verify_uploads_block_forward": sorted(gates.stages_verify_uploads_block_forward),
                "stages_require_vacancy_for_forward": sorted(gates.stages_require_vacancy_for_forward),
            },
            "tenant_link_routing": {
                "storage": "tenant_links.features_json",
                "active_handoff_links": link_summaries,
            },
            "candidate_overrides": {
                "storage": "candidate_pipeline_overrides",
                "scope_for_handoff": "both",
                "approval_roles": ["supervisor", "administrator"],
            },
            "recruiter_confirmations": {
                "storage": f"candidate.extra.{RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY}",
                "confirmed_by_role": "recruiter",
            },
            "legacy_ruleset": {
                "storage": "document_ruleset_versions",
                "handoff_gate_source": False,
                "note": "Compatibility only — not used by TransferPolicyResolver",
            },
            "candidate_profile": {
                "storage": "candidate_profiles.config.document_configs",
                "handoff_gate_source": False,
                "note": "Influences HR verification plan; merged indirectly via eligibility context",
            },
        },
        "governance": {
            "enable_document_pack": ["tenant_administrator"],
            "document_type_override": ["tenant_administrator", "compliance_admin"],
            "candidate_override_request": ["recruiter"],
            "candidate_override_approve": ["supervisor", "administrator"],
            "handoff_route_config": ["agency_administrator"],
            "recruiter_block_confirm": ["recruiter"],
            "hr_final_accept": ["hr_officer"],
            "platform_pack_change": ["platform_administrator"],
        },
    }


__all__ = [
    "TransferPolicyResolver",
    "resolve_tenant_transfer_policy_summary",
    "RECRUITMENT_CONFIRMED_BLOCKS_EXTRA_KEY",
    "POLICY_VERSION",
]
