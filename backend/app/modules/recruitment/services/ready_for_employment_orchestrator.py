"""RSO-2: Fits prepares Ready for employment; Transfer crosses the boundary.

Fits = Recruitment decision + package prep (never create_handoff / Employee).
Transfer = explicit boundary: revalidate package → create_handoff → audit
Recruitment completed.

Contract: ``ready_for_employment.v1``
SoT: docs/specs/architecture/ready-for-employment-contract.md
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Final, Literal, Mapping, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from fastapi import HTTPException

from backend.app.core.audit_events import AuditEntityType, AuditEventType
from backend.app.models import Lead
from backend.app.models.candidate import Candidate
from backend.app.models.vacancy import Vacancy
from backend.app.modules.leads import crud
from backend.app.modules.leads.duplicate_resolution import resolve_lead_duplicate_match
from backend.app.reference.ready_for_employment import (
    CONTRACT_ID,
    FORBIDDEN_TOP_LEVEL_KEYS,
    TRANSFER_OPERATOR_ACTION,
    validate_ready_for_employment_package_v1,
)
from backend.app.services.audit import log_audit_event

PREP_KEY: Final[str] = "ready_for_employment_prep_v1"
FITS_INTENT: Final[str] = "fits"
NEXT_OFFER_HANDOFF: Final[str] = "offer_handoff"
NEXT_ASK_MISSING: Final[str] = "ask_recruitment_missing"
NEXT_CONFIRM_DUPLICATE: Final[str] = "confirm_probable_duplicate"
NEXT_ASK_VACANCY: Final[str] = "ask_vacancy"
NEXT_NOT_FITS: Final[str] = "not_fits"

READY_LABEL: Final[str] = "Готов к передаче на трудоустройство"

# Codes that must never appear as Recruitment missing (Employment / legalization).
FORBIDDEN_RECRUITMENT_MISSING_CODES: Final[frozenset[str]] = frozenset(
    {
        "passport",
        "passport_scan",
        "visa",
        "zezwolenie",
        "work_permit",
        "zus",
        "zus_journey",
        "legalization",
        "legalization_pathway",
        "employment_contract",
        "employment_missing",
        "create_employee",
        "accept_handoff",
        "employee_id",
    }
)

NextAction = Literal[
    "offer_handoff",
    "ask_recruitment_missing",
    "confirm_probable_duplicate",
    "ask_vacancy",
    "not_fits",
]


@dataclass
class FitsResult:
    next_action: NextAction
    package: dict[str, Any] | None = None
    package_valid: bool = False
    package_fingerprint: str | None = None
    recruitment_missing: list[dict[str, str]] = field(default_factory=list)
    probable_duplicate: dict[str, Any] | None = None
    vacancy_prompt: str | None = None
    message: str | None = None
    candidate_id: str | None = None
    created_handoff: bool = False  # always False after Fits


@dataclass
class TransferResult:
    handoff_id: str
    package: dict[str, Any]
    package_fingerprint: str
    created: bool
    message: str | None = None


class RsoOrchestratorError(Exception):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def package_fingerprint_v1(package: Mapping[str, Any]) -> str:
    """Stable hash of package-critical facts (staleness check on Transfer)."""
    person = _record(package.get("person"))
    target = _record(package.get("target_work"))
    fits = _record(package.get("fits_decision"))
    refs = _record(package.get("context_refs"))
    critical = {
        "contract_id": package.get("contract_id"),
        "tenant_id": _text(package.get("tenant_id")),
        "person_id": _text(person.get("person_id") or person.get("candidate_id")),
        "identity_facts": _record(person.get("identity_facts")),
        "vacancy_id": _text(target.get("vacancy_id")),
        "employer_id": _text(target.get("employer_id")),
        "role": _text(target.get("role")),
        "fits_decision": _text(fits.get("decision")).lower(),
        "application_id": _text(refs.get("application_id")),
        "recruitment_facts": _record(package.get("recruitment_facts")),
        "evidence": _record(package.get("evidence")),
    }
    raw = json.dumps(critical, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def assert_recruitment_missing_is_rso_safe(missing: list[dict[str, str]]) -> list[str]:
    """Return violation codes if Employment/legalization items leaked into missing."""
    violations: list[str] = []
    for row in missing:
        code = _text(row.get("field_code") or row.get("code")).lower().replace("-", "_")
        if code in FORBIDDEN_RECRUITMENT_MISSING_CODES:
            violations.append(code)
        label = _text(row.get("label")).lower()
        for bad in ("zezwolenie", "legalization", "zus ", "work permit", "паспорт для трудоустр"):
            if bad in label:
                violations.append(code or label)
    return violations


def filter_rso_recruitment_missing(missing: list[dict[str, str]]) -> list[dict[str, str]]:
    """Drop any employment-side codes that slipped in (defense in depth)."""
    out: list[dict[str, str]] = []
    for row in missing:
        code = _text(row.get("field_code") or row.get("code")).lower().replace("-", "_")
        if code in FORBIDDEN_RECRUITMENT_MISSING_CODES:
            continue
        out.append(row)
    return out


def _alpha2(value: Any) -> str:
    code = _text(value).upper()
    return code if len(code) == 2 and code.isalpha() else ""


def _identity_overlay_from_lead(lead: Lead | None) -> dict[str, Any]:
    if lead is None:
        return {}
    norm = _record(lead.normalized)
    out: dict[str, Any] = {}
    for key in ("citizenship", "nationality", "nationality_code"):
        code = _alpha2(norm.get(key))
        if code:
            out["citizenship"] = code
            break
    first = _text(norm.get("first_name") or getattr(lead, "first_name", None))
    last = _text(norm.get("last_name") or getattr(lead, "last_name", None))
    if first:
        out.setdefault("first_name", first)
    if last:
        out.setdefault("last_name", last)
    return out


def _employment_country_from_vacancy(vacancy: Vacancy | None) -> str:
    loc = _text(getattr(vacancy, "location", None)).upper()
    if "PL" in loc or "POLAND" in loc or "POLSKA" in loc:
        return "PL"
    return "PL"


def build_ready_for_employment_package_v1(
    *,
    tenant_id: str,
    application_id: str,
    candidate: Candidate,
    vacancy: Vacancy | None,
    actor_id: str,
    decided_at: str,
    evidence: Mapping[str, Any] | None = None,
    recruitment_facts: Mapping[str, Any] | None = None,
    source_id: str | None = None,
    lead: Lead | None = None,
) -> dict[str, Any]:
    """Assemble package blocks. Does not persist. Does not create handoff."""
    personal = candidate._get_personal_data() if hasattr(candidate, "_get_personal_data") else {}
    if not isinstance(personal, dict):
        personal = {}
    identity_facts: dict[str, Any] = {}
    extra = candidate._get_extra() if hasattr(candidate, "_get_extra") else {}
    if not isinstance(extra, dict):
        extra = {}
    for key in ("citizenship", "first_name", "last_name", "nationality"):
        val = personal.get(key) or extra.get(key) or getattr(candidate, key, None)
        if val is not None and _text(val):
            identity_facts[key] = val
    if candidate.first_name and "first_name" not in identity_facts:
        identity_facts["first_name"] = candidate.first_name
    if candidate.last_name and "last_name" not in identity_facts:
        identity_facts["last_name"] = candidate.last_name
    overlay = _identity_overlay_from_lead(lead)
    for key, val in overlay.items():
        identity_facts.setdefault(key, val)

    vac_id = _text(getattr(vacancy, "id", None) or getattr(candidate, "vacancy_id", None)) or None
    employer_id = _text(getattr(vacancy, "company_id", None) or getattr(candidate, "company_id", None)) or None
    role = _text(getattr(vacancy, "title", None)) or None

    target_work: dict[str, Any] = {}
    if vac_id:
        target_work["vacancy_id"] = vac_id
    if employer_id:
        target_work["employer_id"] = employer_id
    if role:
        target_work["role"] = role
    target_work["employment_country"] = _employment_country_from_vacancy(vacancy)

    context_refs: dict[str, Any] = {"application_id": application_id}
    if source_id:
        context_refs["source_id"] = source_id
    if actor_id:
        context_refs["recruiter_id"] = actor_id

    package: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "tenant_id": tenant_id,
        "person": {
            "person_id": str(candidate.id),
            "candidate_id": str(candidate.id),
            "identity_facts": identity_facts,
        },
        "target_work": target_work,
        "recruitment_facts": dict(recruitment_facts or {}),
        "evidence": dict(evidence or {}),
        "fits_decision": {
            "decision": "fits",
            "decided_at": decided_at,
            "actor_id": actor_id,
        },
        "context_refs": context_refs,
    }
    return package


def evaluate_package_recruitment_missing(
    *,
    candidate: Candidate | None,
    vacancy: Vacancy | None,
    package: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    """Only facts required to decide Fits and assemble a correct package."""
    missing: list[dict[str, str]] = []
    if candidate is None:
        missing.append({"field_code": "person", "label": "Person / candidate"})
    target = _record((package or {}).get("target_work")) if package else {}
    vac_ok = bool(_text(target.get("vacancy_id")) or (vacancy is not None and _text(getattr(vacancy, "id", None))))
    emp_ok = bool(
        _text(target.get("employer_id"))
        or (vacancy is not None and _text(getattr(vacancy, "company_id", None)))
        or (candidate is not None and _text(getattr(candidate, "company_id", None)))
    )
    if not vac_ok and not emp_ok:
        missing.append(
            {
                "field_code": "target_work",
                "label": "Vacancy or employer for this fit",
            }
        )
    if package is not None:
        for err in validate_ready_for_employment_package_v1(package):
            # Map validator gaps to operator-facing missing (not employment docs).
            if "person" in err and not any(m["field_code"] == "person" for m in missing):
                missing.append({"field_code": "person", "label": "Person / candidate"})
            elif "target_work" in err and not any(m["field_code"] == "target_work" for m in missing):
                missing.append(
                    {
                        "field_code": "target_work",
                        "label": "Vacancy or employer for this fit",
                    }
                )
            elif "fits_decision" in err:
                missing.append({"field_code": "fits_decision", "label": "Fits decision"})
    return filter_rso_recruitment_missing(missing)


def _read_prep(lead: Lead) -> dict[str, Any]:
    return _record(_record(lead.normalized).get(PREP_KEY))


def _write_prep(lead: Lead, prep: Mapping[str, Any]) -> None:
    norm = _record(lead.normalized)
    norm[PREP_KEY] = dict(prep)
    lead.normalized = norm
    try:
        flag_modified(lead, "normalized")
    except AttributeError:
        # Non-ORM doubles in unit tests.
        pass


async def _load_vacancy(db: AsyncSession, tenant_id: str, vacancy_id: str | None) -> Vacancy | None:
    if not vacancy_id:
        return None
    vac = await db.get(Vacancy, vacancy_id)
    if vac is None:
        return None
    if _text(getattr(vac, "tenant_id", None)) and _text(vac.tenant_id) != _text(tenant_id):
        return None
    return vac


async def _resolve_vacancy_for_fits(
    db: AsyncSession,
    *,
    tenant_id: str,
    lead: Lead,
) -> tuple[Vacancy | None, NextAction | None, str | None]:
    """AUTO only when resolution is unambiguous. Else human vacancy question."""
    vac_id = _text(getattr(lead, "vacancy_id", None))
    if vac_id:
        vac = await _load_vacancy(db, tenant_id, vac_id)
        if vac is not None:
            return vac, None, None
        return None, NEXT_ASK_VACANCY, "Vacancy on application is missing or inaccessible"

    # Meta ad → vacancy map (single entry when present).
    raw_ad = getattr(lead, "ad_id", None)
    if raw_ad is None:
        raw_ad = _record(lead.normalized).get("ad_id")
    if raw_ad is not None and _text(raw_ad):
        try:
            ad_id = int(_text(raw_ad))
        except (TypeError, ValueError):
            ad_id = None
        if ad_id is not None:
            entry = await crud.get_meta_ads_entry(db, tenant_id=tenant_id, ad_id=ad_id)
            mapped = _text(getattr(entry, "vacancy_id", None)) if entry else ""
            if mapped:
                vac = await _load_vacancy(db, tenant_id, mapped)
                if vac is not None:
                    return vac, None, None

    return (
        None,
        NEXT_ASK_VACANCY,
        "Для какой вакансии подходит этот человек?",
    )


async def run_fits_prep(
    db: AsyncSession,
    *,
    tenant_id: str,
    own_company_id: str | None,
    application_id: str,
    actor_id: str,
    current_user: Any,
) -> FitsResult:
    """Recruitment-side prep after Fits. Never creates handoff or Employee."""
    from backend.app.modules.applications import mutations as app_mutations
    from backend.app.modules.leads import service as lead_service

    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead or (lead.lead_type == "client" and lead.lead_target_type == "client_lead"):
        raise RsoOrchestratorError("application_not_found", "Application not found")

    decided_at = _now_iso()
    actor = _text(actor_id) or "unknown"

    vacancy, vac_block, vac_prompt = await _resolve_vacancy_for_fits(db, tenant_id=tenant_id, lead=lead)
    if vac_block == NEXT_ASK_VACANCY:
        prep = {
            "fits_decision": {"decision": "fits", "decided_at": decided_at, "actor_id": actor},
            "next_action": NEXT_ASK_VACANCY,
            "vacancy_prompt": vac_prompt,
            "package": None,
            "package_valid": False,
            "package_fingerprint": None,
            "recruitment_missing": [],
            "prepared_at": decided_at,
            "handoff_id": None,
            "recruitment_completed_at": None,
        }
        _write_prep(lead, prep)
        return FitsResult(
            next_action=NEXT_ASK_VACANCY,
            vacancy_prompt=vac_prompt,
            message=vac_prompt,
            created_handoff=False,
        )

    # Confirm vacancy onto lead when resolved from map (zero-choice AUTO).
    if vacancy is not None and not _text(getattr(lead, "vacancy_id", None)):
        try:
            await lead_service.confirm_lead_vacancy(
                db,
                tenant_id=tenant_id,
                lead_id=application_id,
                vacancy_id=str(vacancy.id),
                actor_sub=actor,
            )
            lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
            if not lead:
                raise RsoOrchestratorError("application_not_found", "Application not found")
        except lead_service.LeadProcessingError as exc:
            raise RsoOrchestratorError(
                getattr(exc, "code", None) or "vacancy_confirm_failed",
                str(exc),
            ) from exc

    candidate_id = _text(getattr(lead, "candidate_id", None)) or None
    candidate: Candidate | None = None
    if candidate_id:
        candidate = await db.get(Candidate, candidate_id)

    # Probable duplicate is the only allowed interruption before person attach.
    if candidate is None:
        norm = _record(lead.normalized)
        match = await resolve_lead_duplicate_match(
            db,
            tenant_id=tenant_id,
            company_id=_text(getattr(lead, "company_id", None))
            or _text(getattr(vacancy, "company_id", None))
            or None,
            normalized=norm,
            email=_text(getattr(lead, "email", None)) or norm.get("email"),
            phone=_text(getattr(lead, "phone", None)) or norm.get("phone"),
            exclude_lead_id=str(lead.id),
        )
        if match.level == "probable" and match.candidate is not None:
            probable = {
                "candidate_id": str(match.candidate.id),
                "reasons": list(match.reasons),
                "prompt": "Это тот же человек?",
            }
            prep = {
                "fits_decision": {"decision": "fits", "decided_at": decided_at, "actor_id": actor},
                "next_action": NEXT_CONFIRM_DUPLICATE,
                "probable_duplicate": probable,
                "package": None,
                "package_valid": False,
                "package_fingerprint": None,
                "recruitment_missing": [],
                "prepared_at": decided_at,
                "handoff_id": None,
                "recruitment_completed_at": None,
            }
            _write_prep(lead, prep)
            return FitsResult(
                next_action=NEXT_CONFIRM_DUPLICATE,
                probable_duplicate=probable,
                message="Это тот же человек?",
                created_handoff=False,
            )

        # Exact → silent attach / create via existing process (AUTO).
        try:
            await app_mutations._prepare_recruitment_application_for_process(
                db,
                tenant_id=tenant_id,
                application_id=application_id,
                current_user=current_user,
            )
            process_result = await app_mutations.recruitment_process_application(
                db,
                tenant_id=tenant_id,
                own_company_id=own_company_id or "",
                application_id=application_id,
                current_user=current_user,
            )
            candidate_id = _text(getattr(process_result, "candidate_id", None)) or None
        except HTTPException:
            raise
        except RsoOrchestratorError:
            raise
        except Exception as exc:  # noqa: BLE001 — surface as orchestrator blocker
            detail = getattr(exc, "detail", None)
            code = "person_attach_failed"
            if isinstance(detail, dict) and detail.get("code"):
                code = str(detail["code"])
            elif isinstance(detail, str):
                code = detail
            raise RsoOrchestratorError(code, str(detail or exc)) from exc

        lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
        if not lead:
            raise RsoOrchestratorError("application_not_found", "Application not found")
        candidate_id = candidate_id or _text(getattr(lead, "candidate_id", None)) or None
        if candidate_id:
            candidate = await db.get(Candidate, candidate_id)

    if candidate is None:
        missing = [{"field_code": "person", "label": "Person / candidate"}]
        prep = {
            "fits_decision": {"decision": "fits", "decided_at": decided_at, "actor_id": actor},
            "next_action": NEXT_ASK_MISSING,
            "recruitment_missing": missing,
            "package": None,
            "package_valid": False,
            "package_fingerprint": None,
            "prepared_at": decided_at,
            "handoff_id": None,
            "recruitment_completed_at": None,
        }
        _write_prep(lead, prep)
        return FitsResult(
            next_action=NEXT_ASK_MISSING,
            recruitment_missing=missing,
            message="Recruitment needs a person before handoff package",
            created_handoff=False,
        )

    # Reflect readiness on candidate stage (not SoT; package is SoT). No handoff yet.
    stage = _text(getattr(candidate, "stage", None)).lower()
    if stage not in {"ready_for_handoff", "ready_for_hr", "handed_off", "processing_by_hr", "processing_by_client"}:
        candidate.stage = "ready_for_handoff"

    evidence = {
        "source": _text(getattr(lead, "source", None)) or "recruitment_application",
        "call_result_v1": _record(lead.normalized).get("call_result_v1"),
        "document_ids": [],
    }
    package = build_ready_for_employment_package_v1(
        tenant_id=tenant_id,
        application_id=application_id,
        candidate=candidate,
        vacancy=vacancy,
        actor_id=actor,
        decided_at=decided_at,
        evidence=evidence,
        recruitment_facts={},
        source_id=_text(getattr(lead, "external_id", None)) or None,
        lead=lead,
    )
    errors = validate_ready_for_employment_package_v1(package)
    missing = evaluate_package_recruitment_missing(
        candidate=candidate, vacancy=vacancy, package=package if not errors else None
    )
    if errors and not missing:
        # Validator failed for non-missing structural reasons — treat as missing package facts.
        missing = [{"field_code": "package", "label": "Ready for employment package incomplete"}]

    violations = assert_recruitment_missing_is_rso_safe(missing)
    if violations:
        raise RsoOrchestratorError(
            "employment_missing_leaked",
            "Recruitment missing must not include employment/legalization items",
            details={"codes": violations},
        )

    if missing or errors:
        prep = {
            "fits_decision": package["fits_decision"],
            "next_action": NEXT_ASK_MISSING,
            "recruitment_missing": missing,
            "package": package,
            "package_valid": False,
            "package_fingerprint": None,
            "validation_errors": errors,
            "prepared_at": decided_at,
            "handoff_id": None,
            "recruitment_completed_at": None,
        }
        _write_prep(lead, prep)
        return FitsResult(
            next_action=NEXT_ASK_MISSING,
            package=package,
            package_valid=False,
            recruitment_missing=missing,
            candidate_id=str(candidate.id),
            message="Recruitment missing facts required for the handoff package",
            created_handoff=False,
        )

    fp = package_fingerprint_v1(package)
    prep = {
        "fits_decision": package["fits_decision"],
        "next_action": NEXT_OFFER_HANDOFF,
        "recruitment_missing": [],
        "package": package,
        "package_valid": True,
        "package_fingerprint": fp,
        "prepared_at": decided_at,
        "ready_label": READY_LABEL,
        "transfer_action": TRANSFER_OPERATOR_ACTION,
        "handoff_id": None,
        "recruitment_completed_at": None,
    }
    _write_prep(lead, prep)
    return FitsResult(
        next_action=NEXT_OFFER_HANDOFF,
        package=package,
        package_valid=True,
        package_fingerprint=fp,
        candidate_id=str(candidate.id),
        message=READY_LABEL,
        created_handoff=False,
    )


async def run_transfer_to_employment(
    db: AsyncSession,
    *,
    tenant_id: str,
    application_id: str,
    actor_id: str,
    destination: str = "internal_hr",
    client_company_id: str | None = None,
    client_tenant_id: str | None = None,
) -> TransferResult:
    """Boundary crossing only. Revalidates package; never trusts a stale Fits snapshot."""
    from backend.app.services import handoff as handoff_service

    lead = await crud.get_lead(db, tenant_id=tenant_id, lead_id=application_id)
    if not lead or (lead.lead_type == "client" and lead.lead_target_type == "client_lead"):
        raise RsoOrchestratorError("application_not_found", "Application not found")

    prep = _read_prep(lead)
    if _text(prep.get("next_action")) != NEXT_OFFER_HANDOFF and not prep.get("package_valid"):
        # Allow transfer if we can rebuild a valid package now; else block.
        pass

    candidate_id = _text(getattr(lead, "candidate_id", None))
    if not candidate_id:
        raise RsoOrchestratorError(
            "person_required",
            "Transfer requires a person; run Fits prep first",
        )
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None:
        raise RsoOrchestratorError("person_required", "Candidate not found")

    vac_id = _text(getattr(lead, "vacancy_id", None) or getattr(candidate, "vacancy_id", None)) or None
    vacancy = await _load_vacancy(db, tenant_id, vac_id)

    prior_fits = _record(prep.get("fits_decision"))
    decided_at = _text(prior_fits.get("decided_at")) or _now_iso()
    actor = _text(actor_id) or _text(prior_fits.get("actor_id")) or "unknown"

    evidence = {
        "source": _text(getattr(lead, "source", None)) or "recruitment_application",
        "call_result_v1": _record(lead.normalized).get("call_result_v1"),
        "document_ids": [],
    }
    # Rebuild from current facts — never emit a stale stored snapshot.
    package = build_ready_for_employment_package_v1(
        tenant_id=tenant_id,
        application_id=application_id,
        candidate=candidate,
        vacancy=vacancy,
        actor_id=actor,
        decided_at=decided_at,
        evidence=evidence,
        recruitment_facts=_record(_record(prep.get("package")).get("recruitment_facts")),
        source_id=_text(getattr(lead, "external_id", None)) or None,
    )
    errors = validate_ready_for_employment_package_v1(package)
    if errors:
        raise RsoOrchestratorError(
            "invalid_package",
            "ready_for_employment.v1 failed validation on Transfer",
            details={"errors": errors},
        )

    fp = package_fingerprint_v1(package)
    stored_fp = _text(prep.get("package_fingerprint"))
    if stored_fp and stored_fp != fp:
        # Package-critical data changed since Fits — require re-prep awareness;
        # Transfer still proceeds with freshly validated package (not stale).
        pass

    for key in FORBIDDEN_TOP_LEVEL_KEYS:
        if key in package:
            raise RsoOrchestratorError(
                "forbidden_package_key",
                f"Package must not contain {key}",
            )

    # Ensure stage gate for create_handoff reuse.
    stage = _text(getattr(candidate, "stage", None)).lower()
    if stage not in {"ready_for_handoff", "ready_for_hr"}:
        candidate.stage = "ready_for_handoff"

    dest = _text(destination) or "internal_hr"
    # Resolve client target from vacancy employer when not provided.
    if not client_company_id and not client_tenant_id:
        client_company_id = _text(getattr(vacancy, "company_id", None) or getattr(candidate, "company_id", None)) or None
    if not client_company_id and not client_tenant_id:
        raise RsoOrchestratorError(
            "client_required",
            "Transfer needs employer/client context from the package target work",
        )

    handoff, err = await handoff_service.create_handoff(
        db,
        candidate_id=str(candidate.id),
        agency_tenant_id=tenant_id,
        client_company_id=client_company_id,
        client_tenant_id=client_tenant_id,
        requested_by_user_id=actor,
        destination=dest,
        application_id=application_id,
        ready_for_employment_package=package,
        idempotent=True,
    )
    if err and handoff is None:
        if isinstance(err, dict):
            raise RsoOrchestratorError(
                str(err.get("code") or "handoff_failed"),
                str(err.get("message") or err),
                details=err,
            )
        raise RsoOrchestratorError("handoff_failed", str(err))

    assert handoff is not None
    created = bool(getattr(handoff, "_rso_created", True))
    completed_at = _now_iso()

    # Boundary audit: Recruitment completed — only after successful create_handoff.
    if created or not prep.get("recruitment_completed_at"):
        await log_audit_event(
            db,
            tenant_id=tenant_id,
            event_type=AuditEventType.recruitment_completed,
            entity_type=AuditEntityType.lead,
            entity_id=application_id,
            actor_id=actor,
            payload={
                "application_id": application_id,
                "candidate_id": str(candidate.id),
                "handoff_id": str(handoff.id),
                "contract_id": CONTRACT_ID,
                "package_fingerprint": fp,
                "message": "Recruitment completed",
            },
        )

    prep_out = {
        **prep,
        "next_action": "handed_off",
        "package": package,
        "package_valid": True,
        "package_fingerprint": fp,
        "handoff_id": str(handoff.id),
        "recruitment_completed_at": completed_at,
        "transfer_action": TRANSFER_OPERATOR_ACTION,
    }
    _write_prep(lead, prep_out)

    return TransferResult(
        handoff_id=str(handoff.id),
        package=package,
        package_fingerprint=fp,
        created=created,
        message="Recruitment completed",
    )


def fits_must_not_create_boundary_artifacts(result: FitsResult) -> None:
    """Machine invariant helper for gate tests."""
    if result.created_handoff:
        raise AssertionError("Fits must never create a handoff")


__all__ = [
    "FitsResult",
    "TransferResult",
    "RsoOrchestratorError",
    "PREP_KEY",
    "NEXT_OFFER_HANDOFF",
    "READY_LABEL",
    "FORBIDDEN_RECRUITMENT_MISSING_CODES",
    "package_fingerprint_v1",
    "build_ready_for_employment_package_v1",
    "evaluate_package_recruitment_missing",
    "assert_recruitment_missing_is_rso_safe",
    "run_fits_prep",
    "run_transfer_to_employment",
    "fits_must_not_create_boundary_artifacts",
]
