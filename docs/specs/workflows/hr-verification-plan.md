# HR Verification Plan (PR13) — hybrid model

**Status:** Accepted (implemented).  
**Related:** [Data Verification Workspace](hr-data-verification-workspace.md), [PR12 sequential flow](hr-data-verification-workspace.md#ui-review-case-layout-pr12).

**PR14 (deferred):** step status labels, final ready screen, button polish, full E2E path.

---

## Principle

`verification_plan` is **not absolute truth**. It is:

> **system-generated recommendation + hard legal blockers**

| Role | Responsibility |
|------|----------------|
| **Recruitment** | Collect documents, initial classification, handoff package (completeness, vacancy, citizenship) |
| **System** | Calculate tiers, risk/blockers, guide HR — does not replace human legal judgment |
| **HR** | Final control: confirm, reject, return, waive (where allowed), request extra docs |

Neither “HR thinks from scratch” nor “system decides everything”.

---

## Requirement tiers

| Tier | Who defines | Blocks approve | HR override |
|------|-------------|----------------|-------------|
| `hard_blocker` | Backend / legal rules | **Yes** | **No** |
| `required` | Vacancy / client profile / ruleset | Yes (unless waived) | Limited — `waive-requirement` + reason |
| `recommended` | System (optional catalog / ruleset) | **No** | Yes — waive or confirm optionally |
| `hr_requested` | HR (`decision_basis_json.hr_document_requests`) | Yes until satisfied | HR defines |
| `not_required` | System (e.g. transport for non-driver) | No | — |

### Hard blockers (examples)

- Passport / ID (legal identity)
- Active journey steps: legal stay, work permit, red paper when journey requires
- Driver license when position is driver

### Recommended (examples)

- Medical / psych when only in `optionalTypes`
- Optional catalog items for citizenship/vacancy

Stored on each document row: `requirement_tier`, `overridable`, legacy `requirement_level` for UI compat.

Waiver payload (on document verification row):

```json
{ "_requirement_waiver": { "reason": "…", "by_user_id": "…", "at": "…" } }
```

API: `POST …/document-verifications/{document_key}/waive-requirement`  
Body: `{ "reason": "…" }` — returns 422 `CANNOT_WAIVE_HARD_BLOCKER` for Passport / ID and Driver license.

---

## Plan sources

| Source | Data |
|--------|------|
| Candidate | citizenship, work_country, legal_status, profession |
| Vacancy | country, profession, contract_type, category |
| Client profile | `CandidateProfile.document_configs` |
| Ruleset | `compute_candidate_checklist` |
| Journey | work eligibility steps |
| HR | `decision_basis_json.hr_document_requests[]` |

Service: `backend/app/services/hr_verification_plan.py` — `plan_mode: "hybrid"`.

---

## `verification_plan` shape

| Block | Content |
|-------|---------|
| `plan_mode` | `"hybrid"` |
| `hard_blocker_documents` | must confirm; no waiver |
| `required_documents` | vacancy/client; waivable |
| `recommended_documents` | system hint; does not block |
| `hr_requested_documents` | HR-added |
| `blocking_reasons` | `hard_blocker:…` / `required:…` prefixes |
| `can_approve` | plan-level readiness (hard + non-waived required + hr_requested) |

Panel `can_approve` in **hybrid** mode follows `verification_plan` only (PR15). Legacy checklist / verified-fields apply outside hybrid.

---

## HR UI

1. **Main queue** — `hard_blocker` + `required` + `hr_requested`
2. **Recommended** — collapsed; label “HR may waive”
3. **Not required** — collapsed system list
4. Actions per document: fill from scan → confirm / request correction / reject / waive (if `overridable`)

---

## Recruitment handoff

Recruitment should pass the richest possible package. The plan **recomputes** on HR open from live candidate + vacancy + rules — handoff snapshot is input, not the only source.

---

## Approve gate

Backend: `finalize_hr_review_can_approve(panel)` + `plan_blocks_approve(verification_plan)`.  
Frontend: `isHrApproveAllowed(panel)` reads the same `verification_plan`.

### Critical: hybrid mode must not double-gate documents

When `verification_plan.plan_mode === "hybrid"`, do **not** run the legacy loop over `documents_for_approval` inside `finalize_hr_review_can_approve`. Rows without `required: false` would still block approve and break **recommended** / **optional** behaviour.

Document gates = `plan_blocks_approve` only. No parallel checklist, verified-fields, or data-verification gate in hybrid mode.

See `workforce_hr_review.finalize_hr_review_can_approve` and `_assert_can_approve` (hybrid branch).

---

## Acceptance criteria

- [x] Hybrid tiers on every plan document
- [x] Recommended does not block approve
- [x] Hard blockers block without waiver
- [x] Required waivable with reason
- [x] HR-requested docs supported via `decision_basis_json`
- [x] UI + backend share `verification_plan` gates

---

## Implementation

| Area | Path |
|------|------|
| Plan | `backend/app/services/hr_verification_plan.py` |
| Waiver | `backend/app/services/hr_document_verification.py` |
| API | `workforce/router.py`, `handoffs.py` |
| UI | `HrSequentialDocumentVerification.tsx`, `hrDocumentVerificationFields.ts` |
