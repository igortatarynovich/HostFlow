# PR17 — Candidate → Employee HR profile handoff (spec)

**Type:** Handoff mapping + HR employee card UX — **not** a new Person aggregate, **not** merging Recruitment/HR modules, **not** rewriting verification engines.

**Rule:** Recruitment and HR stay separate. After internal HR handoff, HR opens **the employee card** (`/app/hr/employees/:id`) already filled from the candidate card (fields + documents + verification task).

**Out of scope:** New `Person` API, redirecting HR to `/app/candidates/:id`, `verification_plan` rewrite, PR15 approve gate, PR14 style-only work.

---

## 1. Correct product model

| Module | Owns | After handoff |
|--------|------|----------------|
| **Recruitment** | `Candidate`, pipeline, handoff request | Candidate row stays; stage → `processing_by_hr` |
| **HR** | `WorkforceEmployee`, HR review, eligibility, payroll satellites | Employee row created or linked; data **copied/synced** from candidate |

One human, **two module boundaries** — not one merged UI product.

---

## 2. What happens today (code facts)

### Accept internal HR handoff (`accept_handoff` → `accept_internal_hr_handoff`)

| Tenant flag | On accept |
|-------------|-----------|
| **Legacy** (`delayed_hr_workforce_creation` = false) | `handoff_from_candidate` → employee + `ensure_hr_operational_context` + checklist activities |
| **Stage B delayed** (flag = true) | **No employee yet** — only `ensure_hr_review_for_handoff` (review row, `employee_id` null) |

### Employee creation (`workforce_employees.handoff_from_candidate`)

Copies into `WorkforceEmployee`:

- `display_name`, `candidate_id`, `company_id`, `vacancy_id`, `recruiter_user_id`, `own_company_id`
- `candidate_snapshot` — **minimal** JSON: `first_name`, `last_name`, `email`, `phone`, `company_id`, `vacancy_id`, `stage`, `status`, `captured_at`
- `meta.source` = `recruitment_handoff`, `meta.internal_hr_handoff_id` after accept
- `ensure_hr_profiles_bundle` (empty shells: payroll, ZUS, work eligibility, etc.)

**Does not copy today:** `personal_data`, `extra`, `contacts`, full document payloads, recruitment checklist state into employee fields.

### Documents (`ensure_hr_operational_context`)

When employee **exists**:

- Links all active **candidate** documents → `DocumentEntityLink` (`reused_for_hr`, `workforce_employee`)
- Creates `WorkforceHrCase`
- Calls `ensure_hr_review_for_employee`

When **delayed workforce**: document links run only after **approve** materializes employee.

### HR review / verification task

- Review row: `WorkforceHrReview` (by `employee_id` or `handoff_id` + `candidate_id`)
- UI task: `GET .../hr-review` panel → `mode`, `current_task`, `verification_plan`, `next_action`
- Inbox queue: `operational_queue` on `/api/v1/hr/inbox` handoff rows

### Where HR opens the person today

| Entry | Route | Component |
|-------|-------|-----------|
| Employee list / inbox (approved) | `/app/hr/employees/:id` | `HrEmployeeDetailPage` |
| Handoff / inbox (in review) | `/app/hr/handoffs/:id` | `HrHandoffDetailPage` |
| Candidate | `/app/candidates/:id` | `CandidateCard` (no first-class link to HR employee card) |

---

## 3. Why the card feels “empty” or “legacy zoo”

| Symptom | Cause |
|---------|--------|
| Empty / thin profile | `candidate_snapshot` is minimal; operational profile reads snapshot + empty bundle shells |
| No documents on employee | Delayed workforce: no employee → no `DocumentEntityLink` until approve; or links exist but UI uses wrong section |
| Legacy eligibility + compliance tables | `HrEmployeeDetailPage`: when `hr-review` loads → case blocks on top; **`!caseWorkspace`** branch still renders `WorkEligibilityJourneyWorkspace`, payroll, compliance (lines ~366–596) |
| Two “products” | Separate handoff page vs employee page; duplicate verification surfaces |
| 422 broke case UI | Backend bug (`vacancy.meta`) → `hrReview` null → **only** legacy branch rendered |

Fixing PR17 does **not** require merging routes into CandidateCard unless product explicitly chooses that later. Primary fix: **fill employee card from handoff** + **one coherent employee layout**.

---

## 4. PR17 deliverables (mapping matrix)

Document and implement:

### 4.1 Field mapping (candidate → employee / HR satellites)

