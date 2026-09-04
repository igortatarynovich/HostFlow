from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from backend.app.reference.requirement_policy_consumer_parity import r5_required_set


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _ctx_value(ctx: dict[str, Any], *keys: str) -> str:
    for key in keys:
        raw = ctx.get(key)
        if raw not in (None, ""):
            return _norm(raw)
    return ""


def _ctx_tenant_delta(ctx: dict[str, Any]):
    raw = ctx.get("tenant_delta")
    return raw if isinstance(raw, dict) else None


@dataclass(frozen=True)
class DocumentPackDefinition:
    code: str
    label: str
    document_codes: tuple[str, ...]
    ref_pack_codes: tuple[str, ...]
    applies: Callable[[dict[str, Any]], bool]
    skeleton: bool = False


def _driver_pack_applies(ctx: dict[str, Any]) -> bool:
    return _ctx_value(ctx, "position_category", "role", "profession_category") == "driver"


def _legal_stay_pack_applies(ctx: dict[str, Any]) -> bool:
    return bool(_ctx_value(ctx, "citizenship")) or bool(_ctx_value(ctx, "residency_status"))


def _employment_pack_applies(ctx: dict[str, Any]) -> bool:
    stage = _ctx_value(ctx, "stage")
    if stage in {"employment", "onboarding", "hr", "employee", "active"}:
        return True
    if _ctx_value(ctx, "employee_id"):
        return True
    return True


def _client_pack_applies(_ctx: dict[str, Any]) -> bool:
    return True


DOCUMENT_PACK_DEFINITIONS: tuple[DocumentPackDefinition, ...] = (
    DocumentPackDefinition(
        code="driver_pack",
        label="Driver Pack",
        document_codes=(
            "driver_license",
            "driver_qualification_card",
            "tachograph_card",
            "medical_certificate",
            "psychological_certificate",
        ),
        ref_pack_codes=("pl_transport_driver", "eu_driver_compliance"),
        applies=_driver_pack_applies,
    ),
    DocumentPackDefinition(
        code="legal_stay_pack",
        label="Legal Stay Pack",
        document_codes=(
            "passport",
            "national_identity_card",
            "residence_card",
            "visa",
            "work_permit",
        ),
        ref_pack_codes=("pl_non_eu_worker", "pl_base_hr"),
        applies=_legal_stay_pack_applies,
    ),
    DocumentPackDefinition(
        code="employment_pack",
        label="Employment Pack",
        document_codes=(
            "employment_contract",
            "civil_contract",
            "zus_zua",
            "zus_zza",
            "tax_declaration",
        ),
        ref_pack_codes=("pl_base_hr",),
        applies=_employment_pack_applies,
    ),
    DocumentPackDefinition(
        code="client_pack",
        label="Client Pack",
        document_codes=("other",),
        ref_pack_codes=("client_specific_requirements",),
        applies=_client_pack_applies,
        skeleton=True,
    ),
)


def get_pack_definition(code: str) -> Optional[DocumentPackDefinition]:
    target = _norm(code)
    for pack in DOCUMENT_PACK_DEFINITIONS:
        if pack.code == target:
            return pack
    return None


def required_codes_for_pack(pack: DocumentPackDefinition, ctx: dict[str, Any]) -> tuple[str, ...]:
    """Grouping ∩ R5 required-set. Packs do not invent policy required codes."""
    if pack.skeleton:
        return ()
    if not pack.applies(ctx):
        return ()
    r5 = r5_required_set(ctx, _ctx_tenant_delta(ctx))
    return tuple(code for code in pack.document_codes if code in r5)
