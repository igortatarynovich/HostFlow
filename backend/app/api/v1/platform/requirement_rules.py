"""Read/evaluate Requirement Rules API (P1)."""

from __future__ import annotations

from typing import Any, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.auth.deps import get_current_user, require_roles
from backend.app.auth.hiring_workspace_roles import HIRING_CANDIDATE_PROFILE_READ_ROLES
from backend.app.db.deps import get_db_with_tenant
from backend.app.requirement_rules.constants import VALID_CONTEXTS
from backend.app.requirement_rules.facade import evaluate_entity_requirements, resolve_requirement_rule_set
from backend.app.requirement_rules.registry import RequirementRulesNotFoundError

router = APIRouter(
    prefix="/platform/requirement-rules",
    tags=["requirement-rules"],
    redirect_slashes=False,
)


class RequirementRuleOut(BaseModel):
    rule_type: str
    source: str
    source_ref: Optional[str] = None
    target: str
    level: str = "blocking"
    context: str
    reason_code: Optional[str] = None
    qualified_code: Optional[str] = None
    document_type_code: Optional[str] = None
    pack_code: Optional[str] = None
    verification: Optional[str] = None


class RequirementRuleSetOut(BaseModel):
    contract_version: str
    entity_profile_code: str
    entity_type: Optional[str] = None
    context: str
    document_pack_code: Optional[str] = None
    process_profile_code: Optional[str] = None
    rule_sources_applied: List[dict[str, str]] = Field(default_factory=list)
    rules: List[RequirementRuleOut]
    p1_sources_only: bool = True
    excluded_sources: List[str] = Field(default_factory=list)


class RequirementEvaluateIn(BaseModel):
    entity_profile_code: str = Field(..., min_length=1, max_length=191)
    context: Literal["intake", "card_save", "transition", "handoff", "readiness"] = "readiness"
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    normalized_payload: dict[str, Any] = Field(default_factory=dict)
    documents: List[dict[str, Any]] = Field(default_factory=list)


class RequirementFieldGapOut(BaseModel):
    qualified_code: str
    level: str
    reason_code: str
    source: Optional[str] = None
    source_ref: Optional[str] = None


class RequirementDocumentGapOut(BaseModel):
    document_type_code: str
    pack_code: Optional[str] = None
    level: str
    verification: Optional[str] = None
    reason_code: str
    source: Optional[str] = None
    source_ref: Optional[str] = None


class RequirementBlockerOut(BaseModel):
    code: str
    message: str
    source_rule_id: str
    layer: str = "requirement_rules"
    qualified_code: Optional[str] = None
    document_type_code: Optional[str] = None


class RequirementEvaluationOut(BaseModel):
    evaluation_version: str
    entity_profile_code: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    context: str
    required_fields: List[RequirementFieldGapOut]
    required_documents: List[RequirementDocumentGapOut]
    blockers: List[RequirementBlockerOut]
    warnings: List[RequirementBlockerOut]
    satisfied: bool
    rule_sources_applied: List[dict[str, str]] = Field(default_factory=list)
    evaluated_at: str
    p1_sources_only: bool = True


def _validate_context(context: str) -> str:
    ctx = str(context or "readiness").strip().lower()
    if ctx not in VALID_CONTEXTS:
        raise HTTPException(status_code=422, detail=f"Invalid context: {context}")
    return ctx


@router.get(
    "/{entity_profile_code}",
    response_model=RequirementRuleSetOut,
    dependencies=[Depends(require_roles(*HIRING_CANDIDATE_PROFILE_READ_ROLES))],
)
async def get_requirement_rules(
    entity_profile_code: str,
    context: str = Query(default="readiness"),
    ctx_user=Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> RequirementRuleSetOut:
    db, tenant_id = db_tenant
    eval_context = _validate_context(context)
    try:
        payload = await resolve_requirement_rule_set(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=entity_profile_code,
            context=eval_context,
        )
    except RequirementRulesNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RequirementRuleSetOut.model_validate(payload)


@router.post(
    "/evaluate",
    response_model=RequirementEvaluationOut,
    dependencies=[Depends(require_roles(*HIRING_CANDIDATE_PROFILE_READ_ROLES))],
)
async def post_requirement_rules_evaluate(
    body: RequirementEvaluateIn,
    ctx_user=Depends(get_current_user),
    db_tenant: tuple = Depends(get_db_with_tenant),
) -> RequirementEvaluationOut:
    db, tenant_id = db_tenant
    try:
        result = await evaluate_entity_requirements(
            db,
            tenant_id=str(tenant_id),
            entity_profile_code=body.entity_profile_code,
            context=body.context,
            normalized_payload=body.normalized_payload,
            documents=body.documents,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
        )
    except RequirementRulesNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RequirementEvaluationOut.model_validate(result)
