# HR Employment Identity Read Adapter (PR6+)

**Status:** Implemented.  
**Related:** [Identity projection](hr-employment-identity-projection.md), [Contract generation](hr-contract-generation-mvp.md), [Data verification](hr-data-verification-workspace.md).

## Goal

Standardize **trusted reads** for downstream processes. Read contract only — not automation.

## Entry points

- `get_trusted_employment_identity(db, tenant_id, review_id, consumer, …)`  
- `get_trusted_employment_identity_for_employee(db, tenant_id, employee_id, consumer, …)` — resolves review, then delegates  

Internal (no consumer guard): `load_employment_identity_projection`.

### Operational note (recursion guard)

`get_trusted_employment_identity_for_employee` calls:

```text
ensure_hr_review_for_employee(..., sync_from_sources=False)
```

So journey build → `evaluate_permit_application` → trusted read does **not** re-enter `_sync_review_from_sources` → `build_work_eligibility_journey` (fixes `RecursionError` on handoff/employee hr-review).

Panel build still uses `sync_from_sources=True` (default) once per request.

## Consumers (v1)

| Consumer | Purpose |
|----------|---------|
| `contract_generation` | Merge / contract templates |
| `zus_preparation` | ZUS registration prep |
| `payroll_prep` | Payroll onboarding |
| `permit_application` | Permit filings (journey step) |
| `export` | HR exports |
| `client_form` | Client-facing forms |
| `hr_review_display` | Case UI (never raises) |

## Access matrix

| Projection status | contract / ZUS / payroll / permit | export / client_form | hr_review_display |
|-------------------|-----------------------------------|----------------------|-------------------|
| `complete` | allowed | allowed | allowed |
| `stale` | **blocked** | allowed | allowed |
| `incomplete` | blocked | blocked | allowed |
| `conflicted` | blocked | blocked | allowed |

Denied automation: `TrustedIdentityAccessError` (`TRUSTED_IDENTITY_STALE`, …).

## Forbidden for downstream

- `employee.candidate_snapshot` as trust source  
- Raw `reviewed_fields_json`  
- Document meta for identity fields  

## Wired modules

| Module | Consumer |
|--------|----------|
| `document_merge/context.py`, `generate.py` | `contract_generation` |
| `workforce_zus_task_autocreate.py` | `zus_preparation` |
| `workforce_hr_satellites` (payroll patch) | `payroll_prep` |
| `workforce_work_eligibility_journey.py` | `permit_application` |
| `workforce_downstream_identity.py` | all `evaluate_*` helpers |

## PR8 — prep status + merge variables

- `GET …/employees/{id}/trusted-identity/prep-status`  
- Merge: `{{ trusted_identity.legal_name }}`, `bindings["trusted_identity.*"]`  
- `apply_trusted_identity_merge_variables` in `workforce_downstream_identity.py`

## PR9 — contract draft preview

`POST …/contract-generation/preview` — see [hr-contract-generation-mvp.md](hr-contract-generation-mvp.md).  
Frontend preview panel: **not yet merged** (component exists locally).

## Next

- Contract preview UI  
- Finalization (send / sign / ePUAP) after preview UX stable
