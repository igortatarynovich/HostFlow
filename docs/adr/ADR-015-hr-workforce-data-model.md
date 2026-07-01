# ADR-015: HR workforce core data model (tax, insurance, document context, compliance state)

## Status

Accepted

## Context

HostFlow HR is being shaped as a Polish-style **Kadry + payroll preparation + compliance** contour, not a single “employee card” backed by ad-hoc JSON (`meta`, `candidate_snapshot`) and derived-only dashboard signals.

Legal and payroll-prep attributes must live in **first-class tables** so that:

- ZUS workspace, PIT/PPK flows, HR document hub (e-teczka), and compliance dashboards can evolve without rewriting read-models on every feature.
- **WorkforceEmployee** remains the HR root aggregate; **Candidate** stays historical context (never primary SoT for HR operations).

## Decision

Introduce four tenant-scoped tables keyed by `workforce_employees.id`:

1. **`workforce_tax_profiles`** — one row per employee (PIT-oriented fields; amounts are tenant-configurable, not hard-coded).
2. **`workforce_insurance_profiles`** — one row per employee (ZUS / social insurance title and component flags; not a payroll calculation engine).
3. **`workforce_hr_document_contexts`** — links `documents` to an employee with HR/e-teczka semantics (`context_type`, `legal_category`, verification, expiry, `source`).
4. **`workforce_compliance_states`** — one row per employee storing **materialised** compliance counters and flags plus `reasons` JSON for auditability (complements derived queues used in directory/profile).

On every **employee materialisation** path (`create_employee`, `handoff_from_candidate` / `ensure_hr_profiles_bundle`), the application **ensures** empty/default rows exist for tax, insurance, and compliance state (idempotent).

This ADR does **not** adopt: payroll calculation, KEDU/XML export, e-Deklaracje submission, or PPK file generation.

## Consequences

- New migrations and ORM models must stay in sync; RLS on PostgreSQL follows existing `workforce_*` patterns (`tenant_id`).
- Directory / operational read-models may later **read** `workforce_compliance_states` when evaluation jobs write it; until then derived logic can coexist.
- `workforce_hr_document_contexts` allows HR to classify recruitment-originated documents without treating Candidate APIs as the HR operating surface.

## References

- Spec: `docs/specs/architecture/hr-workforce-data-model.md`
- Related: `docs/hr/ADR-001-workforce-employee-vs-app-user.md`, `docs/specs/architecture/ADR-002-modular-recruitment-hr-boundary.md`