| Source (candidate) | Target (HR) | Today |
|--------------------|-------------|-------|
| `first_name`, `last_name`, `email`, `phone` | `display_name`, snapshot | Partial |
| `personal_data` (citizenship, PESEL, address, …) | `WorkEligibilityProfile`, verified fields seeds | **Gap** |
| `extra` (role, documents flags, …) | `meta`, position_category, plan context | **Gap** |
| `vacancy_id` | `employee.vacancy_id`, employment row | Partial |
| Handoff snapshot JSON | `WorkforceHrCase.meta` / review `decision_basis` | Partial |

### 4.2 Document mapping

| Step | Today | PR17 target |
|------|-------|-------------|
| Copy/link docs on handoff accept | Links when employee exists | **Always** after accept (or explicit pre-employee link to `candidate_id` on review) |
| Employee documents API | `GET .../employees/:id/documents` | Same docs visible as recruitment |
| Verification rows | `verification_plan` + doc verifications | HR fields created from linked doc types |

### 4.3 HR fields for documents

| Engine | Role |
|--------|------|
| `hr_verification_plan` | Which docs to verify (unchanged) |
| `hr_document_verification` | Per-doc state (unchanged) |
| `hr_verified_fields` | Critical fields from docs (unchanged) |

PR17: ensure plan sees linked candidate docs after handoff, not empty legacy rows.

### 4.4 “Verify documents” task visibility

| Surface | PR17 |
|---------|------|
| HR Inbox row | Clear CTA → **employee card** `#hr-verification` (or handoff until employee exists) |
| `panel.current_task` / `next_action` | Prominent on employee card header |
| Onboarding tasks | `documents_hr_review` activity from `_ensure_internal_hr_handoff_checklist_activities` |

### 4.5 Employee card UI (HR module)

| Change | PR17 |
|--------|------|
| Primary layout | **Employee card** = HR home for hired person |
| Case mode | Verification section primary; legacy journey/payroll **secondary** (collapsed), not same scroll |
| Handoff page | Thin redirect or embed → employee card when `workforce_employee_id` set |
| Link from candidate | Optional chip “Open in HR” → `/app/hr/employees/:id` |

---

## 5. Redirect / alias strategy (HR stays HR)

| URL | PR17 behavior |
|-----|----------------|
| `/app/hr/employees/:employeeId` | **Stays** canonical HR card (no redirect to candidate) |
| `/app/hr/handoffs/:handoffId` | If `workforce_employee_id` → redirect to employee `#hr-verification`; else minimal handoff pickup UI |
| `/app/candidates/:id` | Unchanged; optional link-out to HR employee |

**Deprecated (conceptual, not delete):** Treating handoff detail as a second full HR product surface.

---

## 6. Internal / admin (unchanged)

- `work-eligibility/journey` — engine/debug, not primary card hero
- Raw checklist PATCH — hybrid path unused in UI
- ZUS workspace, compliance queues — lane tools linking to employee card

---

## 7. Acceptance criteria

- [x] After accept (non-delayed tenant): open `/app/hr/employees/:id` — name, recruitment snapshot, **linked documents** visible without manual re-upload.
- [x] After accept (delayed): open handoff/inbox — see verify task; after approve, same document visibility on employee card.
- [x] `personal_data` / key eligibility fields pre-filled on work eligibility profile where candidate had them.
- [x] HR inbox “HR review” opens employee card (or handoff only when no employee yet), not a parallel case universe.
- [x] Employee card: verification block is primary; legacy operational sections not duplicated above it on same page.
- [x] PR15 hybrid approve regression still passes.
- [x] Mapping doc in repo lists every field/doc path (this spec §4 filled in implementation PR).

---

## 8. Suggested implementation phases

| Phase | Work |
|-------|------|
| **17.1** | Mapping audit + enrich `handoff_from_candidate` / `ensure_hr_operational_context` (snapshot + profile seed from candidate) |
| **17.2** | Document link on delayed path at accept; handoff → employee redirect when `workforce_employee_id` present |
| **17.3** | `HrEmployeeDetailPage` layout: case-first, legacy collapsed; inbox/list links |
| **17.4** | Candidate card “Open in HR” + tests |

---

## References

- `backend/app/services/workforce_employees.py` — `handoff_from_candidate`, `_candidate_snapshot`
- `backend/app/services/workforce_hr_operational_context.py` — document links
- `backend/app/services/hr_acceptance_orchestrator.py` — accept / delayed paths
- `hostflow-frontend/src/pages/hr/HrEmployeeDetailPage.tsx` — dual layout
- `hostflow-frontend/src/utils/hrEmploymentCaseMode.ts` — case vs legacy switch
