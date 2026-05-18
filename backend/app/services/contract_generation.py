"""HR contract generation MVP — draft/preview via trusted identity only (PR9)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.document_merge.generate import generate_merge_document
from backend.app.services.document_merge.render import _PLACEHOLDER_RE
from backend.app.services.document_merge.templates_repo import get_template, resolve_template_for_scope
from backend.app.services.employment_identity_read_adapter import TrustedIdentityAccessError
from backend.app.services.workforce_downstream_identity import (
    CONSUMER_CONTRACT_GENERATION,
    evaluate_contract_merge_identity,
)

GENERATION_KIND_CONTRACT_DRAFT_PREVIEW = "contract_draft_preview"
LOG_STATUS_DRAFT_PREVIEW = "draft_preview"

# Contract templates must not read legal identity from recruitment candidate context.
_FORBIDDEN_PLACEHOLDER_PREFIXES: tuple[str, ...] = (
    "candidate.",
    "employee.display_name",
    "employee.",
)

_TRUSTED_IDENTITY_PREFIX = "trusted_identity."


def extract_merge_placeholders(text: str) -> list[str]:
    return [m.strip() for m in _PLACEHOLDER_RE.findall(text or "") if m.strip()]


def validate_contract_template_placeholders(*texts: str) -> list[str]:
    """Return list of forbidden placeholder keys found in template bodies."""
    violations: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for key in extract_merge_placeholders(text):
            if key in seen:
                continue
            seen.add(key)
            if key.startswith(_TRUSTED_IDENTITY_PREFIX):
                continue
            for prefix in _FORBIDDEN_PLACEHOLDER_PREFIXES:
                if key == prefix.rstrip(".") or key.startswith(prefix):
                    violations.append(key)
                    break
            # Bare legacy keys at bindings root (legal_name without namespace) — disallow in templates
            if key in {
                "legal_name",
                "legal_first_name",
                "legal_last_name",
                "pesel",
                "citizenship",
                "passport_number",
                "permit_type",
                "permit_expiry",
            }:
                violations.append(key)
    return violations


def _sanitize_extra_bindings(extra: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not extra:
        return {}
    out: dict[str, Any] = {}
    for k, v in extra.items():
        key = str(k or "").strip()
        if not key:
            continue
        if key.startswith(_TRUSTED_IDENTITY_PREFIX) or key in {
            "legal_name",
            "pesel",
            "citizenship",
            "permit_type",
            "permit_expiry",
        }:
            raise ValueError("CONTRACT_TEMPLATE_IDENTITY_OVERRIDE_FORBIDDEN")
        out[key] = v
    return out


async def assert_contract_generation_allowed(
    db: AsyncSession, tenant_id: str, employee_id: str
) -> dict[str, Any]:
    """Enforce contract_generation consumer guard; return trusted bindings on success."""
    prep = await evaluate_contract_merge_identity(db, tenant_id, employee_id)
    if prep.blocked:
        raise TrustedIdentityAccessError(
            code=str(prep.block_code or "TRUSTED_IDENTITY_DENIED"),
            consumer=CONSUMER_CONTRACT_GENERATION,
            projection_status=str(prep.projection_status or ""),
            review_id=str(prep.review_id or ""),
            message=prep.message or "Trusted employment identity not available for contract generation",
            details={
                "missing_required": [],
                "conflicts": [],
            },
        )
    return dict(prep.bindings)


async def generate_contract_draft_preview(
    db: AsyncSession,
    tenant_id: str,
    *,
    employee_id: str,
    template_id: Optional[str] = None,
    template_code: Optional[str] = None,
    variable_bindings: Optional[dict[str, Any]] = None,
    triggered_by_user_id: Optional[str] = None,
) -> tuple[Any, Any, dict[str, Any]]:
    """
    Generate a draft/preview contract document for a workforce employee.

    - Requires trusted identity (contract_generation consumer).
    - Template must use ``trusted_identity.*`` for person/legal fields (no candidate snapshot).
    - Does not send, sign, or integrate with ePUAP.
    """
    from backend.app.services import workforce_employees as we_svc

    emp = await we_svc.get_employee(db, tenant_id, employee_id)
    if not emp:
        raise ValueError("EMPLOYEE_NOT_FOUND")
    if not emp.candidate_id:
        raise ValueError("EMPLOYEE_CANDIDATE_REQUIRED_FOR_DOCUMENT")

    trusted_bindings = await assert_contract_generation_allowed(db, tenant_id, employee_id)

    template = None
    if template_id:
        template = await get_template(db, tenant_id, template_id)
    elif template_code:
        template = await resolve_template_for_scope(
            db, tenant_id, template_code.strip(), own_company_id=emp.own_company_id
        )
    if template is None:
        raise ValueError("template_not_found")

    violations = validate_contract_template_placeholders(
        template.body_text or "",
        template.output_filename_pattern or "",
    )
    if violations:
        raise ValueError(f"CONTRACT_TEMPLATE_UNTRUSTED_PLACEHOLDERS:{','.join(violations[:8])}")

    safe_extra = _sanitize_extra_bindings(variable_bindings)

    log, doc = await generate_merge_document(
        db,
        tenant_id,
        template_id=template.id,
        workforce_employee_id=employee_id,
        candidate_id=str(emp.candidate_id) if emp.candidate_id else None,
        variable_bindings=safe_extra,
        triggered_by_user_id=triggered_by_user_id,
        generation_kind=GENERATION_KIND_CONTRACT_DRAFT_PREVIEW,
        trusted_identity_bindings=trusted_bindings,
    )

    meta = {
        "generation_kind": GENERATION_KIND_CONTRACT_DRAFT_PREVIEW,
        "consumer": CONSUMER_CONTRACT_GENERATION,
        "trusted_identity_bindings": trusted_bindings,
        "automation": {
            "send": False,
            "sign": False,
            "epuap": False,
        },
    }
    return log, doc, meta
