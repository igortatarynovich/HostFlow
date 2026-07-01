from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, FrozenSet, Optional

from backend.app.services.document_applicability_policy import derive_document_applicability_decision

# Module-owned baseline sets for applicability policy (no platform reference imports).
_DEFAULT_EU_COUNTRIES: FrozenSet[str] = frozenset(
    {
        "at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr", "hu", "ie",
        "it", "lv", "lt", "lu", "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se",
    }
)
_DEFAULT_OSWIADCZENIE_COUNTRIES: FrozenSet[str] = frozenset({"ua", "by", "md", "ge"})


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _ctx_value(ctx: dict[str, Any], *keys: str) -> str:
    for key in keys:
        raw = ctx.get(key)
        if raw not in (None, ""):
            return _norm(raw)
    return ""


def _applicability_decision(ctx: dict[str, Any]):
    return derive_document_applicability_decision(
        citizenship=_ctx_value(ctx, "citizenship"),
        work_country=_ctx_value(ctx, "work_country") or "pl",
        role=_ctx_value(ctx, "position_category", "role", "profession_category"),
        eu_countries=set(_DEFAULT_EU_COUNTRIES),
        oswiadczenie_countries=set(_DEFAULT_OSWIADCZENIE_COUNTRIES),
    )


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
    # Pack projection is always available; required codes are filtered by module policy.
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


def _legal_stay_required_codes(ctx: dict[str, Any], base_codes: tuple[str, ...]) -> tuple[str, ...]:
    decision = _applicability_decision(ctx)
    citizenship = _ctx_value(ctx, "citizenship")
    codes = list(base_codes)
    if citizenship in _DEFAULT_EU_COUNTRIES:
        codes = [c for c in codes if c not in {"work_permit", "visa", "residence_card"}]
    elif not decision.visa_required:
        codes = [c for c in codes if c != "visa"]
    return tuple(codes)


DOCUMENT_PACK_DEFINITIONS: tuple[DocumentPackDefinition, ...] = (
    DocumentPackDefinition(
        code="driver_pack",
        label="Driver Pack",
        document_codes=(
            "driver_license",
            "code_95",
            "tachograph_card",
            "medical_certificate",
            "psychotest",
        ),
        ref_pack_codes=("pl_transport_driver", "eu_driver_compliance"),
        applies=_driver_pack_applies,
    ),
    DocumentPackDefinition(
        code="legal_stay_pack",
        label="Legal Stay Pack",
        document_codes=(
            "passport",
            "id_card",
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
    if pack.skeleton:
        return ()
    if not pack.applies(ctx):
        return ()
    if pack.code == "legal_stay_pack":
        return _legal_stay_required_codes(ctx, pack.document_codes)
    return pack.document_codes
