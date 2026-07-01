from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document import Document
from backend.app.models.ref_document_type import (
    RefDocumentType,
    RefDocumentTypeVersion,
    RefPack,
    RefPackItem,
    RefPackRule,
    TenantDocumentPackEnablement,
    TenantDocumentTypeOverride,
)
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.services.document_expiry_engine import evaluate_document_expiry
from backend.app.services.document_type_runtime_resolver import DocumentTypeRuntimeResolver


@dataclass
class DocumentApplicabilityContext:
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


class DocumentApplicabilityResolver:
    """Resolves expected documents from enabled packs with safe fallback behavior."""

    @staticmethod
    def _norm(v: Any) -> str:
        return str(v or "").strip().lower()

    @classmethod
    def _citizenship_group(cls, citizenship: Optional[str]) -> str:
        eu = {
            "at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr", "hu", "ie",
            "it", "lv", "lt", "lu", "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se",
        }
        cc = cls._norm(citizenship)
        if cc in eu:
            return "eu"
        if cc:
            return "non_eu"
        return "unknown"

    @classmethod
    def _matches(cls, cond: dict[str, Any], ctx: DocumentApplicabilityContext) -> bool:
        if not cond:
            return True
        for key, value in cond.items():
            if value in (None, "", [], {}):
                continue
            actual = {
                "work_country": cls._norm(ctx.work_country),
                "citizenship_group": cls._citizenship_group(ctx.citizenship),
                "position_category": cls._norm(ctx.position_category),
                "employment_type": cls._norm(ctx.employment_type),
                "stage": cls._norm(ctx.stage),
            }.get(key, "")
            if isinstance(value, list):
                if actual not in {cls._norm(v) for v in value}:
                    return False
            else:
                if actual != cls._norm(value):
                    return False
        return True

    @classmethod
    async def resolve_expected_documents(
        cls,
        db: AsyncSession,
        *,
        context: DocumentApplicabilityContext,
    ) -> list[dict[str, Any]]:
        tid = str(context.tenant_id).strip()
        q = (
            select(TenantDocumentPackEnablement, RefPack)
            .join(RefPack, RefPack.id == TenantDocumentPackEnablement.pack_id)
            .where(TenantDocumentPackEnablement.tenant_id == tid)
            .where(TenantDocumentPackEnablement.enabled.is_(True))
            .where(RefPack.status == "active")
        )
        enabled = (await db.execute(q)).all()
        if not enabled:
            return []

        pack_ids = [str(p.id) for _, p in enabled]
        pack_by_id = {str(p.id): p for _, p in enabled}

        items = (
            await db.execute(
                select(RefPackItem, RefDocumentTypeVersion, RefDocumentType)
                .join(RefDocumentTypeVersion, RefDocumentTypeVersion.id == RefPackItem.document_type_version_id)
                .join(RefDocumentType, RefDocumentType.id == RefDocumentTypeVersion.document_type_id)
                .where(RefPackItem.pack_id.in_(pack_ids))
            )
        ).all()

        rules = (
            await db.execute(select(RefPackRule).where(RefPackRule.pack_id.in_(pack_ids)).order_by(RefPackRule.priority.asc()))
        ).scalars().all()
        rules_by_pack: dict[str, list[RefPackRule]] = {}
        for r in rules:
            rules_by_pack.setdefault(str(r.pack_id), []).append(r)

        overrides = (
            await db.execute(select(TenantDocumentTypeOverride).where(TenantDocumentTypeOverride.tenant_id == tid))
        ).scalars().all()
        ov_by_doc_id = {str(o.document_type_id): o for o in overrides}

        out_by_code: dict[str, dict[str, Any]] = {}
        for item, ver, doc_type in items:
            pack = pack_by_id.get(str(item.pack_id))
            if not pack:
                continue

            required = cls._norm(item.role) == "required"
            due_point = "before_employment"
            reason = f"required by pack {pack.code}"
            criticality = str(doc_type.criticality or "informational")

            for rule in rules_by_pack.get(str(item.pack_id), []):
                cond = rule.condition_expr if isinstance(rule.condition_expr, dict) else {}
                if not cls._matches(cond, context):
                    continue
                eff = rule.effect_payload if isinstance(rule.effect_payload, dict) else {}
                if str(rule.effect_type or "") == "set_requirement":
                    if "required" in eff:
                        required = bool(eff.get("required"))
                    due_point = str(eff.get("due_point") or due_point)
                    reason = str(eff.get("reason") or reason)
                    if eff.get("criticality_override"):
                        criticality = str(eff.get("criticality_override"))

            override_changed = False
            ov = ov_by_doc_id.get(str(doc_type.id))
            if ov is not None:
                if ov.enabled is False:
                    if criticality in {"work_blocking", "compliance_critical"}:
                        pass
                    else:
                        continue
                lvl = cls._norm(ov.required_level)
                if lvl == "required" and not required:
                    required = True
                    override_changed = True
                if lvl in {"optional", "disabled"} and required:
                    if criticality not in {"work_blocking", "compliance_critical"}:
                        required = False
                        override_changed = True

            code = str(doc_type.code)
            prev = out_by_code.get(code)
            row = {
                "document_code": code,
                "label": str(doc_type.public_name or code),
                "group": str(doc_type.category_code or "other"),
                "required": required,
                "source_pack": str(pack.code),
                "reason": reason,
                "due_point": due_point,
                "criticality": criticality,
                "verification_profile": dict(ver.verification_profile_json or {}),
                "required_fields": list((ver.schema_json or {}).get("required") or []),
                "expiry_rules": dict(ver.expiry_rules_json or {}),
                "tenant_override_changed": override_changed,
                "document_type_id": str(doc_type.id),
                "document_type_version_id": str(ver.id),
            }
            if prev is None or (required and not bool(prev.get("required"))):
                out_by_code[code] = row

        out = list(out_by_code.values())

        # Optional status projection against live docs when candidate/employee context is provided.
        candidate_id = str(context.candidate_id or "").strip()
        if not candidate_id and context.employee_id:
            emp = await db.get(WorkforceEmployee, str(context.employee_id))
            if emp and emp.candidate_id:
                candidate_id = str(emp.candidate_id)

        docs: list[Document] = []
        if candidate_id:
            docs = (
                await db.execute(
                    select(Document).where(
                        Document.tenant_id == tid,
                        Document.candidate_id == candidate_id,
                        Document.deleted_at.is_(None),
                    )
                )
            ).scalars().all()

        if docs:
            by_code: dict[str, list[Document]] = {}
            for d in docs:
                rr = await DocumentTypeRuntimeResolver.resolve_for_document(db, d)
                by_code.setdefault(rr.canonical_code, []).append(d)

            today = date.today()
            for row in out:
                matches = by_code.get(str(row["document_code"]), [])
                if not matches:
                    row["status"] = "missing"
                    continue
                expired = False
                present = False
                expiry_rules = dict(row.get("expiry_rules") or {})
                requires_expiry = bool(expiry_rules.get("expiry_required") or expiry_rules.get("has_expiry"))
                renewal_window = int(expiry_rules.get("renewal_window_days") or 30)
                for d in matches:
                    evaluation = evaluate_document_expiry(
                        expires_on=getattr(d, "expire_date", None),
                        expiry_required=requires_expiry,
                        reference_date=today,
                        expiring_soon_days=renewal_window,
                    )
                    if evaluation.state in {"expired", "missing_expiry"}:
                        expired = True
                    else:
                        present = True
                row["status"] = "expired" if (expired and not present) else "present"
        else:
            for row in out:
                row["status"] = "missing"

        out.sort(key=lambda x: (not bool(x.get("required")), str(x.get("group") or ""), str(x.get("label") or "")))
        return out
