# ADR-016: ZUS Workspace MVP (operational surface, no ZUS API)

## Status

Accepted — MVP scope (workspace only).

## Context

HR needs a single operational view for Polish social insurance (ZUS) obligations that is **not** the legal insurance profile row and **not** the registration workflow row on the employee card. Those remain:

- **Insurance profile** — juridical materialisation (titles, coverage flags).
- **ZUS registration profile** — process-oriented registration status on the employee.

The workspace is a **tenant-scoped task board**: who must be reported, deregistered, which ZUA/ZZA/ZWUA need review, monthly settlement follow-ups, and a placeholder lane for future exports — without KEDU, Płatnik integration, or payroll math.

## Decision

1. Persist operational items in **`workforce_zus_workspace_tasks`** with:
   - `workspace_lane` — separates task queue, form-status lane, registration/deregistration checklists, monthly settlement, export placeholder.
   - `task_kind` — stable string code for filtering and UI labels.
   - Optional `form_kind` / `form_status` for ZUA/ZZA/ZWUA tracking.
   - `status`, `due_at`, `assigned_hr_user_id`, `checklist_json`, `export_status`, `title`, `notes`.
2. Expose **HR-only** APIs under `/api/v1/workforce/zus-workspace/*` with list filters (status, lane, form kind, due window, assignee).
3. **No** ZUS API, KEDU, ePłatnik, or payroll calculation in this ADR.

## Consequences

- HR can run a ZUS desk from one screen; data is auditable and assignable.
- Later PRs can add auto-materialisation from `WorkforceInsuranceProfile` / `WorkforceZusProfile`, reminders, and real export pipelines without renaming the table.
