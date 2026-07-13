# PR 2B-4 — Fleet Migration Reuse Review

**ADR:** [ADR-018](../architecture/ADR-018-requirement-policy-evaluation-model.md)  
**Goal:** Extend the existing single-candidate migration script into a fleet-wide audit & migration tool — no second migration framework.

## Existing assets reviewed

| Asset | Path | Reuse decision |
|-------|------|----------------|
| Single-candidate migration CLI | `backend/scripts/migrate_candidate_adr018_evaluation.py` | **Extend in place** — becomes thin CLI over shared package |
| Policy pin / resolve | `backend/app/services/requirement_policy_assignment.py` | **Reuse** — `pin_requirement_policy`, `resolve_policy_ref_for_candidate`, `ensure_driver_ce_policy_pin` |
| Evaluation bridge | `backend/app/requirement_rules/evaluation/candidate_bridge.py` | **Reuse** — `evaluate_candidate_requirements_v2`, `load_document_data_contracts_for_candidate` |
| Document type registry | `backend/app/document_types/registry.py` | **Reuse** — `normalize_input_doc_type`, `is_canonical_code`, `is_runtime_alias` |
| DocumentData adapter | `backend/app/document_hub/document_data_contract.py` | **Reuse** — contract build + schema validation for audit |
| Document type code audit | `backend/scripts/audit_document_type_codes.py` | **Reference only** — static codebase scan; fleet tool audits DB rows per candidate |
| Candidate evidence service | `backend/app/services/candidate_evidence_service.py` | **Reuse patterns** — variant lookup; supersede via status flip (history preserved) |
| Stage guard (post-cutover) | `backend/app/services/candidate_doc_pipeline_guard.py` | **Consumer** — not used by migration; audit compares evaluator vs stage |
| Fingerprint | `backend/app/requirement_rules/evaluation/fingerprint.py` | **Reuse** — post-migration fingerprint in audit record |

## Not found (no separate backfill tools)

- No fleet candidate backfill scripts beyond S3 upload helpers.
- **Version resolver added (2B-4.1):** `document_type_version_assignment_resolver.py`
- No standalone document canonicalization migration script — normalization at apply + version assignment

## Extension strategy

1. **Package:** `backend/app/requirement_rules/migration/` — audit, classify, apply, batch, review queue, report.
2. **CLI:** same script path, new flags (`--audit-only`, `--tenant-id`, `--vacancy-id`, `--candidate-ids`, `--only-safe`, `--apply`, `--resume`, `--limit`, `--export-report`).
3. **Review queue:** read-model exported in batch JSON report (`review_queue[]`); not a new SSOT table in this PR.
4. **Apply idempotency:** skip pin if already pinned to target policy; skip doc normalize if already canonical; supersede only active **standard** manual evidence; store audit record in `candidate.extra.adr018_migration`.

## Protected manual evidence (never auto-supersede)

Variant codes matching: `waiver`, `attestation`, `registry`, `no_file` (ADR-018 §14.2.5).

## Auto-fix forbidden (review queue only)

- Guess `additional_document` / `unclassified` type
- Change citizenship / residency basis
- Create missing documents
- Mark requirements fulfilled manually
- Roll back stage
- Override ambiguous policy assignment

## Evaluation invalidation note

Requirement evaluation is **computed on demand** (no materialized cache in 2B-3). Consumers re-call `evaluate_candidate_requirements_v2` when inputs change. Triggers that must invoke evaluation (stage guard, checklist, workspace):

- document upload / replacement / review / expiry metadata change
- citizenship / residency / work access change
- vacancy / policy assignment change
- process state / waiver / attestation change

Stage guard and checklist already call v2 per request; no stale-cache layer to invalidate in this PR.

## P0 — new candidate creation

`ensure_driver_ce_policy_pin` exists but was **not wired** at candidate INSERT — fixed in this PR inside `create_candidate_full`.

## Cleanup deferred (post fleet migration)

- `slot_evaluator.py` Driver CE paths
- legacy standard evidence endpoints
- `owner_summary.py` projection-only cutover
- unused legacy aliases
- one-off migration helpers after fleet apply completes
