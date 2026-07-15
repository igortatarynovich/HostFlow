# Intake Form Purpose — Phase 1 Backend

**Status:** implementation contract (L3 — executes ADR-022)  
**Date:** 2026-07-15  
**ADR:** [ADR-022-intake-form-purpose-and-submission-policy-model.md](../architecture/ADR-022-intake-form-purpose-and-submission-policy-model.md)

---

## Goal

Deliver a narrow backend vertical slice for Product B: B2B public `match_or_create` + personal invite `attach`, with policy snapshot on Submission.

**Process gate:** backend slice was implemented before ADR-022 Accepted — merge requires architecture review + P1 fixes below.

---

## Reuse-first ownership (summary)

| New | Reuses | Does not duplicate |
|-----|--------|-------------------|
| `intake_platform/*` policy + match + submission | Decision Layer, Outcome Executor, IntakeRouter, ingest_runtime | Routing, entity disposition |
| `application_matcher` | `contact_identifiers` | `duplicate_resolution` (Candidate scope) |
| `submission_store` | Lead row + `normalized_merging_lead_persisted_blocks` | Draft session state |

Full matrix: ADR-022 §5.5.

---

## P1 fixes (merge gate — mandatory)

| # | Fix | Status |
|---|-----|--------|
| 1 | `entity_profile_gate.py` bugfix + validation tests | Done |
| 2 | Shared `services/contact_identifiers.py` | Done |
| 3 | Strict match matrix (terminal/abandoned excluded; offering match; both identifiers for strong) | Done |
| 4 | `append_submission` with `SELECT FOR UPDATE` + idempotency key + idempotent re-submit | Done |
| 5 | Preserve `submissions_v1` on Lead normalized PATCH | Done |
| 6 | Exclude `intake_draft_abandoned` from list + monthly lead count | Done |

**Backend merge gate:** ADR-022 Accepted + checklist signed + P1 tests green + backend A/B/C API tests.  
**Release gate (separate):** UI/publication slice + browser walkthrough — not a backend PR blocker.

**Architecture merge request (PR body):** [adr022-phase1-backend-pr-description.md](adr022-phase1-backend-pr-description.md)

---

## Deliverables

### 1. Platform module `backend/app/intake_platform/`

See ADR-022 §5.5. Shared normalization: `backend/app/services/contact_identifiers.py`.

### 2. Schema migration `202607151000_adr022_form_purpose`

Fields on `tenant_lead_forms` and `publication_config_v1` on `intake_source_profiles` — **schema prep only** for versioning/publication; not full versioning.

### 3. Service wiring

| File | Change |
|------|--------|
| `intake_form_write_service.py` | purpose, policy, gate validation |
| `seed_targeted_advertising_form.py` | system preset + `match_or_create` |
| `lead_questionnaire_invite.py` | forced attach + async submission append |
| `intake.py` submit | client path → `submit_client_public_intake_with_policy` |
| `lead_communications.py` | preserve `submissions_v1` on normalized merge |
| `_listing.py`, `lead_quota.py` | exclude abandoned drafts |

### 4. Tests

| Test | Scenario |
|------|----------|
| `test_adr022_intake_policy_phase1.py` | Public match/create/attach + invite + idempotent submit |
| `test_adr022_p1_fixes.py` | Gate validation |
| `test_sales_targeted_advertising_intake.py` | Regression |

---

## Not implemented (Phase 1)

- Immutable published versions / publish workflow
- Publication CRUD / multi-campaign first-class
- Review Queue UI
- Candidate matching
- Full offering/campaign admin UI

---

## Rollout order

1. Freeze new features
2. P1 fixes + tests
3. Architecture review → ADR-022 **Accepted** (incl. multi-form scalability §9)
4. Merge backend slice
5. Next slice: **Product B walkthrough** (UI/publication — not full Form Definition editor)

## Development filter (post-merge)

**Model:** [`release-revenue-flow-audit.md`](../release-revenue-flow-audit.md) §0 — Foundation → Scenario Step → Revenue Flow. Progress = passable steps, not Foundation merges.

Next Scenario Step PRs: **B-1** (`F3-B-02`, `F3-B-03`) → **B-2** (`F3-B-04`..`F3-B-07`). Each must state **Operator gain**.
