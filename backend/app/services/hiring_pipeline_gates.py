"""
Tenant-configurable hiring pipeline gates (FINAL plan §3 / §12 / §13).

DEPRECATED (P6): runtime resolution prefers Process Engine transition rules
(`pe_transition_rules`, profile-scoped). This tenant settings blob remains as
legacy fallback and for the Settings → Hiring Pipeline Gates editor until removed.
Stored under Tenant.settings["hiring_stage_gates_v1"].
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.constants.stages import PIPELINE_COMPLETED_STAGE_CODES
from backend.app.services.document_catalog import normalize_doc_type
from backend.app.services.pipeline_override_policy import NON_OVERRIDABLE_DOC_TYPES

SETTINGS_KEY = "hiring_stage_gates_v1"

_DEFAULT_STAGES_WITHOUT_DOC: FrozenSet[str] = frozenset(
    {"new", "no_answer", "contacted", "questionnaire_submitted"}
)
_DEFAULT_VERIFY_UPLOADS: FrozenSet[str] = frozenset(
    {
        "docs_got",
        "permit_ordered",
        "permit_received",
        "visa",
        "red_paper",
        "trip_plan",
        "at_client",
        "employment_pending",
        "on_trip",
        "employed",
        "probation_ok",
        "ready_for_handoff",
        "processing_by_client",
        "docs_submitted_permit",
        "handoff_returned",
    }
)
_DEFAULT_VACANCY_STAGES: FrozenSet[str] = frozenset({"contacted", "questionnaire_submitted"})
_DEFAULT_CONTACT_ATTEMPT_STAGES: FrozenSet[str] = frozenset({"new"})


def _norm_stage_token(s: str) -> str:
    return str(s or "").strip().lower()


def _as_frozenset(key: str, raw: Any, default: FrozenSet[str], *, max_items: int = 80) -> FrozenSet[str]:
    if raw is None:
        return default
    if not isinstance(raw, list):
        return default
    out: set[str] = set()
    for item in raw:
        v = _norm_stage_token(str(item))
        if not v or len(v) > 64:
            continue
        out.add(v)
        if len(out) >= max_items:
            break
    return frozenset(out) if out else default


def _as_extra_non_overridable(raw: Any, *, max_items: int = 40) -> FrozenSet[str]:
    if raw is None or not isinstance(raw, list):
        return frozenset()
    out: set[str] = set()
    for item in raw:
        c = normalize_doc_type(str(item))
        if c:
            out.add(c)
        if len(out) >= max_items:
            break
    return frozenset(out)


def _as_bool(raw: Any, default: bool) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)) and raw in (0, 1):
        return bool(raw)
    if isinstance(raw, str):
        s = raw.strip().lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off"):
            return False
    return default


@dataclass(frozen=True)
class HiringPipelineGates:
    """Resolved gates for one tenant (merged defaults + settings)."""

    stages_without_doc_pipeline_block: FrozenSet[str]
    stages_verify_uploads_block_forward: FrozenSet[str]
    stages_require_vacancy_for_forward: FrozenSet[str]
    contact_attempt_gate_stages: FrozenSet[str]
    stages_doc_block_soft_only: FrozenSet[str]
    non_overridable_doc_types_extra: FrozenSet[str]
    # When False: skip hard 409 for requirement/doc forward blocks and ready_for_handoff transfer policy.
    enforce_requirement_stage_blocks: bool = True

    def effective_non_overridable_doc_types(self) -> FrozenSet[str]:
        return NON_OVERRIDABLE_DOC_TYPES | self.non_overridable_doc_types_extra


def default_hiring_pipeline_gates() -> HiringPipelineGates:
    return HiringPipelineGates(
        stages_without_doc_pipeline_block=_DEFAULT_STAGES_WITHOUT_DOC,
        stages_verify_uploads_block_forward=_DEFAULT_VERIFY_UPLOADS,
        stages_require_vacancy_for_forward=_DEFAULT_VACANCY_STAGES,
        contact_attempt_gate_stages=_DEFAULT_CONTACT_ATTEMPT_STAGES,
        stages_doc_block_soft_only=frozenset(),
        non_overridable_doc_types_extra=frozenset(),
        enforce_requirement_stage_blocks=True,
    )


def merge_hiring_pipeline_gates(raw: Optional[Dict[str, Any]]) -> HiringPipelineGates:
    base = default_hiring_pipeline_gates()
    if not raw or not isinstance(raw, dict):
        return base
    return HiringPipelineGates(
        stages_without_doc_pipeline_block=_as_frozenset(
            "stages_without_doc_pipeline_block",
            raw.get("stages_without_doc_pipeline_block"),
            base.stages_without_doc_pipeline_block,
        ),
        stages_verify_uploads_block_forward=_as_frozenset(
            "stages_verify_uploads_block_forward",
            raw.get("stages_verify_uploads_block_forward"),
            base.stages_verify_uploads_block_forward,
        ),
        stages_require_vacancy_for_forward=_as_frozenset(
            "stages_require_vacancy_for_forward",
            raw.get("stages_require_vacancy_for_forward"),
            base.stages_require_vacancy_for_forward,
        ),
        contact_attempt_gate_stages=_as_frozenset(
            "contact_attempt_gate_stages",
            raw.get("contact_attempt_gate_stages"),
            base.contact_attempt_gate_stages,
        ),
        stages_doc_block_soft_only=_as_frozenset(
            "stages_doc_block_soft_only",
            raw.get("stages_doc_block_soft_only"),
            frozenset(),
        ),
        non_overridable_doc_types_extra=_as_extra_non_overridable(raw.get("non_overridable_doc_types_extra")),
        enforce_requirement_stage_blocks=_as_bool(
            raw.get("enforce_requirement_stage_blocks"),
            base.enforce_requirement_stage_blocks,
        ),
    )


def hiring_gates_from_tenant_settings(settings: Optional[Dict[str, Any]]) -> HiringPipelineGates:
    if not settings or not isinstance(settings, dict):
        return default_hiring_pipeline_gates()
    raw = settings.get(SETTINGS_KEY)
    if raw is None:
        return default_hiring_pipeline_gates()
    if not isinstance(raw, dict):
        return default_hiring_pipeline_gates()
    return merge_hiring_pipeline_gates(raw)


async def resolve_hiring_pipeline_gates(
    db: AsyncSession,
    tenant_id: str,
    *,
    candidate_id: str | None = None,
) -> HiringPipelineGates:
    """Resolve hiring pipeline gates — PE transition rules first, tenant settings fallback."""
    if candidate_id:
        from backend.app.process_engine.transition_rules_adapter import (
            resolve_hiring_pipeline_gates_for_candidate,
        )

        gates, _meta = await resolve_hiring_pipeline_gates_for_candidate(
            db,
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
        )
        return gates

    from backend.app.api.v1.tenants import service as tenant_service

    tenant = await tenant_service.get_tenant(db, tenant_id)
    if tenant is None:
        return default_hiring_pipeline_gates()
    return hiring_gates_from_tenant_settings(tenant.settings if isinstance(tenant.settings, dict) else None)


def docs_pipeline_blocks_forward_resolved(
    canonical_stage: str,
    missing: list[str],
    problematic: list[str],
    in_progress: list[str],
    gates: HiringPipelineGates,
) -> tuple[bool, bool]:
    """
    Returns (hard_blocks, soft_warn_only).
    hard_blocks: forward must be rejected server-side.
    soft_warn_only: true when stage is in soft-only set and docs would otherwise hard-block
    (caller may still allow move — server skips 409 for soft).
    """
    if not gates.enforce_requirement_stage_blocks:
        return False, False

    code = (canonical_stage or "").strip().lower()
    if not code:
        return False, False

    if code in PIPELINE_COMPLETED_STAGE_CODES:
        return False, False

    would_hard = False
    if code not in gates.stages_without_doc_pipeline_block:
        if missing or problematic:
            would_hard = True
        elif code in gates.stages_verify_uploads_block_forward and in_progress:
            would_hard = True

    if not would_hard:
        return False, False

    if code in gates.stages_doc_block_soft_only:
        return False, True

    return True, False


def vacancy_gate_applies(canon_old: str, gates: HiringPipelineGates) -> bool:
    c = (canon_old or "").strip().lower()
    return c in gates.stages_require_vacancy_for_forward


def contact_attempt_gate_applies(canon_old: str, gates: HiringPipelineGates) -> bool:
    c = (canon_old or "").strip().lower()
    return c in gates.contact_attempt_gate_stages


def serialize_gates_public(gates: HiringPipelineGates) -> Dict[str, Any]:
    eff = sorted(gates.effective_non_overridable_doc_types())
    return {
        "version": 1,
        "enforce_requirement_stage_blocks": bool(gates.enforce_requirement_stage_blocks),
        "stages_without_doc_pipeline_block": sorted(gates.stages_without_doc_pipeline_block),
        "stages_verify_uploads_block_forward": sorted(gates.stages_verify_uploads_block_forward),
        "stages_require_vacancy_for_forward": sorted(gates.stages_require_vacancy_for_forward),
        "contact_attempt_gate_stages": sorted(gates.contact_attempt_gate_stages),
        "stages_doc_block_soft_only": sorted(gates.stages_doc_block_soft_only),
        "non_overridable_doc_types_extra": sorted(gates.non_overridable_doc_types_extra),
        "effective_non_overridable_doc_types": eff,
        "deprecated_tenant_settings_key": SETTINGS_KEY,
        "deprecation_note": (
            "Runtime gates resolve from pe_transition_rules (profile-scoped). "
            "This settings blob is legacy fallback / editor storage only."
        ),
    }


def patch_settings_dict(
    current: Optional[Dict[str, Any]],
    patch: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge patch into hiring_stage_gates_v1 bucket; replace lists when provided."""
    root: Dict[str, Any] = dict(current) if isinstance(current, dict) else {}
    prev = root.get(SETTINGS_KEY)
    bucket: Dict[str, Any] = dict(prev) if isinstance(prev, dict) else {}
    for k, v in patch.items():
        if v is None:
            bucket.pop(k, None)
        else:
            bucket[k] = v
    if not bucket:
        root.pop(SETTINGS_KEY, None)
    else:
        root[SETTINGS_KEY] = bucket
    return root
