# PR 2B-3 Cutover Report

**Date:** 2026-07-13  
**Status:** Complete  
**ADR:** ADR-018

## Runtime cutover

| Before | After |
|--------|-------|
| 3 blocker sources (manual evidence checklist, owner_summary fallback, shadow v2) | **1** — `RequirementEvaluationService` |
| Stage guard ~514 LOC with legacy paths | **~230 LOC** thin adapter |
| Shadow mode + divergence logs | **Removed** |
| Checklist from slot evaluator + manual evidence | **v2 evaluation DTO** |
| Handoff gate from legacy v1 evaluator | **v2 requirement gate** |

## Removed from stage guard path

- `_requirement_fulfillment_blockers`
- `_legacy_document_type_blockers`
- `_owner_context_for_docs` / `_minimal_serialized_doc`
- `_shadow_requirement_evaluation_if_enabled`
- `REQUIREMENT_EVALUATION_SHADOW`
- `shadow_comparator.py` (deleted)

## Files deleted

- `backend/app/requirement_rules/evaluation/shadow_comparator.py`

## Files added / major changes

- `backend/app/requirement_rules/evaluation/workspace_adapter.py`
- `backend/scripts/migrate_candidate_adr018_evaluation.py`
- `backend/tests/requirement_rules/evaluation/test_stage_guard_cutover_2b3.py`
- Rewritten: `backend/app/services/candidate_doc_pipeline_guard.py`
- Updated: `candidate_evidence_service.build_requirements_checklist`, `requirements_workspace_service`, `transition_bridge`

## Remaining legacy (non–Driver CE runtime, isolated)

| Asset | Status | Consumers |
|-------|--------|-----------|
| `slot_evaluator.py` | Legacy unit tests + non-CE profiles | Not imported by stage guard |
| `requirement_slots.v1.json` | Deprecated catalog | Slot evaluator only |
| `owner_summary.py` | Document module read-model | Intake/telegram/documents router — **not stage gate** |
| Manual evidence API | Waiver/attestation only | `candidate_requirements.py` mutations retained |

## Yurchuk migration

Script: `backend/scripts/migrate_candidate_adr018_evaluation.py`

```bash
python3 backend/scripts/migrate_candidate_adr018_evaluation.py \
  --candidate-id 5d4953de-4ced-4512-b4e3-7d38511938e1 \
  --tenant-id <tenant_uuid> \
  --target-stage permit_ordered
```

Steps: pin policy → supersede manual evidence → recalculate → print requirement report.

## Feature flags removed

- `REQUIREMENT_EVALUATION_SHADOW`

## Tests

- 41 evaluation package tests passing (2B-1 + 2B-2 + 2B-3 cutover)
- Stage guard source scan asserts no owner_summary / shadow / legacy symbols

## Architectural boundaries verified

- Stage guard imports only `evaluate_candidate_requirements_v2` (Recruitment adapter → platform evaluation)
- Hub does not import requirement policy
- Evaluation service has no DB access
- Frontend receives `requirement_evaluation_v2` in workspace payload (display-only)

## Blocker sources: before → after

**Before:** manual evidence checklist | owner_summary ruleset | (shadow) v2  
**After:** `requirement_evaluation_v2` only

Driver CE document contour is architecturally complete after this PR.
