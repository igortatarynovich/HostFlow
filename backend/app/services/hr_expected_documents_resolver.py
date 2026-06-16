from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.document_policy import DocumentPolicy, RequirementLevel
from backend.app.models.ref_document_type import RefDocumentType, RefDocumentTypeI18n, RefDocumentTypeVersion
from backend.app.services.document_applicability_resolver import (
    DocumentApplicabilityContext,
    DocumentApplicabilityResolver,
)
from backend.app.services.hr_expected_documents import load_hr_expected_documents


def _norm(x: Any) -> str:
    return str(x or "").strip().lower()


def _owner_for_group(group: str) -> str:
    g = _norm(group)
    if g in ("identity",):
        return "Recruiter"
    if g in ("work_authorization", "work_auth"):
        return "External legal"
    if g in ("driver", "medical"):
        return "Employee"
    if g in ("employment", "social_security", "tax"):
        return "HR"
    return "HR"


def _group_for_ref(dt: RefDocumentType) -> str:
    g = _norm(getattr(dt, "category_code", None))
    if g in ("work_authorization",):
        return "work_auth"
    if g in ("driver_compliance",):
        return "driver"
    if g in ("occupational_health",):
        return "medical"
    if g in ("social_security", "tax"):
        return "employment"
    if g in ("identity", "employment", "medical", "driver", "work_auth"):
        return g
    return "other"


def _applies_to_context(*, position_category: str | None, group: str) -> tuple[bool, bool]:
    pos = _norm(position_category)
    is_driver = "driver" in pos
    g = _norm(group)
    if g == "driver":
        return True, False
    if g == "other":
        return True, True
    return True, True if not is_driver else True


