# HR workforce data model (PR-1 foundation)

This document describes the **first-class** persistence introduced for HostFlow HR (Polish Kadry-oriented foundation). It complements `WorkforceEmployee`, `WorkforceEmployment`, and existing payroll/ZUS **operational** satellites (`workforce_payroll_profiles`, `workforce_zus_profiles`) by separating **legal/tax/insurance materialisation** and **HR document context** from recruitment blobs.

## Principles

- **WorkforceEmployee** is the HR aggregate root. **Candidate** is optional historical linkage (`candidate_id`, frozen `candidate_snapshot`), never the primary store for HR compliance.
- Tables are **tenant-scoped** (`tenant_id`) with FK to `workforce_employees.id` and RLS aligned with other `workforce_*` tables on PostgreSQL.
- **No payroll engine** in this layer: numeric tax fields are storage for declared/configured values (e.g. PIT-2 monthly reduction comes from tenant policy / user input, not hard-coded law constants in code).

## Entities

### 1. Tax profile — `workforce_tax_profiles`

One row per `(tenant_id, employee_id)`.

| Column | Type | Notes |
|--------|------|--------|
| `id` | UUID string | PK |
| `tenant_id` | UUID string | FK `tenants.id` |
| `employee_id` | UUID string | FK `workforce_employees.id` CASCADE |
| `tax_residency_country` | string(8), nullable | ISO-like short code |
| `tax_office` | string(64), nullable | US / urząd skarbowy code or label |
| `pit2_submitted` | bool | default false |
| `pit2_monthly_amount` | numeric(12,4), nullable | tenant/user-defined; not a fixed PL default in app code |
| `tax_deductible_costs_type` | string(32), nullable | e.g. standard / elevated |
| `young_person_relief` | bool | default false |
| `created_at` / `updated_at` | timestamptz | |

### 2. Insurance profile — `workforce_insurance_profiles`

One row per `(tenant_id, employee_id)`. Distinct from `workforce_zus_profiles` (which remains payroll-registration workflow storage). This row models **insurance/legal title** materialisation for ZUS workspace and future export.

| Column | Type | Notes |
|--------|------|--------|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK tenants |
| `employee_id` | UUID | FK workforce_employees |
| `zus_title_code` | string(32), nullable | Insurance title code |
| `social_insurance` | string(32), nullable | Status / regime label |
| `health_insurance` | string(32), nullable | |
| `sickness_insurance` | string(32), nullable | |
| `accident_insurance` | string(32), nullable | |
| `zus_registration_type` | string(64), nullable | e.g. ZUA / ZZA / ZWUA family label |
| `registered_at` | date, nullable | |
| `deregistered_at` | date, nullable | |
| `status` | string(32) | default `draft` |
| `created_at` / `updated_at` | timestamptz | |

### 3. HR document context — `workforce_hr_document_contexts`

Many rows per employee. Links a `documents.id` row to HR/e-teczka semantics.

| Column | Type | Notes |
|--------|------|--------|
| `id` | UUID | PK |
| `tenant_id` | UUID | |
| `employee_id` | UUID | FK workforce_employees |
| `document_id` | UUID | FK documents.id |
| `context_type` | string(64) | e.g. `hr_eteczka`, `handoff_mirror` |
| `legal_category` | string(64), nullable | |
| `document_group` | string(64), nullable | |
| `required` | bool | default false |
| `verified` | bool | default false |
| `verification_status` | string(32), nullable | |
| `expires_at` | timestamptz, nullable | |
| `source` | string(64), nullable | `manual`, `import`, `handoff`, … |
| `created_at` / `updated_at` | timestamptz | |

Unique: `(tenant_id, employee_id, document_id)`.

### 4. Compliance state — `workforce_compliance_states`

One row per `(tenant_id, employee_id)`. Holds **persisted** evaluation snapshot for dashboards and exports.

| Column | Type | Notes |
|--------|------|--------|
| `id` | UUID | PK |
| `tenant_id` | UUID | |
| `employee_id` | UUID | FK workforce_employees |
| `status` | string(32) | e.g. `not_evaluated`, `compliant`, … |
| `missing_count` | int | default 0 |
| `expired_count` | int | default 0 |
| `expiring_soon_count` | int | default 0 |
| `high_risk_count` | int | default 0 |
| `cannot_work` | bool | default false |
| `last_evaluated_at` | timestamptz, nullable | |
| `reasons` | JSONB, nullable | array or structured reasons |
| `created_at` / `updated_at` | timestamptz | |

## Application behaviour

- `ensure_workforce_hr_core_profiles` (service): idempotent insert of default tax, insurance, and compliance rows when missing.
- Invoked from `ensure_hr_profiles_bundle` after existing payroll/ZUS/onboarding seeding so **all** creation paths get the foundation.

## Out of scope (later PRs)

- Payroll calculation, KEDU/XML, e-Deklaracje transport, PPK contribution files.
- UI sections for tax/ZUS hub (PR-2+).
