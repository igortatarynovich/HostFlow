"""Calculated HR verification plan — hybrid recommendation + hard legal blockers (PR13).

The plan is system-generated guidance for HR, not absolute truth. Recruitment supplies
the initial package; the system classifies tiers; HR makes the final legal/control decision.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.models.workforce_employee import WorkforceEmployee
from backend.app.models.workforce_hr_review import WorkforceHrReview
from backend.app.services.reference_service_facade import ReferenceContext, ReferenceServiceFacade
from backend.app.services.hr_review_document_resolution import DOC_KEY_CANDIDATE_TYPES
from backend.app.services.hr_verified_field_catalog import OPTIONAL_FILE_VERIFICATION_KEYS
from backend.app.services.hr_verification_requirements import (
    is_driver_position,
    resolve_position_category_for_review,
)
from backend.app.services.workforce_work_eligibility_journey import build_work_eligibility_journey

STEP_LEGAL_IDENTITY = "legal_identity"
STEP_LEGAL_STAY = "legal_stay_eligibility"
STEP_PROFESSIONAL = "professional_eligibility"
STEP_EMPLOYMENT = "employment_setup"

STEP_LABELS = {
    STEP_LEGAL_IDENTITY: "Legal identity",
    STEP_LEGAL_STAY: "Legal stay & work eligibility",
    STEP_PROFESSIONAL: "Professional eligibility",
    STEP_EMPLOYMENT: "Employment setup",
}

# Always included in HR dossier (not driven by document catalog alone).
_ALWAYS_INCLUDED_DATA_KEYS = frozenset({"Contacts & address", "Work experience"})

# Catalog doc types (ruleset) → HR verification document_key
CATALOG_TO_DOCUMENT_KEY: dict[str, str] = {}
for _key, _types in DOC_KEY_CANDIDATE_TYPES.items():
    for _t in _types:
        CATALOG_TO_DOCUMENT_KEY[_t] = _key
CATALOG_TO_DOCUMENT_KEY.update(
    {
        "identity_document": "Passport / ID",
        "passport_scan": "Passport / ID",
        "pesel": "Red paper",
        "qualification_code95": "Code95",
        "swiadectwo_kierowcy": "Driver license",
        "prawo_jazdy": "Driver license",
        "karta_tachografu": "Tacho card",
        "visa_d": "Legal stay",
        "visa": "Legal stay",
        "residence_card": "Legal stay",
        "karta_pobytu": "Legal stay",
        "oswiadczenie": "Work permit",
        "zezwolenie_a": "Work permit",
    }
)

# Explicit slot catalog for plan builder (order within step)
@dataclass(frozen=True)
class _SlotDef:
    document_key: str
    step_code: str
    step_order: int
    slot_order: int
    catalog_types: frozenset[str]
    journey_step: Optional[str] = None  # force required when journey step active


VERIFICATION_SLOT_DEFS: tuple[_SlotDef, ...] = (
    _SlotDef("Passport / ID", STEP_LEGAL_IDENTITY, 1, 1, frozenset({"passport", "national_id", "identity_document", "id_card", "identity_card", "passport_scan"})),
    _SlotDef(
        "Legal stay",
        STEP_LEGAL_STAY,
        2,
        1,
        frozenset({"legal_stay", "residence_permit", "residence_card", "karta_pobytu", "visa", "visa_d"}),
        "legal_stay",
    ),
    _SlotDef("Work permit", STEP_LEGAL_STAY, 2, 2, frozenset({"work_permit", "work_permit_application", "oswiadczenie", "zezwolenie_a"}), "work_permit"),
    _SlotDef("Red paper", STEP_LEGAL_STAY, 2, 3, frozenset({"red_paper", "red_paper_certificate", "pesel"}), "red_paper"),
    _SlotDef("Driver license", STEP_PROFESSIONAL, 3, 1, frozenset({"driver_license", "prawo_jazdy", "eu_driver_license", "swiadectwo_kierowcy"})),
    _SlotDef("Code95", STEP_PROFESSIONAL, 3, 2, frozenset({"code95", "qualification_code95", "code_95"})),
    _SlotDef("Tacho card", STEP_PROFESSIONAL, 3, 3, frozenset({"tacho_card", "tachograph_card", "karta_tachografu"})),
    _SlotDef("Medical", STEP_EMPLOYMENT, 4, 1, frozenset({"medical", "medical_certificate", "badania_lekarskie"})),
    _SlotDef("Psychological", STEP_EMPLOYMENT, 4, 2, frozenset({"psychological", "psychological_certificate", "psychotest"})),
    _SlotDef(
        "Contacts & address",
        STEP_LEGAL_IDENTITY,
        1,
        0,
        frozenset(),
    ),
    _SlotDef(
        "Work experience",
        STEP_EMPLOYMENT,
        4,
        0,
        frozenset({"employment_record", "swiadectwo_pracy", "work_certificate", "employment_history"}),
    ),
)

# Requirement tiers (hybrid model)
TIER_HARD_BLOCKER = "hard_blocker"
TIER_REQUIRED = "required"
TIER_RECOMMENDED = "recommended"
TIER_HR_REQUESTED = "hr_requested"
TIER_NOT_REQUIRED = "not_required"

_TIERS_IN_PLAN = frozenset({TIER_HARD_BLOCKER, TIER_REQUIRED, TIER_RECOMMENDED, TIER_HR_REQUESTED})
_TIERS_BLOCK_APPROVE = frozenset({TIER_HARD_BLOCKER, TIER_REQUIRED, TIER_HR_REQUESTED})
_TIERS_OVERRIDABLE = frozenset({TIER_REQUIRED, TIER_RECOMMENDED})

# Always required for HR identity step (minimum hire gate)
_ALWAYS_REQUIRED_KEYS = frozenset({"Passport / ID"})
_DRIVER_HARD_BLOCKER_KEYS = frozenset({"Driver license"})

# ISO 3166-1 alpha-2 — EU/EEA/CH (simplified gate for legal-stay expectations in plan context)
_EU_CITIZENSHIP_CODES = frozenset(
    {
        "at",
        "be",
        "bg",
        "hr",
        "cy",
        "cz",
        "dk",
        "ee",
        "fi",
        "fr",
        "de",
        "gr",
        "hu",
        "ie",
        "it",
        "lv",
        "lt",
        "lu",
        "mt",
        "nl",
        "pl",
        "pt",
        "ro",
        "sk",
        "si",
        "es",
        "se",
        "ch",
        "no",
        "is",
        "li",
    }
)


def _citizenship_code(raw: Any) -> Optional[str]:
    s = str(raw or "").strip().upper()
    if len(s) >= 2:
        return s[:2]
    return None


def _is_eu_citizen(citizenship: Any) -> Optional[bool]:
    code = _citizenship_code(citizenship)
    if not code:
        return None
    return code.lower() in _EU_CITIZENSHIP_CODES


def _journey_step_by_code(journey: dict[str, Any], code: str) -> Optional[dict[str, Any]]:
    for s in journey.get("steps") or []:
        if isinstance(s, dict) and str(s.get("code") or "") == code:
            return s
    return None


def _journey_requires_document(journey: dict[str, Any], step_code: str) -> bool:
    step = _journey_step_by_code(journey, step_code)
    if not step:
        return False
    st = str(step.get("status") or "").lower()
    if st in ("not_required", "done"):
        return False
    req = step.get("required_documents") or []
    return bool(req) or st in ("pending", "blocked", "needs_data")


def _vacancy_extra_dict(vacancy: Any) -> dict[str, Any]:
    """Parse Vacancy.extra (JSON string or dict) for ruleset / verification context."""
    raw = getattr(vacancy, "extra", None)
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(str(raw))
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


async def _build_ruleset_context(
    db: AsyncSession,
    tenant_id: str,
    *,
    candidate: Optional[Candidate],
    employee: Optional[WorkforceEmployee],
    vacancy: Optional[Vacancy],
) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    personal: dict[str, Any] = {}
    if candidate:
        extra = candidate._get_extra()
        personal = candidate._get_personal_data()
    snap = {}
    if employee and isinstance(employee.candidate_snapshot, dict):
        snap = employee.candidate_snapshot
    citizenship = (
        extra.get("citizenship")
        or personal.get("citizenship")
        or snap.get("citizenship")
    )
    legal_status = (
        extra.get("legal_status")
        or extra.get("poland_stay_basis")
        or personal.get("residency_status")
        or personal.get("legal_status")
    )
    profession = extra.get("role") or snap.get("role") or extra.get("profession")
    ctx: dict[str, Any] = {
        "candidate_id": str(candidate.id) if candidate else None,
        "citizenship": citizenship,
        "eu_citizen": _is_eu_citizen(citizenship),
        "legal_status": legal_status,
        "residency_status": extra.get("poland_stay_basis") or personal.get("residency_status"),
        "profession": profession,
        "has_adr": extra.get("has_adr"),
        "work_country": extra.get("work_country") or snap.get("work_country") or "PL",
        "documents": {
            k: bool(v)
            for k, v in (extra.get("documents") or {}).items()
            if isinstance(extra.get("documents"), dict) and isinstance(v, bool)
        }
        if isinstance(extra.get("documents"), dict)
        else {},
    }
    if vacancy:
        cat = None
        vac_extra = _vacancy_extra_dict(vacancy)
        if vac_extra.get("position_category"):
            cat = str(vac_extra.get("position_category"))
        elif vac_extra.get("category"):
            cat = str(vac_extra.get("category"))
        ctx["vacancy"] = {
            "id": str(vacancy.id),
            "title": getattr(vacancy, "title", None),
            "category": cat or ("driver" if is_driver_position(profession) else "non_driver"),
            "profession": vac_extra.get("profession") or vac_extra.get("position"),
            "contract_type": vac_extra.get("contract_type")
            or vac_extra.get("employment_type")
            or getattr(vacancy, "employment_type", None),
            "requires_driver_attestation": vac_extra.get("requires_driver_attestation"),
            "work_country": vac_extra.get("work_country") or vac_extra.get("country") or ctx.get("work_country"),
            "required_documents": vac_extra.get("required_documents"),
        }
    elif is_driver_position(extra.get("role") or snap.get("role")):
        ctx["vacancy"] = {"category": "driver"}
    else:
        ctx["vacancy"] = {"category": "non_driver"}
    return {k: v for k, v in ctx.items() if v is not None}


async def _resolve_expected_document_sets(
    db: AsyncSession,
    tenant_id: str,
    *,
    candidate: Optional[Candidate],
    owner_context: dict[str, Any],
    own_company_id: Optional[str],
) -> tuple[set[str], set[str], str]:
    expected = await ReferenceServiceFacade.get_applicable_documents(
        db,
        context=ReferenceContext(
            tenant_id=tenant_id,
            module="hr",
            entity_type="candidate",
            entity_id=str(candidate.id) if candidate else None,
            candidate_id=str(candidate.id) if candidate else None,
            citizenship=owner_context.get("citizenship"),
            work_country=owner_context.get("work_country"),
            residence_status=owner_context.get("residency_status"),
            position_category=(owner_context.get("vacancy") or {}).get("category") or owner_context.get("profession"),
            employment_type=(owner_context.get("vacancy") or {}).get("contract_type"),
            stage="hr",
            client_id=own_company_id,
            vacancy_id=str(getattr(candidate, "vacancy_id", "") or "").strip() or None,
        ),
    )
    required_types = {
        str(r.get("document_code") or "").strip().lower().replace("-", "_")
        for r in expected
        if bool(r.get("required")) and str(r.get("document_code") or "").strip()
    }
    optional_types = {
        str(r.get("document_code") or "").strip().lower().replace("-", "_")
        for r in expected
        if (not bool(r.get("required"))) and str(r.get("document_code") or "").strip()
    }
    return required_types, optional_types, "reference_service_facade"


def _is_requirement_waived(row: dict[str, Any]) -> bool:
    reviewed = row.get("reviewed_fields") if isinstance(row.get("reviewed_fields"), dict) else {}
    waiver = reviewed.get("_requirement_waiver")
    if not isinstance(waiver, dict):
        return False
    return bool(str(waiver.get("reason") or "").strip())


def _classify_requirement_tier(
    slot: _SlotDef,
    *,
    level: str,
    journey: dict[str, Any],
    position_category: Optional[str],
) -> str:
    """Map catalog level → hybrid tier (hard_blocker | required | recommended | not_required)."""
    if level == "not_required":
        return TIER_NOT_REQUIRED
    if slot.document_key in _ALWAYS_REQUIRED_KEYS:
        return TIER_HARD_BLOCKER
    if slot.journey_step and _journey_requires_document(journey, slot.journey_step):
        return TIER_HARD_BLOCKER
    if (
        slot.step_code == STEP_PROFESSIONAL
        and is_driver_position(position_category)
        and slot.document_key in _DRIVER_HARD_BLOCKER_KEYS
    ):
        return TIER_HARD_BLOCKER
    if level == "required":
        return TIER_REQUIRED
    return TIER_RECOMMENDED


def _apply_tier_metadata(row: dict[str, Any], tier: str) -> dict[str, Any]:
    row = dict(row)
    row["requirement_tier"] = tier
    row["overridable"] = tier in _TIERS_OVERRIDABLE
    if tier == TIER_RECOMMENDED:
        row["requirement_level"] = "optional"
        row["required"] = False
    elif tier in _TIERS_IN_PLAN:
        row["requirement_level"] = "required"
        row["required"] = True
    else:
        row["requirement_level"] = "not_required"
        row["required"] = False
    return row


def _hr_requested_document_rows(review: WorkforceHrReview) -> list[dict[str, Any]]:
    basis = review.decision_basis_json if isinstance(review.decision_basis_json, dict) else {}
    raw = basis.get("hr_document_requests") or basis.get("additional_document_requests") or []
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        key = str(item.get("document_key") or item.get("label") or "").strip()
        if not key:
            continue
        out.append(
            _apply_tier_metadata(
                {
                    "document_key": key,
                    "label": str(item.get("label") or key),
                    "status": str(item.get("status") or "requested"),
                    "step_code": str(item.get("step_code") or STEP_EMPLOYMENT),
                    "step_label": str(item.get("step_label") or "HR requested"),
                    "step_order": int(item.get("step_order") or 5),
                    "slot_order": idx + 1,
                    "requested_by": item.get("requested_by") or "hr",
                    "request_note": item.get("note") or item.get("reason"),
                },
                TIER_HR_REQUESTED,
            )
        )
    return out


def _classify_slot(
    slot: _SlotDef,
    *,
    required_types: set[str],
    optional_types: set[str],
    journey: dict[str, Any],
    position_category: Optional[str],
) -> str:
    """Catalog match: required | optional | not_required (feeds tier mapping)."""
    if slot.document_key in _ALWAYS_INCLUDED_DATA_KEYS:
        return "required"
    if slot.document_key in _ALWAYS_REQUIRED_KEYS:
        return "required"
    catalog_hit_required = bool(slot.catalog_types & required_types)
    catalog_hit_optional = bool(slot.catalog_types & optional_types)
    if slot.step_code == STEP_PROFESSIONAL and not is_driver_position(position_category):
        return "not_required"
    if slot.journey_step and _journey_requires_document(journey, slot.journey_step):
        return "required"
    if catalog_hit_required:
        return "required"
    if catalog_hit_optional:
        return "optional"
    # Map via CATALOG_TO_DOCUMENT_KEY for types only in required set
    for ct in required_types:
        if CATALOG_TO_DOCUMENT_KEY.get(ct) == slot.document_key:
            return "required"
    for ct in optional_types:
        if CATALOG_TO_DOCUMENT_KEY.get(ct) == slot.document_key:
            return "optional"
    if slot.document_key in OPTIONAL_FILE_VERIFICATION_KEYS:
        return "optional"
    # Handoff dossier mirrors recruitment package — include standard blocks for HR review.
    return "required"


def _legacy_row_for_slot(
    document_key: str,
    legacy_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    for r in legacy_rows:
        if str(r.get("document_key") or "") == document_key:
            return dict(r)
    return {
        "document_key": document_key,
        "label": document_key,
        "status": "missing",
        "verified": False,
    }


async def build_hr_verification_plan(
    db: AsyncSession,
    tenant_id: str,
    review: WorkforceHrReview,
    *,
    employee: Optional[WorkforceEmployee] = None,
    candidate: Optional[Candidate] = None,
    legacy_approval_rows: Optional[list[dict[str, Any]]] = None,
    bundle: Optional[dict[str, Any]] = None,
    journey: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    tid = str(tenant_id).strip()
    cid = str(
        (candidate.id if candidate else None)
        or review.candidate_id
        or (employee.candidate_id if employee else None)
        or ""
    ).strip()
    if not candidate and cid:
        candidate = await db.get(Candidate, cid)

    vacancy: Optional[Vacancy] = None
    profile = None
    if candidate:
        from backend.app.services.candidate_document_checklist import (
            resolve_vacancy_profile_for_document_checklist,
        )

        profile = await resolve_vacancy_profile_for_document_checklist(db, tid, candidate)
    if candidate and getattr(candidate, "vacancy_id", None):
        vacancy = await db.get(Vacancy, str(candidate.vacancy_id))

    if journey is None and employee and review.employee_id:
        journey = await build_work_eligibility_journey(db, tid, str(review.employee_id))
    journey = journey if isinstance(journey, dict) else {}

    owner_ctx = await _build_ruleset_context(db, tid, candidate=candidate, employee=employee, vacancy=vacancy)
    oc = str(getattr(candidate, "own_company_id", None) or getattr(employee, "own_company_id", None) or "").strip() or None
    required_types, optional_types, required_source = await _resolve_expected_document_sets(
        db,
        tid,
        candidate=candidate,
        owner_context=owner_ctx,
        own_company_id=oc,
    )

    position_category = await resolve_position_category_for_review(
        db, tid, employee_id=review.employee_id, candidate_id=cid or None
    )

    legacy = list(legacy_approval_rows or [])
    plan_documents: list[dict[str, Any]] = []
    steps_out: list[dict[str, Any]] = []
    steps_seen: set[str] = set()

    for slot in VERIFICATION_SLOT_DEFS:
        level = _classify_slot(
            slot,
            required_types=required_types,
            optional_types=optional_types,
            journey=journey,
            position_category=position_category,
        )
        if level == "not_required":
            continue
        tier = _classify_requirement_tier(
            slot,
            level=level,
            journey=journey,
            position_category=position_category,
        )
        row = _legacy_row_for_slot(slot.document_key, legacy)
        row["step_code"] = slot.step_code
        row["step_label"] = STEP_LABELS[slot.step_code]
        row["step_order"] = slot.step_order
        row["slot_order"] = slot.slot_order
        row["catalog_types"] = sorted(slot.catalog_types)
        plan_documents.append(_apply_tier_metadata(row, tier))

        if slot.step_code not in steps_seen:
            steps_seen.add(slot.step_code)
            steps_out.append(
                {
                    "step_code": slot.step_code,
                    "step_order": slot.step_order,
                    "label": STEP_LABELS[slot.step_code],
                    "document_keys": [],
                }
            )
        for st in steps_out:
            if st["step_code"] == slot.step_code:
                st["document_keys"].append(slot.document_key)

    steps_out.sort(key=lambda s: int(s.get("step_order") or 0))

    wel = bundle.get("work_eligibility_profile") if bundle else None
    vac_meta = owner_ctx.get("vacancy") if isinstance(owner_ctx.get("vacancy"), dict) else {}
    candidate_context = {
        "citizenship": owner_ctx.get("citizenship"),
        "eu_citizen": owner_ctx.get("eu_citizen"),
        "work_country": owner_ctx.get("work_country"),
        "legal_status": owner_ctx.get("legal_status"),
        "residency_status": owner_ctx.get("residency_status"),
        "profession": owner_ctx.get("profession"),
        "position_category": position_category,
        "role": (candidate._get_extra().get("role") if candidate else None),
    }
    vacancy_context: dict[str, Any] = dict(vac_meta) if vac_meta else {}
    if vacancy:
        vacancy_context.update(
            {
                "id": str(vacancy.id),
                "title": getattr(vacancy, "title", None),
            }
        )
    client_context: dict[str, Any] = {}
    if candidate and getattr(candidate, "company_id", None):
        client_context["company_id"] = str(candidate.company_id)
    if profile:
        client_context["profile_id"] = str(profile.id)
        if getattr(profile, "client_id", None):
            client_context["client_id"] = str(profile.client_id)
        client_context["profile_code"] = getattr(profile, "code", None)
        cfg = profile.config if isinstance(profile.config, dict) else {}
        doc_cfgs = cfg.get("document_configs") if isinstance(cfg.get("document_configs"), list) else []
        client_context["document_requirements_count"] = len(doc_cfgs)
    if wel is not None:
        candidate_context["eligibility_status"] = getattr(wel, "eligibility_status", None)
        candidate_context["requires_work_permit"] = getattr(wel, "requires_work_permit", None)

    hr_requested = _hr_requested_document_rows(review)
    plan_documents.extend(hr_requested)
    for hr_row in hr_requested:
        sc = str(hr_row.get("step_code") or STEP_EMPLOYMENT)
        if sc not in steps_seen:
            steps_seen.add(sc)
            steps_out.append(
                {
                    "step_code": sc,
                    "step_order": int(hr_row.get("step_order") or 5),
                    "label": str(hr_row.get("step_label") or "HR requested"),
                    "document_keys": [],
                }
            )
        for st in steps_out:
            if st["step_code"] == sc:
                st["document_keys"].append(hr_row["document_key"])

    blocking_reasons, can_complete = _recompute_plan_blocking(plan_documents)
    return {
        "plan_mode": "hybrid",
        "candidate_context": candidate_context,
        "vacancy_context": vacancy_context,
        "client_context": client_context,
        "ruleset_checklist": {
            "required_types": sorted(required_types),
            "optional_types": sorted(optional_types),
            "source": required_source,
        },
        "documents": plan_documents,
        "hard_blocker_documents": [d for d in plan_documents if d.get("requirement_tier") == TIER_HARD_BLOCKER],
        "required_documents": [d for d in plan_documents if d.get("requirement_tier") == TIER_REQUIRED],
        "recommended_documents": [d for d in plan_documents if d.get("requirement_tier") == TIER_RECOMMENDED],
        "optional_documents": [d for d in plan_documents if d.get("requirement_tier") == TIER_RECOMMENDED],
        "hr_requested_documents": hr_requested,
        "not_required_document_keys": [
            s.document_key
            for s in VERIFICATION_SLOT_DEFS
            if _classify_slot(
                s,
                required_types=required_types,
                optional_types=optional_types,
                journey=journey,
                position_category=position_category,
            )
            == "not_required"
        ],
        "verification_order": steps_out,
        "blocking_reasons": blocking_reasons,
        "can_complete_verification": can_complete,
        "can_approve": can_complete,
    }


def _collect_missing_data_from_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fields HR can fill from document or return for recruiter correction."""
    out: list[dict[str, Any]] = []
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        key = str(doc.get("document_key") or "")
        for field in doc.get("fields_to_review") or []:
            if not isinstance(field, dict):
                continue
            if not field.get("needs_manual_confirmation") or field.get("confirmed"):
                continue
            out.append(
                {
                    "document_key": key,
                    "field_code": field.get("field_code"),
                    "label": field.get("label"),
                    "hint": "enter_from_document",
                }
            )
    return out