async def expected_docs_for_employee(
    db: AsyncSession,
    *,
    tenant_id: str,
    vacancy_id: str | None,
    company_id: str | None,
    work_country: str | None,
    citizenship: str | None,
    position_category: str | None,
) -> list[dict[str, Any]]:
    """Resolve expected document rows from system dictionaries + policies, with JSON fallback."""
    tid = str(tenant_id).strip()

    m4 = await DocumentApplicabilityResolver.resolve_expected_documents(
        db,
        context=DocumentApplicabilityContext(
            tenant_id=tid,
            citizenship=citizenship,
            work_country=work_country,
            position_category=position_category,
            employment_type=None,
            stage="hr",
            client_id=company_id,
            vacancy_id=vacancy_id,
        ),
    )
    if m4:
        out: list[dict[str, Any]] = []
        for row in m4:
            g = _norm(row.get("group"))
            applies_driver, applies_non_driver = _applies_to_context(position_category=position_category, group=g)
            out.append(
                {
                    "document_code": str(row.get("document_code") or ""),
                    "label": str(row.get("label") or ""),
                    "group": g or "other",
                    "default_owner": _owner_for_group(g),
                    "requires_expiry": bool((row.get("expiry_rules") or {}).get("expiry_required") or (row.get("expiry_rules") or {}).get("has_expiry")),
                    "verification_required": bool((row.get("verification_profile") or {}).get("manual_review_required", True)),
                    "applies_to_driver": applies_driver,
                    "applies_to_non_driver": applies_non_driver,
                    "blocks_employment": bool(row.get("required")),
                    "renewal_window_days": int((row.get("expiry_rules") or {}).get("renewal_window_days") or 30),
                    "default_next_action": str(row.get("due_point") or "before_employment"),
                    "aliases": [str(row.get("document_code") or "")],
                    "source": "packs",
                    "source_pack": row.get("source_pack"),
                    "reason": row.get("reason"),
                    "criticality": row.get("criticality"),
                    "tenant_override_changed": bool(row.get("tenant_override_changed")),
                    "context": {
                        "work_country": work_country,
                        "citizenship": citizenship,
                    },
                }
            )
        return out

    today = date.today()

    # Active ref types (dictionary foundation).
    dt_rows = (
        await db.execute(
            select(RefDocumentType).where(
                RefDocumentType.status.in_(("active", "published", "draft"))
            )
        )
    ).scalars().all()
    if not dt_rows:
        return load_hr_expected_documents()

    dt_by_id = {str(x.id): x for x in dt_rows}

    ver_rows = (
        await db.execute(
            select(RefDocumentTypeVersion).where(
                RefDocumentTypeVersion.document_type_id.in_(list(dt_by_id.keys())),
                or_(RefDocumentTypeVersion.valid_to.is_(None), RefDocumentTypeVersion.valid_to >= today),
            )
        )
    ).scalars().all()
    ver_by_doc: dict[str, RefDocumentTypeVersion] = {}
    for v in ver_rows:
        did = str(v.document_type_id)
        cur = ver_by_doc.get(did)
        if cur is None or str(v.version_code or "") > str(cur.version_code or ""):
            ver_by_doc[did] = v

    i18n_rows = (
        await db.execute(
            select(RefDocumentTypeI18n).where(RefDocumentTypeI18n.document_type_id.in_(list(dt_by_id.keys())))
        )
    ).scalars().all()
    aliases_by_doc: dict[str, list[str]] = {}
    for r in i18n_rows:
        did = str(r.document_type_id)
        aliases_by_doc.setdefault(did, [])
        for a in (r.aliases or []):
            aa = _norm(a)
            if aa and aa not in aliases_by_doc[did]:
                aliases_by_doc[did].append(aa)

    # Policy layer (tenant/client/vacancy required-ness).
    pol_rows = (
        await db.execute(
            select(DocumentPolicy).where(
                DocumentPolicy.tenant_id == tid,
                DocumentPolicy.enabled.is_(True),
                DocumentPolicy.ref_document_type_id.is_not(None),
                DocumentPolicy.required_level != RequirementLevel.DISABLED,
                or_(
                    and_(DocumentPolicy.scope == "tenant", DocumentPolicy.scope_id.is_(None)),
                    and_(DocumentPolicy.scope == "client", DocumentPolicy.scope_id == (company_id or "")),
                    and_(DocumentPolicy.scope == "vacancy", DocumentPolicy.scope_id == (vacancy_id or "")),
                ),
            )
        )
    ).scalars().all()

    policy_level_by_doc: dict[str, str] = {}
    scope_rank = {"tenant": 1, "client": 2, "vacancy": 3}
    for p in pol_rows:
        did = str(p.ref_document_type_id or "").strip()
        if not did:
            continue
        cur = policy_level_by_doc.get(did)
        incoming = f"{scope_rank.get(str(p.scope), 0)}:{str(p.required_level)}"
        if cur is None or incoming > cur:
            policy_level_by_doc[did] = incoming

    out: list[dict[str, Any]] = []
    for did, dt in dt_by_id.items():
        code = _norm(dt.code)
        label = str(dt.public_name or dt.code or "").strip()
        group = _group_for_ref(dt)
        applies_driver, applies_non_driver = _applies_to_context(
            position_category=position_category, group=group
        )
        ver = ver_by_doc.get(did)
        expiry_rules = ver.expiry_rules_json if ver is not None and isinstance(ver.expiry_rules_json, dict) else {}
        verification_profile = (
            ver.verification_profile_json
            if ver is not None and isinstance(ver.verification_profile_json, dict)
            else {}
        )
        rule = policy_level_by_doc.get(did, "")
        required_level = rule.split(":", 1)[1] if ":" in rule else "required"
        blocks = required_level in ("required", "blocking")
        renewal_days = int(expiry_rules.get("renewal_window_days") or 30)
        requires_expiry = bool(expiry_rules.get("expiry_required") or expiry_rules.get("has_expiry"))
        default_action = "Request upload" if blocks else "Verify"
        if group == "work_auth":
            default_action = "Start permit process"

        out.append(
            {
                "document_code": code,
                "label": label,
                "group": group,
                "default_owner": _owner_for_group(group),
                "requires_expiry": requires_expiry,
                "verification_required": bool(verification_profile.get("manual_review_required", True)),
                "applies_to_driver": applies_driver,
                "applies_to_non_driver": applies_non_driver,
                "blocks_employment": blocks,
                "renewal_window_days": renewal_days,
                "default_next_action": default_action,
                "aliases": sorted(set([code, *aliases_by_doc.get(did, [])])),
                "source": "dictionaries",
                "context": {
                    "work_country": work_country,
                    "citizenship": citizenship,
                    "required_level": required_level,
                },
            }
        )

    if not out:
        return load_hr_expected_documents()
    return out
