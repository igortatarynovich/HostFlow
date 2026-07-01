# Work eligibility & ZUS dependency (PR-4)

## Goal

Encode **citizenship / legal stay / work permit / red paper** state before ZUS registration is actionable, especially for **non-EU drivers** in Poland.

## Data

- **`workforce_work_eligibility_profiles`**: one row per `(tenant_id, employee_id)`; RLS like other `workforce_*`.
- **`work_permit_submission_channels`**: reference rows (`country`, `voivodeship`, `permit_type`, `submission_method`, `portal_url`, …) for HR guidance (empty until content ops seed).
- **`workforce_work_eligibility_payment_requirements`**: per-employee fee rows (`work_permit_fee`, `red_paper_fee`) with `payment_status`, amounts, `blocks_step`, optional `receipt_document_id`. Seeded when profile matches **third-country driver** (`foreign_driver_fee_rows_expected`). RLS by `tenant_id`.

## Rules (v1)

Implemented in `backend/app/services/workforce_work_eligibility_rules.py`:

- Explicit `eligibility_status` in `ZUS_REGISTRATION_ALLOWED_STATUSES` → ZUS registration **allowed** only if **fee rows** (when present) are not stuck in `required` without `paid` / `waived` / `not_required`.
- Status in `ZUS_REGISTRATION_BLOCKED_STATUSES` → ZUS registration **blocked** with mapped `blocked_by`.
- `not_evaluated` + **foreign driver heuristic** ( `position_category=driver`, third-country `citizenship`, no `work_permit_received_at`, `requires_work_permit` not `False` ) → **blocked** until permit path is closed.

**Fee gates** (`validate_work_eligibility_profile_patch`):

- Cannot set `work_permit_application_status` to submitted-like values or `work_permit_submitted_at` until **work permit fee** is satisfied.
- Cannot set `red_paper_status` to ordered-like values until **red paper fee** is satisfied.
- Cannot set `eligibility_status` to `ready_for_zus` / `eligible_to_work` until both fee rows are satisfied (or absent).

EU/EEA/CH citizenship list is a static ISO2 allowlist (extend as product requires).

## HR tasks

On work-eligibility PATCH, `ensure_fee_onboarding_tasks` idempotently adds onboarding checklist rows with `meta.task_kind`:

`pay_work_permit_fee`, `upload_work_permit_fee_confirmation`, `pay_red_paper_fee`, `upload_red_paper_fee_confirmation`.

## ZUS integration

`ensure_zus_registration_task` (see `workforce_zus_task_autocreate.py`) creates or updates the operational **registration** task:

- `status=blocked` + `checklist_json.blocked_by` when gate is blocked (includes `work_permit_fee` / `red_paper_fee` when those rows are unpaid).
- `status=pending` when gate allows (promotes from blocked when eligibility improves).

`PATCH /workforce/employees/{id}/work-eligibility/payment-requirements/{rid}` updates a fee row and re-runs `ensure_zus_registration_task`.

## HR journey read-model

`GET /workforce/employees/{id}/work-eligibility/journey` returns ordered steps (`legal_stay` → … → `eligible_to_work`) with `status`, `blockers`, `required_documents`, optional payment / portal links, and `recommended_next_action`. Implemented in `workforce_work_eligibility_journey.py` (derived from profile, fee rows, insurance, ZUS gate, optional `work_permit_submission_channels` portal URL).

## Next steps (later PRs)

- Full rules engine output: ordered required documents, external links resolution from `work_permit_submission_channels`, HR document context groups (`legal_stay`, `work_permit`, …).
- Gate monthly settlement or other lanes if compliance requires it.