def _document_tier(row: dict[str, Any]) -> str:
    return str(row.get("requirement_tier") or row.get("requirement_level") or "")


def _tier_blocks_approve(tier: str, row: dict[str, Any]) -> bool:
    if tier not in _TIERS_BLOCK_APPROVE:
        return False
    if tier in _TIERS_OVERRIDABLE and _is_requirement_waived(row):
        return False
    return True


def _recompute_plan_blocking(plan_documents: list[dict[str, Any]]) -> tuple[list[str], bool]:
    """Only hard blockers + non-waived required/hr_requested block approve."""
    blocking: list[str] = []
    for row in plan_documents:
        tier = _document_tier(row)
        if not _tier_blocks_approve(tier, row):
            continue
        key = str(row.get("document_key") or "")
        vs = str(row.get("verification_status") or row.get("status") or "").lower()
        prefix = "hard_blocker" if tier == TIER_HARD_BLOCKER else "required"
        if not row.get("document_id"):
            blocking.append(f"{prefix}:missing_file:{key}")
        elif vs not in ("verified", "not_required"):
            blocking.append(f"{prefix}:document_not_confirmed:{key}")
        reviewed = row.get("reviewed_fields") if isinstance(row.get("reviewed_fields"), dict) else {}
        for field in row.get("fields_to_review") or []:
            if not isinstance(field, dict):
                continue
            code = str(field.get("field_code") or "")
            if not code:
                continue
            entry = reviewed.get(code) if isinstance(reviewed.get(code), dict) else {}
            confirmed = bool(field.get("confirmed") or entry.get("confirmed"))
            has_value = bool(
                str(entry.get("value") or field.get("reviewed_value") or "").strip()
                or _pick_recruiter_field_value(field)
            )
            if field.get("needs_manual_confirmation") and not confirmed and not has_value:
                blocking.append(f"{prefix}:missing_required_field:{key}:{code}")
    return blocking, len(blocking) == 0


