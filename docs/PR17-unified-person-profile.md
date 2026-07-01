# PR17 — Candidate → employee handoff (notes)

**Canonical spec:** [PR17-candidate-to-employee-handoff-spec.md](./PR17-candidate-to-employee-handoff-spec.md)

**Status:** Planned (after PR15).  
**Scope:** Handoff field/document mapping + HR employee card as primary HR surface — **not** Person Profile merge, **not** new backend aggregate.

> **Rule:** HR and Recruitment stay separate modules; employee card is populated from candidate at handoff.

---

## Problem

Backend correctly grew **engines** (ruleset, plan, journey, checklist, blockers, verifications).  
But those engines were also exposed as **parallel product surfaces** that the UI must orchestrate:

| Layer today | Examples |
|-------------|----------|
| Recruitment person | `Candidate`, handoff |
| Workforce person | `WorkforceEmployee`, employments |
| HR case | `WorkforceHrReview`, `hr-review` panel |
| Eligibility engine | `work-eligibility`, `work-eligibility/journey` |
| Compliance / payroll | `hr-bundle`, `operational-profile`, per-domain PATCH endpoints |
| Document ops | `hr-review/document-verifications/*`, verified-fields, checklist patch |

The frontend then built a **quasi-HR app** (`/app/hr/employees/:id`, handoff detail, inbox) instead of extending **one person card**.

**Technical debt:** complexity is fine **inside** services; it is harmful **on the wire** as ten entry points for one human.

---

## Principle

> **Engines stay. Public contract shrinks.**

- **Internal (keep):** `verification_plan`, `hr_document_verification`, `hr_verified_fields`, `workforce_work_eligibility_journey`, checklist sync, blockers recompute, `finalize_hr_review_can_approve`, handoff orchestration, ruleset/checklist resolution.
- **External (one primary read model):** **Person Profile API** — sections the UI renders, not engines the UI assembles.

---

## Current public surfaces (inventory — 2026-05)

### Workforce employee (primary HR zoo)

| Endpoint | Role today | PR17 target |
|----------|------------|-------------|
| `GET /workforce/employees/{id}/operational-profile` | Fat read-model for “employee workspace” | **Fold into** person profile `employment` + `timeline` |
| `GET /workforce/employees/{id}/hr-bundle` | Parallel aggregate | **Fold into** person profile or internal-only |
| `GET /workforce/employees/{id}/hr-review` | HR case BFF (`mode`, hero, plan, checklist, blockers, …) | **Section** `hr_verification` on person profile; keep PATCH/POST actions under stable subpaths |
| `GET .../work-eligibility/journey` | Raw engine steps for legacy UI | **Internal**; expose `eligibility_summary` only |
| `PATCH .../work-eligibility` | Profile edit | **Action** on person profile or nested `employment.eligibility` |
| `PATCH .../hr-review/checklist/{code}` | Manual checklist (non-hybrid) | **Deprecated** for UI; engine-only / admin |
| `GET .../hr-review/verified-fields` | Raw SoT rows | **Inside** `hr_verification` section, not standalone list page |
| `GET .../hr-review/document-verifications` | Duplicate of plan docs | **Prefer** `verification_plan` slice; deprecate list endpoint for UI |
| Many `PATCH .../payroll-profile`, `zus`, `tax`, `compliance-state`, … | CRUD slices | **Sections** on person profile; writes can stay as sub-resources initially |

### Handoff (duplicate HR case surface)

| Endpoint | PR17 target |
|----------|-------------|
| `GET /handoffs/{id}/hr-review` (+ same doc-verify tree) | **Same** `hr_verification` builder keyed by `handoff_id` until employee exists; inbox links **deep-link to person**, not a second case universe |

### HR inbox / dashboard

| Endpoint | PR17 target |
|----------|-------------|
| `GET /hr/inbox`, `/hr/dashboard`, … | **Queue only** — rows resolve to `person_id` + `section=hr_verification` |

### Candidate (canonical person root)

| Endpoint | PR17 target |
|----------|-------------|
| `GET /candidates/{id}` (+ documents, pipeline) | **Canonical shell**; after hire, person profile extends candidate with `workforce_employee_id` |

---

## Target: Person Profile API (v1 contract sketch)

