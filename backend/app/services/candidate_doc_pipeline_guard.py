"""
Server-side alignment with frontend `candidateStageDocPolicy.ts`.

Blocks *forward* stage transitions when:
- required documents are missing / problematic / awaiting review (unless waived), or
- `contacted` / `questionnaire_submitted` without `vacancy_id` (data gate), or
- `new` → forward while contact-attempt policy is on and zero attempts logged.

Backward/same-index moves are always allowed.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from backend.app.models.candidate import Candidate
from backend.app.constants.stages import LABELS, TERMINAL_STATUSES, code_for_label
from backend.app.constants.stages_adapter import PIPELINE_SEQUENCE
from backend.app.modules.documents import crud as documents_crud
from backend.app.modules.documents.crud import get_last_document_checks_map
from backend.app.modules.documents.owner_summary import compute_owner_summary
from backend.app.services.document_catalog import normalize_doc_type
from backend.app.services.document_ruleset import load_default_ruleset
from backend.app.services.ruleset_versioning import normalize_ruleset_payload
from backend.app.services.hiring_pipeline_gates import (
    HiringPipelineGates,
    contact_attempt_gate_applies,
    default_hiring_pipeline_gates,
    docs_pipeline_blocks_forward_resolved,
    resolve_hiring_pipeline_gates,
    vacancy_gate_applies,
)
from backend.app.services import contact_attempts as _contact_attempts

# Back-compat: defaults match `hiring_pipeline_gates.default_hiring_pipeline_gates()`.
STAGES_WITHOUT_DOC_PIPELINE_BLOCK: FrozenSet[str] = default_hiring_pipeline_gates().stages_without_doc_pipeline_block
STAGES_VERIFY_UPLOADS_BLOCK_FORWARD: FrozenSet[str] = default_hiring_pipeline_gates().stages_verify_uploads_block_forward
STAGES_REQUIRE_VACANCY_FOR_FORWARD: FrozenSet[str] = default_hiring_pipeline_gates().stages_require_vacancy_for_forward

# Extra aliases (API / funnel codes) → canonical codes used in PIPELINE_SEQUENCE
_STAGE_DOC_CANONICAL_ALIASES: Dict[str, str] = {
    "contact_established": "contacted",
    "interview": "contacted",
}

# Keep in sync with candidates/helpers._STAGE_CODE_ALIASES (avoid importing candidates.* → circular).
_HELPERS_STAGE_ALIASES: Dict[str, str] = {
    "planning_arrival": "trip_plan",
    "plan_arrival": "trip_plan",
    "planning-trip": "trip_plan",
}


def _normalize_stage_to_code_local(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip()
    vl = v.lower()
    alias = _HELPERS_STAGE_ALIASES.get(vl)
    if alias:
        return alias
    if vl in LABELS:
        return vl
    return code_for_label(v) or code_for_label(vl)


def _norm_stage_token(raw: Optional[str]) -> str:
    if not raw:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    code = _normalize_stage_to_code_local(s) or s.lower()
    return _STAGE_DOC_CANONICAL_ALIASES.get(code, code)


def _pipeline_index(code: str) -> int:
    if not code:
        return -1
    try:
        return PIPELINE_SEQUENCE.index(code)
    except ValueError:
        return -1


def is_forward_pipeline_move(old_stage: Optional[str], new_stage: str) -> bool:
    """True if new stage is strictly later in PIPELINE_SEQUENCE than old."""
    old_c = _norm_stage_token(old_stage)
    new_c = _norm_stage_token(new_stage)
    if not new_c:
        return False
    oi = _pipeline_index(old_c)
    ni = _pipeline_index(new_c)
    if ni < 0:
        return False
    if oi < 0:
        return False
    return ni > oi


def _norm_doc_type(value: str) -> str:
    raw = str(value or "").strip().lower().replace("-", "_")
    if not raw:
        return ""
    return normalize_doc_type(raw) or raw


def _relax_blocker_lists(
    missing: List[str],
    problematic: List[str],
    in_progress: List[str],
    relaxed: Set[str],
) -> Tuple[List[str], List[str], List[str]]:
    rset = {_norm_doc_type(x) for x in relaxed if x}
    rset.discard("")

    def filt(xs: List[str]) -> List[str]:
        out: List[str] = []
        for x in xs:
            if _norm_doc_type(x) not in rset:
                out.append(x)
        return out

    return filt(missing), filt(problematic), filt(in_progress)


def docs_pipeline_blocks_forward(
    canonical_stage: str,
    missing: List[str],
    problematic: List[str],
    in_progress: List[str],
    gates: HiringPipelineGates | None = None,
) -> bool:
    g = gates or default_hiring_pipeline_gates()
    hard, _soft = docs_pipeline_blocks_forward_resolved(canonical_stage, missing, problematic, in_progress, g)
    return hard


def _owner_context_for_docs(
    *,
    candidate_id: str,
    extra: Dict[str, Any] | None,
    personal: Dict[str, Any] | None,
) -> Dict[str, Any]:
    extra_data = extra if isinstance(extra, dict) else {}
    personal_data = personal if isinstance(personal, dict) else {}
    docs_raw = extra_data.get("documents")
    docs_ctx = {
        key: bool(value)
        for key, value in (docs_raw.items() if isinstance(docs_raw, dict) else [])
        if isinstance(value, bool)
    }
    ctx: Dict[str, Any] = {
        "candidate_id": str(candidate_id),
        "citizenship": extra_data.get("citizenship") or personal_data.get("citizenship"),
        "residency_status": extra_data.get("poland_stay_basis") or personal_data.get("residency_status"),
        "has_adr": extra_data.get("has_adr"),
        "documents": docs_ctx,
    }
    return {k: v for k, v in ctx.items() if v is not None}


def _minimal_serialized_doc(doc: Any, last_check: Any) -> Dict[str, Any]:
    st = getattr(doc.status, "value", None) or str(getattr(doc, "status", "") or "")
    lc = None
    if last_check is not None:
        decision = getattr(last_check, "decision", None)
        if decision:
            lc = {"decision": str(decision).strip().lower()}
    exp = getattr(doc, "expires_at", None)
    return {
        "type": doc.doc_type,
        "doc_type": doc.doc_type,
        "status": st,
        "last_check": lc,
        "expires_at": str(exp)[:10] if exp is not None else None,
        "custom_name": getattr(doc, "custom_name", None),
        "meta": getattr(doc, "meta", None),
    }


async def enforce_pipeline_doc_forward_block(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate_id: str,
    old_stage: Optional[str],
    new_stage: str,
    extra: Dict[str, Any] | None,
    personal: Dict[str, Any] | None,
    gates: HiringPipelineGates | None = None,
) -> None:
    """
    Raise HTTP 409 when moving forward in the pipeline while document blockers apply
    at the *current* stage (same rule as CandidateCard journey).
    """
    if not is_forward_pipeline_move(old_stage, new_stage):
        return

    if _norm_stage_token(new_stage) in TERMINAL_STATUSES:
        return

    resolved_gates = gates or await resolve_hiring_pipeline_gates(
        db, tenant_id, candidate_id=candidate_id
    )

    canon_old = _norm_stage_token(old_stage)
    if not canon_old:
        return

    owner_ctx = _owner_context_for_docs(candidate_id=candidate_id, extra=extra, personal=personal)

    oc_row = await db.execute(
        select(Candidate.own_company_id).where(
            Candidate.id == candidate_id,
            Candidate.tenant_id == tenant_id,
        ).limit(1)
    )
    oc = oc_row.scalar_one_or_none()
    own_company_id = str(oc).strip() if oc else None
    ruleset_version = await documents_crud.ensure_ruleset_seed(
        db,
        tenant_id,
        load_default_ruleset(),
        own_company_id=own_company_id,
    )
    ruleset_payload = normalize_ruleset_payload(ruleset_version.json_data)

    existing_docs = await documents_crud.list_candidate_documents(
        db,
        tenant_id,
        candidate_id,
        include_deleted=False,
        active_own_company_id=own_company_id,
    )
    active_docs = [d for d in existing_docs if getattr(d, "deleted_at", None) is None]
    doc_ids = [str(d.id) for d in active_docs]
    last_checks = await get_last_document_checks_map(db, tenant_id, doc_ids)
    serialized = [_minimal_serialized_doc(d, last_checks.get(str(d.id))) for d in active_docs]

    summary = compute_owner_summary(owner_ctx, ruleset_payload, serialized)
    req = summary.get("required") or {}
    missing = list(req.get("missing") or [])
    problematic = list(req.get("problematic") or [])
    in_progress = list(req.get("in_progress_types") or [])

    # Lazy import: pipeline_overrides_service lives under candidates package (router pulls service).
    from backend.app.api.v1.candidates.pipeline_overrides_service import approved_pipeline_relaxed_types

    relaxed = await approved_pipeline_relaxed_types(db, tenant_id=tenant_id, candidate_id=candidate_id)
    missing, problematic, in_progress = _relax_blocker_lists(missing, problematic, in_progress, relaxed)

    hard_block, _soft = docs_pipeline_blocks_forward_resolved(
        canon_old, missing, problematic, in_progress, resolved_gates
    )
    if not hard_block:
        return

    raise HTTPException(
        status_code=409,
        detail={
            "code": "stage_blocked_by_documents",
            "message": "Cannot move stage forward: required documents are incomplete or need review",
            "missing_types": missing,
            "problematic_types": problematic,
            "in_progress_types": in_progress,
        },
    )


def enforce_pipeline_vacancy_forward_block(
    *,
    old_stage: Optional[str],
    new_stage: str,
    vacancy_id: Optional[str],
    gates: HiringPipelineGates | None = None,
) -> None:
    """
    Raise HTTP 409 when moving forward from contacted / questionnaire_submitted without vacancy_id.
    """
    if not is_forward_pipeline_move(old_stage, new_stage):
        return
    if _norm_stage_token(new_stage) in TERMINAL_STATUSES:
        return
    canon_old = _norm_stage_token(old_stage)
    g = gates or default_hiring_pipeline_gates()
    if not vacancy_gate_applies(canon_old, g):
        return
    vid = str(vacancy_id or "").strip()
    if vid:
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "stage_blocked_by_vacancy",
            "message": "Cannot move stage forward: assign a vacancy (or link this candidate to a vacancy) first",
        },
    )


async def enforce_pipeline_contact_attempt_forward_block(
    db: AsyncSession,
    *,
    tenant_id: str,
    candidate: Candidate,
    old_stage: Optional[str],
    new_stage: str,
    gates: HiringPipelineGates | None = None,
) -> None:
    """
    When contact-attempt tracking is enabled for the candidate, require at least one logged
    attempt before leaving stage **new** (forward only). Mirrors plan §3 (New → contact attempt).
    """
    if not is_forward_pipeline_move(old_stage, new_stage):
        return
    if _norm_stage_token(new_stage) in TERMINAL_STATUSES:
        return
    canon_old = _norm_stage_token(old_stage)
    g = gates or await resolve_hiring_pipeline_gates(db, tenant_id, candidate_id=str(candidate.id))
    if not contact_attempt_gate_applies(canon_old, g):
        return

    policy = await _contact_attempts.get_effective_contact_policy(db, tenant_id, candidate)
    if not policy.get("enabled"):
        return
    n = await _contact_attempts.count_contact_attempts(db, str(candidate.id))
    if n >= 1:
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "stage_blocked_by_contact_attempt",
            "message": "Cannot move stage forward: register at least one contact attempt while the candidate is at New",
        },
    )
