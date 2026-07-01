# ZUS Workspace MVP — architecture

## Goal

Operational HR screen: **kogo zgłosić / wyrejestrować / sprawdzić w ZUS**, checklisty rejestracji i wyrejestrowania, kolejka rozliczeń miesięcznych, status eksportu (placeholder) — **bez** integracji ZUS API, KEDU, Płatnika i bez kalkulacji płac.

## Data model

Table **`workforce_zus_workspace_tasks`** (tenant-scoped, RLS like other `workforce_*`):

| Column | Purpose |
|--------|---------|
| `workspace_lane` | `task_queue` \| `form_status` \| `checklist_register` \| `checklist_deregister` \| `monthly_settlement` \| `export_queue` |
| `task_kind` | Stable code, e.g. `registration`, `deregistration`, `monthly_settlement`, or manual labels |
| `form_kind` | Optional: `ZUA`, `ZZA`, `ZWUA`, or `monthly_settlement` (wider string; migration widens column) |
| `form_status` | Optional lifecycle: `not_filed`, `draft`, `submitted`, `accepted`, `rejected`, `unknown` |
| `status` | Includes `pending` for auto-created rows; also `open`, `in_progress`, `blocked`, `done`, `cancelled` |
| `due_at` | Optional deadline |
| `assigned_hr_user_id` | Optional FK to `users` |
| `export_status` | Placeholder: `not_applicable`, `pending`, `placeholder_ready`, `error_placeholder` |
| `checklist_json` | Structured checklist payload (MVP: free-form JSON) |
| `title`, `notes` | Human-readable context |
| `employee_id` | Required link to `workforce_employees` |

## API (MVP)

- `GET /api/v1/workforce/zus-workspace/tasks` — paginated list; query: `status`, `workspace_lane`, `task_kind`, `form_kind`, `due_before`, `due_after`, `assigned_hr_user_id`, `limit`, `offset`.
- `POST /api/v1/workforce/zus-workspace/tasks` — create row (HR validates employee belongs to tenant).
- `PATCH /api/v1/workforce/zus-workspace/tasks/{id}` — partial update.

All endpoints: same HR workspace roles as other workforce HR APIs; activity log on write.

## Auto tasks (`workforce_zus_task_autocreate`)

Service **`backend/app/services/workforce_zus_task_autocreate.py`**: `ensure_zus_registration_task`, `ensure_zus_deregistration_task`, `ensure_zus_monthly_settlement_task`.

**Work eligibility (PR-4)** gates **registration** tasks only: see [work-eligibility-pr4.md](./work-eligibility-pr4.md) and ADR-017. Until `WorkforceWorkEligibilityProfile` allows ZUS (`ready_for_zus` / `eligible_to_work`, or safe `not_evaluated` default), registration auto-tasks are created with `status=blocked` and `checklist_json.blocked_by` instead of premature `pending`.

- **After employee create** (post `ensure_workforce_hr_core_profiles`): optional body fields `initial_insurance_zus_registration_type` + `initial_insurance_status` seed the insurance row; optional `initial_eligibility_status` seeds work eligibility. If status is one of `pending_zus` / `pending_registration` **and** `zus_registration_type` is set, registration ensure runs (blocked or pending per eligibility gate).
- **After `PATCH .../insurance-profile`** when monitored insurance fields change: registration + deregistration ensures as before.
- **After `PATCH .../work-eligibility`**: registration ensure re-runs (unblocks when eligibility becomes ready).
- **Monthly**: unchanged (see script `run_zus_workspace_monthly_cycle.py`).

## UI

HR workspace nav entry **ZUS** → table with filters and link to employee detail (`/app/hr/employees/:id`).

## Non-goals (explicit)

- KEDU generation, real Płatnik/ePłatnik export, payroll engine, ZUS web service integration.