**Canonical identity:** `candidate_id` (always). Optional `workforce_employee_id` when hired.

```
GET /api/v1/people/{candidate_id}/profile
```

Response sections (stable names for UI tabs):

| Section | Contents (derived, not raw engines) |
|---------|-------------------------------------|
| `personal_data` | Name, contacts, IDs visible to role |
| `documents` | Unified document index (recruitment + workforce context); open/download refs |
| `recruitment_state` | Stage, vacancy, handoffs summary, locks |
| `employment_state` | Employee row, employments, status, hire metadata |
| `hr_verification` | `review_status`, `verification_plan`, `documents_for_approval`, `verified_fields_summary`, `can_approve`, `blockers` (user-facing strings only), `next_action` |
| `eligibility_summary` | Status, blocking reasons, fee state, **no** raw journey step dump |
| `tasks_actions` | Actionable CTAs (approve, request correction, open doc, mark paid) |
| `timeline` | Merged audit/events |

**Writes:** keep existing command endpoints during transition; UI calls them from person profile actions. Phase 2 may alias them under `/people/{id}/actions/...`.

**Explicitly not in primary read model:**

- Raw `checklist[]` as editable surface (hybrid uses plan + doc verifications).
- Raw `blockers_json` / engine codes without labels.
- Full `journey.steps` graph (use summary + deep internal endpoint if debug needed).
- Duplicate `operational-profile` + `hr-bundle` + `hr-review` fetches for one paint.

---

## Frontend alignment (same PR17 program)

| Stop | Replace with |
|------|----------------|
| `HrEmployeeDetailPage` as primary person UI | Extend `CandidateCard` (or shared `PersonProfilePage`) |
| `/app/hr/employees/:id` as main entry | Redirect → `/app/candidates/:id#employment` (or dedicated tab) |
| `WorkEligibilityJourneyWorkspace` as primary | Section `eligibility_summary` + compact actions |
| Handoff detail as full HR case page | Inbox → open person profile at `hr_verification` |
| `isEmploymentCaseWorkspace` fork (two UIs in one file) | Single layout; sections gated by `employment_state` / `review_status` |

---

## Phased delivery (avoid big-bang)

### Phase A — Contract + read path (backend)

1. Add `GET /people/{candidate_id}/profile` (BFF) composing existing services.
2. Map `employee_id` → `candidate_id` for redirects.
3. Mark redundant reads `@deprecated` in OpenAPI (operational-profile for UI, journey GET for UI).
4. No engine deletion.

### Phase B — UI entry (frontend)

1. Person profile shell on candidate card.
2. HR verification section consumes `profile.hr_verification` only (one GET).
3. `/app/hr/employees/:id` → redirect.

### Phase C — Surface removal

1. Remove UI calls to deprecated endpoints.
2. Narrow `hr-review` GET to internal/admin if still needed for debugging.
3. Delete duplicate handoff/employee HR panel builders → single `build_hr_verification_section(person_ctx)`.

---

## Acceptance criteria

- [ ] One primary GET loads person card HR+employment context (≤1 round-trip for read-mostly view).
- [ ] UI does not call `operational-profile` + `hr-review` + `work-eligibility/journey` together for standard paint.
- [ ] Inbox/handoff deep-links open **person profile**, not a separate HR case SPA.
- [ ] Checklist PATCH not required for hybrid approve path in UI.
- [ ] Engines unchanged: PR15 approve gate still passes regression.
- [ ] OpenAPI documents Person Profile as **stable**; legacy endpoints tagged deprecated with removal target.

---

## Out of scope (PR17)

- Rewriting `verification_plan` logic.
- PR16 recruitment package rules (may consume person profile read when ready).
- PR14 visual polish (can target new sections).

---

## Dependencies

| PR | Relation |
|----|----------|
| PR15 | Merge first; do not alter hybrid approve semantics in PR17 |
| PR-INFRA | Independent |
| PR14 | Freeze new HR pages; only section-level UX inside person profile |
| PR16 | Should read recruitment package from person profile, not new surface |

**Roadmap order:** PR-INFRA → PR15 → **PR17** (profile collapse) → PR16 (or PR16 after PR17 Phase A if package API must land earlier — document decision in PR16).
