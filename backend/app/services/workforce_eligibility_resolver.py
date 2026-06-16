from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.document import Document
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services.document_expiry_engine import (
    aggregate_document_expiry_states,
    evaluate_document_expiry,
    owner_expiry_aggregate_to_dict,
)
from backend.app.services.reference_service_facade import ReferenceContext, ReferenceServiceFacade


@dataclass
class WorkforceEligibilityContext:
    tenant_id: str
    candidate_id: Optional[str] = None
    employee_id: Optional[str] = None
    citizenship: Optional[str] = None
    work_country: Optional[str] = None
    residence_status: Optional[str] = None
    position_category: Optional[str] = None
    employment_type: Optional[str] = None
    stage: Optional[str] = None
    client_id: Optional[str] = None
    vacancy_id: Optional[str] = None


class WorkforceEligibilityResolver:
    """M5 unified eligibility/compliance/readiness runtime resolver."""

    _LEGACY_OPS = (
        "client_submission",
        "hr_handoff",
        "contract_signing",
        "route_assignment",
        "onboarding_completion",
        "employee_activation",
    )
    _OPS = (
        "submit_to_client",
        "handoff_to_hr",
        "approve_hr_verification",
        "sign_contract",
        "activate_employee",
        "assign_route",
        "start_work",
        "payroll_ready",
    )
    _VERIFIED_STATUSES = {
        "approved",
        "verified",
        "completed",
        "issued",
        "registered",
        "active",
        "delivered",
        "received",
        "not_required",
    }
    _OP_ALIASES = {
        "client_submission": "submit_to_client",
        "hr_handoff": "handoff_to_hr",
        "contract_signing": "sign_contract",
        "route_assignment": "assign_route",
        "employee_activation": "activate_employee",
        "onboarding_completion": "start_work",
    }
    _BLOCKER_CODES = {
        "missing": "missing_required_document",
        "expired": "expired_required_document",
        "unverified": "pending_document_verification",
    }

    @staticmethod
    def _norm(v: Any) -> str:
        return str(v or "").strip().lower()

    @classmethod
    def _is_driver(cls, position_category: Optional[str]) -> bool:
        return cls._norm(position_category) == "driver"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _severity_from_criticality(criticality: str) -> str:
        raw = "critical" if criticality in {"work_blocking", "compliance_critical"} else "high"
        return ReferenceServiceFacade.normalize_reference_code(domain="risk_severities", value=raw)

    @staticmethod
    def _severity_for_unverified(criticality: str) -> str:
        raw = "high" if criticality in {"work_blocking", "compliance_critical"} else "medium"
        return ReferenceServiceFacade.normalize_reference_code(domain="risk_severities", value=raw)

    @staticmethod
    def _resolution_action(kind: str) -> str:
        # Canonical operational action taxonomy (REF-1C consumer).
        raw = "upload_document" if kind == "missing" else "renew_document"
        return ReferenceServiceFacade.normalize_reference_code(domain="next_actions", value=raw)

    @staticmethod
    def _domain_for_document(code: str) -> str:
        c = str(code or "").strip().lower()
        if c in {"passport", "id_card"}:
            return "identity"
        if c in {"residence_card", "visa"}:
            return "legal_stay"
        if c in {"work_permit"}:
            return "right_to_work"
        if c in {"driver_license", "code_95", "tachograph_card"}:
            return "driver_compliance"
        if c in {"medical_certificate", "psychotest"}:
            return "medical"
        if c in {"employment_contract", "civil_contract"}:
            return "hr_onboarding"
        if c in {"zus_zua", "zus_zza", "tax_declaration"}:
            return "payroll"
        if c in {"other"}:
            return ReferenceServiceFacade.normalize_reference_code(domain="compliance_domains", value="client_specific")
        return ReferenceServiceFacade.normalize_reference_code(domain="compliance_domains", value="operational")

    @classmethod
    def _affected_operations_for(cls, kind: str, domain: str) -> list[str]:
        base: list[str]
        if kind == "missing":
            base = [
                "submit_to_client",
                "handoff_to_hr",
                "sign_contract",
                "approve_hr_verification",
                "activate_employee",
                "start_work",
            ]
            if domain in {"driver_compliance", "medical", "right_to_work", "legal_stay"}:
                base.append("assign_route")
        elif kind == "expired":
            base = ["handoff_to_hr", "sign_contract", "assign_route", "activate_employee", "start_work"]
        else:
            base = ["approve_hr_verification", "activate_employee", "start_work"]
        return sorted({op for op in base if op in cls._OPS})

    @staticmethod
    def _impact_for(kind: str, domain: str) -> str:
        if kind == "missing":
            if domain in {"right_to_work", "legal_stay"}:
                return ReferenceServiceFacade.normalize_reference_code(domain="operational_impacts", value="legal_blocker")
            if domain in {"driver_compliance", "medical"}:
                return ReferenceServiceFacade.normalize_reference_code(domain="operational_impacts", value="dispatch_blocker")
            return ReferenceServiceFacade.normalize_reference_code(domain="operational_impacts", value="document_missing")
        if kind == "expired":
            if domain in {"right_to_work", "legal_stay"}:
                return ReferenceServiceFacade.normalize_reference_code(domain="operational_impacts", value="legal_blocker")
            if domain in {"driver_compliance", "medical"}:
                return ReferenceServiceFacade.normalize_reference_code(domain="operational_impacts", value="dispatch_blocker")
            return ReferenceServiceFacade.normalize_reference_code(domain="operational_impacts", value="compliance_risk")
        return ReferenceServiceFacade.normalize_reference_code(domain="operational_impacts", value="verification_pending")

    @classmethod
    def _build_blocker(
        cls,
        *,
        kind: str,
        severity: str,
        domain: str,
        source: str,
        document_code: str,
        reason: str,
    ) -> dict[str, Any]:
        code = cls._BLOCKER_CODES.get(kind, "pending_document_verification")
        affected = cls._affected_operations_for(kind, domain)
        resolution_action = (
            ReferenceServiceFacade.normalize_reference_code(domain="next_actions", value="verify_document")
            if kind == "unverified"
            else cls._resolution_action("missing" if kind == "missing" else "expired")
        )
        return {
            "code": code,
            "severity": ReferenceServiceFacade.normalize_reference_code(domain="risk_severities", value=severity),
            "domain": ReferenceServiceFacade.normalize_reference_code(domain="compliance_domains", value=domain),
            "source": source,
            "impact": cls._impact_for(kind, domain),
            "affected_operations": affected,
            "resolution_action": resolution_action,
            "document_code": document_code,
            "reason": reason,
            # backward-compat aliases
            "block_type": code,
            "affected_operation": affected,
            "legacy_resolution_action": (
                f"upload_{document_code}"
                if kind == "missing"
                else (f"upload_valid_{document_code}" if kind == "expired" else "verify_document")
            ),
        }

    @classmethod
    async def resolve(
        cls,
        db: AsyncSession,
        *,
        context: WorkforceEligibilityContext,
    ) -> dict[str, Any]:
        candidate_id = str(context.candidate_id or "").strip() or None
        employee_id = str(context.employee_id or "").strip() or None
        tenant_id = str(context.tenant_id).strip()

        if employee_id and not candidate_id:
            emp = await db.get(WorkforceEmployee, employee_id)
            if emp and emp.candidate_id:
                candidate_id = str(emp.candidate_id)

        if candidate_id and (not context.citizenship or not context.work_country or not context.position_category):
            cand = await db.get(Candidate, candidate_id)
            if cand is not None:
                extra = cand._get_extra() if hasattr(cand, "_get_extra") else {}
                personal = cand._get_personal_data() if hasattr(cand, "_get_personal_data") else {}
                if not context.citizenship:
                    context.citizenship = str(extra.get("citizenship") or personal.get("citizenship") or "").strip() or None
                if not context.work_country:
                    context.work_country = str(extra.get("work_country") or personal.get("work_country") or "").strip() or None
                if not context.position_category:
                    context.position_category = str(extra.get("position_category") or extra.get("profession_category") or "").strip() or None

        facade_ctx = ReferenceContext(
            tenant_id=tenant_id,
            module="hr",
            entity_type="employee" if employee_id else "candidate",
            entity_id=employee_id or candidate_id,
            candidate_id=candidate_id,
            employee_id=employee_id,
            citizenship=context.citizenship,
            work_country=context.work_country,
            residence_status=context.residence_status,
            position_category=context.position_category,
            employment_type=context.employment_type,
            stage=context.stage,
            client_id=context.client_id,
            vacancy_id=context.vacancy_id,
        )

        expected = await ReferenceServiceFacade.get_applicable_documents(
            db,
            context=facade_ctx,
        )

        docs: list[Document] = []
        if candidate_id:
            docs = (
                await db.execute(
                    select(Document).where(
                        Document.tenant_id == tenant_id,
                        Document.candidate_id == candidate_id,
                        Document.deleted_at.is_(None),
                    )
                )
            ).scalars().all()

        today = date.today()
        present_by_code: dict[str, list[Document]] = {}
        document_expiry_evaluations = []
        for d in docs:
            runtime_profile = await ReferenceServiceFacade.get_document_runtime_profile(
                db,
                document=d,
                context=facade_ctx,
            )
            profile = runtime_profile.get("profile") or {}
            canonical_code = str(profile.get("canonical_code") or "").strip()
            expiry_rules = dict(profile.get("expiry_rules") or {})
            requires_expiry = bool(expiry_rules.get("expiry_required") or expiry_rules.get("has_expiry"))
            renewal_window = int(expiry_rules.get("renewal_window_days") or 30)
            document_expiry_evaluations.append(
                evaluate_document_expiry(
                    expires_on=getattr(d, "expire_date", None),
                    expiry_required=requires_expiry,
                    reference_date=today,
                    expiring_soon_days=renewal_window,
                )
            )
            if canonical_code:
                present_by_code.setdefault(canonical_code, []).append(d)

        missing_documents: list[str] = []
        expired_documents: list[str] = []
        pending_verification_documents: list[str] = []
        soon_expiring_documents: list[dict[str, Any]] = []
        warnings: list[str] = []
        blocking_reasons: list[dict[str, Any]] = []

        for row in expected:
            code = str(row.get("document_code") or "")
            required = bool(row.get("required"))
            criticality = cls._norm(row.get("criticality")) or "informational"
            matches = present_by_code.get(code, [])

            if not matches:
                if required:
                    missing_documents.append(code)
                    sev = cls._severity_from_criticality(criticality)
                    domain = cls._domain_for_document(code)
                    blocking_reasons.append(
                        cls._build_blocker(
                            kind="missing",
                            severity=sev,
                            domain=domain,
                            source=f"pack:{row.get('source_pack')}",
                            document_code=code,
                            reason=f"Required document '{code}' is missing.",
                        )
                    )
                continue

            has_valid = False
            has_verified = False
            expiry_rules = dict(row.get("expiry_rules") or {})
            requires_expiry = bool(expiry_rules.get("expiry_required") or expiry_rules.get("has_expiry"))
            renewal_window = int(expiry_rules.get("renewal_window_days") or 30)
            for d in matches:
                st_raw = getattr(d, "status", "")
                if hasattr(st_raw, "value"):
                    st_raw = st_raw.value
                st = cls._norm(st_raw)
                evaluation = evaluate_document_expiry(
                    expires_on=getattr(d, "expire_date", None),
                    expiry_required=requires_expiry,
                    reference_date=today,
                    expiring_soon_days=renewal_window,
                )
                if evaluation.state in {"expired", "missing_expiry"}:
                    continue
                has_valid = True
                if st in cls._VERIFIED_STATUSES:
                    has_verified = True
                if evaluation.state == "expiring_soon" and evaluation.days_left is not None:
                    days = evaluation.days_left
                    soon_expiring_documents.append({"document_code": code, "days": days})
                    if days <= 7:
                        warnings.append(f"{code}_expires_in_7_days")
                    elif days <= 14:
                        warnings.append(f"{code}_expires_in_14_days")
                    else:
                        warnings.append(f"{code}_expires_in_30_days")

            if not has_valid:
                expired_documents.append(code)
                sev = cls._severity_from_criticality(criticality)
                domain = cls._domain_for_document(code)
                blocking_reasons.append(
                    cls._build_blocker(
                        kind="expired",
                        severity=sev,
                        domain=domain,
                        source=f"pack:{row.get('source_pack')}",
                        document_code=code,
                        reason=f"Required document '{code}' is expired.",
                    )
                )
                continue

            if required and not has_verified:
                pending_verification_documents.append(code)
                domain = cls._domain_for_document(code)
                blocking_reasons.append(
                    cls._build_blocker(
                        kind="unverified",
                        severity=cls._severity_for_unverified(criticality),
                        domain=domain,
                        source=f"pack:{row.get('source_pack')}",
                        document_code=code,
                        reason=f"Required document '{code}' is not verified yet.",
                    )
                )

        domains = {
            "legal_stay": "compliant",
            "right_to_work": "compliant",
            "identity": "compliant",
            "driver_compliance": "compliant",
            "medical": "compliant",
            "hr_onboarding": "compliant",
            "payroll": "compliant",
            "client_specific": "compliant",
            "operational": "compliant",
        }

        for b in blocking_reasons:
            domain = cls._norm(b.get("domain"))
            if domain in domains:
                domains[domain] = ReferenceServiceFacade.normalize_reference_code(
                    domain="operational_statuses",
                    value="blocked",
                )
            domains["operational"] = "blocked"

        if blocking_reasons:
            critical_blocks = [b for b in blocking_reasons if cls._norm(b.get("severity")) == "critical"]
            if expired_documents and critical_blocks:
                eligibility_status = "expired_critical_documents"
            elif pending_verification_documents and not missing_documents and not expired_documents:
                eligibility_status = "pending_verification"
            elif any(cls._norm(b.get("code")) == "missing_required_document" for b in blocking_reasons):
                eligibility_status = "pending_documents"
            elif warnings:
                eligibility_status = "conditionally_eligible"
            else:
                eligibility_status = "blocked"
        elif warnings:
            eligibility_status = "compliance_risk"
        else:
            eligibility_status = "eligible"

        allowed_operations = {op: True for op in cls._OPS}
        for b in blocking_reasons:
            for op in b.get("affected_operations") or []:
                allowed_operations[str(op)] = False

        # Driver-only operation tightening.
        if cls._is_driver(context.position_category) and domains["driver_compliance"] == "blocked":
            allowed_operations["assign_route"] = False

        allowed_operations["payroll_ready"] = bool(
            allowed_operations["activate_employee"] and domains["payroll"] != "blocked"
        )

        # Backward compatibility aliases.
        for legacy, canonical in cls._OP_ALIASES.items():
            allowed_operations[legacy] = bool(allowed_operations.get(canonical, True))

        def _profile(allowed: bool, domain: str, profile_ops: list[str]) -> dict[str, Any]:
            prof_blockers = [b for b in blocking_reasons if domain == "operational" or cls._norm(b.get("domain")) == domain]
            prof_missing = [m for m in missing_documents if cls._domain_for_document(m) == domain or domain == "operational"]
            prof_warn = [w for w in warnings if domain == "operational" or domain.split("_")[0] in w]
            status = "ready" if allowed and not prof_blockers else ("warning" if allowed and prof_warn else "blocked")
            affected_ops = sorted(
                {
                    str(op)
                    for b in prof_blockers
                    for op in (b.get("affected_operations") or [])
                    if str(op).strip()
                }
            )
            if not affected_ops:
                affected_ops = sorted({str(op) for op in profile_ops if str(op).strip()})
            next_actions = sorted(
                {
                    str(b.get("resolution_action") or "")
                    for b in prof_blockers
                    if str(b.get("resolution_action") or "").strip()
                }
            )
            return {
                "status": status,
                "blockers": prof_blockers,
                "warnings": prof_warn,
                "missing_requirements": prof_missing,
                "affected_operations": affected_ops,
                "next_actions": next_actions,
            }

        readiness_profiles = {
            "recruitment_ready": _profile(
                bool(allowed_operations["submit_to_client"]),
                "operational",
                ["submit_to_client", "handoff_to_hr"],
            ),
            "client_ready": _profile(
                bool(allowed_operations["submit_to_client"]),
                "client_specific",
                ["submit_to_client"],
            ),
            "hr_ready": _profile(
                bool(allowed_operations["handoff_to_hr"]),
                "hr_onboarding",
                ["handoff_to_hr", "approve_hr_verification"],
            ),
            "employment_ready": _profile(
                bool(allowed_operations["sign_contract"]),
                "right_to_work",
                ["sign_contract", "activate_employee", "start_work"],
            ),
            "route_ready": _profile(
                bool(allowed_operations["assign_route"]),
                "driver_compliance",
                ["assign_route", "start_work"],
            ),
            "payroll_ready": _profile(
                bool(allowed_operations["payroll_ready"]),
                "payroll",
                ["payroll_ready"],
            ),
        }

        next_required_actions = [
            str(b.get("resolution_action") or "")
            for b in blocking_reasons
            if b.get("resolution_action")
        ]

        subject_type = "employee" if employee_id else "candidate"
        subject_id = employee_id or candidate_id or ""

        if eligibility_status == "eligible":
            compliance_status = "compliant"
        elif eligibility_status in {"compliance_risk", "conditionally_eligible", "pending_verification"}:
            compliance_status = "partially_compliant"
        else:
            compliance_status = "blocked"

        return {
            "subject_type": subject_type,
            "subject_id": subject_id,
            "eligibility_status": eligibility_status,
            "compliance_status": compliance_status,
            "readiness_profiles": readiness_profiles,
            "allowed_operations": allowed_operations,
            "blocking_reasons": blocking_reasons,
            "warnings": sorted(set(warnings)),
            "missing_documents": sorted(set(missing_documents)),
            "expired_documents": sorted(set(expired_documents)),
            "pending_verification_documents": sorted(set(pending_verification_documents)),
            "soon_expiring_documents": soon_expiring_documents,
            "expiry": owner_expiry_aggregate_to_dict(
                aggregate_document_expiry_states(document_expiry_evaluations)
            ),
            "next_required_actions": next_required_actions,
            "compliance_domains": domains,
            "source_context": {
                "tenant_id": tenant_id,
                "candidate_id": candidate_id,
                "employee_id": employee_id,
                "citizenship": context.citizenship,
                "work_country": context.work_country,
                "residence_status": context.residence_status,
                "position_category": context.position_category,
                "employment_type": context.employment_type,
                "stage": context.stage,
                "client_id": context.client_id,
                "vacancy_id": context.vacancy_id,
            },
            "calculated_at": cls._now_iso(),
            "expected_documents_count": len(expected),
        }
