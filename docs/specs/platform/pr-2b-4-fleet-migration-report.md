# PR 2B-4.1 — Hardening before fleet apply

## Critical gap closed: `document_type_version_id`

**Resolver:** `backend/app/services/document_type_version_assignment_resolver.py`

Deterministic rules:
1. Existing assigned version verified against canonical type → keep
2. Single date-compatible + schema-compatible version → assign
3. Multiple versions → choose by document `created_at` within `[valid_from, valid_to]`; never latest-only
4. Ambiguous / none → `IssueCategory.document_version_unresolved` → not `safe_auto_migration`

Apply step `assign_document_type_versions` persists FK when resolver status is `existing` or `resolved`.

## Safe auto-migration criteria (all required)

- Policy resolvable and pinned
- Canonical document types
- Version assigned (existing or resolvable)
- DocumentData schema-valid for approved participating documents
- Citizenship/residency sufficient
- Manual evidence supersede-eligible only (not operator decision / protected / approved+linked docs)
- No unclassified docs affecting requirements
- Evaluator completes without blocking unresolved
- No `document_version_unresolved`

## Candidate creation — single hook

**Service:** `backend/app/services/candidate_creation_service.py` → `finalize_new_candidate_record()`

Wired from:
- `create_candidate_full` (all API, lead conversion, import, intake bootstrap paths)
- `telegram_intake/candidate_link._create_candidate_from_telegram_intake` (legacy direct INSERT)

Canonical creation remains `create_candidate_full`; non-canonical telegram path now calls the same finalize hook.

## `candidate.extra.adr018_migration` — minimal marker only

```json
{
  "migration_version": "2B-4.1",
  "status": "migrated",
  "input_fingerprint": "...",
  "migrated_at": "...",
  "run_id": "..."
}
```

Full audit lives in exported batch JSON (`aggregate`, `review_queue`, redacted `candidates[]`).

## Review queue export

- Stable `issue_id` (sha256 of run_id + candidate + categories)
- `run_id` persisted across resume checkpoint
- `previous_fingerprint` from prior migration marker
- Dedup via `seen_issue_ids` in checkpoint
- Redacted exports (no schema error values / extracted PII)

## Stage inconsistency split

| Issue | Meaning | Action |
|-------|---------|--------|
| `stage_historical_permitted_now_stricter` | Passed under old guard; docs present | Compliance review; no rollback |
| `stage_data_corruption_or_missing` | Missing/invalid docs or evaluation mismatch | High-priority review |

## Before `--apply --only-safe`

1. Fleet dry-run all tenants → analyze `aggregate` block
2. Fix systemic version/schema/policy gaps
3. Repeat dry-run until `safe_auto_migration` fingerprint-stable
4. Apply in small tenant batches