def _pick_recruiter_field_value(field: dict[str, Any]) -> Optional[str]:
    vals = field.get("current_profile_values")
    if not isinstance(vals, dict):
        return None
    for v in vals.values():
        if v is not None and str(v).strip():
            return str(v).strip()
    return None


def sync_verification_plan_with_enriched_docs(
    plan: dict[str, Any],
    enriched_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge enriched verification rows into plan documents and refresh blocking/missing_data."""
    by_key = {
        str(r.get("document_key") or ""): r
        for r in enriched_rows
        if isinstance(r, dict) and r.get("document_key")
    }
    meta_keys = (
        "requirement_tier",
        "requirement_level",
        "required",
        "overridable",
        "step_code",
        "step_label",
        "step_order",
        "slot_order",
        "catalog_types",
        "requested_by",
        "request_note",
    )

    def _merge_slot(slot: dict[str, Any]) -> dict[str, Any]:
        key = str(slot.get("document_key") or "")
        enriched = by_key.get(key)
        if not enriched:
            return dict(slot)
        merged = dict(enriched)
        for mk in meta_keys:
            if slot.get(mk) is not None:
                merged[mk] = slot[mk]
        return merged

    plan = dict(plan)
    docs = [_merge_slot(d) for d in plan.get("documents") or [] if isinstance(d, dict)]
    plan["documents"] = docs
    plan["hard_blocker_documents"] = [d for d in docs if d.get("requirement_tier") == TIER_HARD_BLOCKER]
    plan["required_documents"] = [d for d in docs if d.get("requirement_tier") == TIER_REQUIRED]
    plan["recommended_documents"] = [d for d in docs if d.get("requirement_tier") == TIER_RECOMMENDED]
    plan["optional_documents"] = plan["recommended_documents"]
    plan["hr_requested_documents"] = [d for d in docs if d.get("requirement_tier") == TIER_HR_REQUESTED]
    blocking, can_complete = _recompute_plan_blocking(docs)
    plan["blocking_reasons"] = blocking
    plan["can_complete_verification"] = can_complete
    plan["can_approve"] = can_complete
    plan["missing_data"] = _collect_missing_data_from_docs(docs)
    return plan


def documents_for_approval_from_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Rows for enrich + UI — all tiers except not_required."""
    out: list[dict[str, Any]] = []
    for d in plan.get("documents") or []:
        if not isinstance(d, dict):
            continue
        tier = _document_tier(d)
        if tier in _TIERS_IN_PLAN or d.get("requirement_level") in ("required", "optional"):
            out.append(dict(d))
    out.sort(key=lambda r: (int(r.get("step_order") or 0), int(r.get("slot_order") or 0)))
    return out


def plan_blocks_approve(plan: Optional[dict[str, Any]]) -> bool:
    if not plan:
        return True
    if plan.get("can_approve") is False or plan.get("can_complete_verification") is False:
        return True
    return bool(plan.get("blocking_reasons"))


def is_document_requirement_waivable(
    document_key: str,
    *,
    journey: Optional[dict[str, Any]] = None,
    position_category: Optional[str] = None,
) -> bool:
    """True only for required/recommended tiers — never hard_blocker."""
    key = str(document_key or "").strip()
    if not key:
        return False
    slot = next((s for s in VERIFICATION_SLOT_DEFS if s.document_key == key), None)
    if not slot:
        return True
    tier = _classify_requirement_tier(
        slot,
        level="required",
        journey=journey if isinstance(journey, dict) else {},
        position_category=position_category,
    )
    return tier in _TIERS_OVERRIDABLE
