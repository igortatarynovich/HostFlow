# HR Employment Identity Read Adapter (PR6)

## Goal

Standardize **trusted reads** of canonical employment identity for downstream processes. Not automation — a read contract only.

## Entry point

`employment_identity_read_adapter.get_trusted_employment_identity(db, tenant_id=…, review_id=…, consumer=…)`

Helper: `get_trusted_employment_identity_for_employee` when only `employee_id` is known.

Internal build (no guard): `load_employment_identity_projection` — verified fields → projection only.

## Consumers (v1)

| Consumer | Purpose |
|----------|---------|
| `contract_generation` | Merge / contract templates |
| `zus_preparation` | ZUS registration prep |
| `payroll_prep` | Payroll onboarding |
| `permit_application` | Permit filings |
| `export` | HR exports |
| `client_form` | Client-facing forms |
| `hr_review_display` | Case workspace UI (never raises) |

## Access matrix

| Projection status | contract / ZUS / payroll / permit | export / client_form | hr_review_display |
|-------------------|-----------------------------------|----------------------|-------------------|
| `complete` | allowed | allowed | allowed |
| `stale` | **blocked** | allowed | allowed |
| `incomplete` | blocked | blocked | allowed (read) |
| `conflicted` | blocked | blocked | allowed (read) |

Denied automation reads raise `TrustedIdentityAccessError` with `code` e.g. `TRUSTED_IDENTITY_STALE`.

## Forbidden for downstream (use adapter instead)

- `employee.candidate_snapshot`
- Raw employee profile as trust source
- `reviewed_fields_json`
- Document meta / file metadata for identity fields

## Out of scope (PR6)

- Contract generation, ZUS export, payroll run
- UI beyond existing identity summary (panel uses `hr_review_display`)
- Profile write-back

## PR7 — Wired consumers

| Module | Consumer | Behavior |
|--------|----------|----------|
| `document_merge/context.py` | `contract_generation` | `trusted_identity` bindings; no candidate legal fields when employee present |
| `document_merge/generate.py` | — | Raises `ValueError(TRUSTED_IDENTITY_*)` when blocked |
| `workforce_zus_task_autocreate.py` | `zus_preparation` | Blocks ZUS registration task with `identity_block_code` |
| `workforce_hr_satellites.patch_payroll_profile` | `payroll_prep` | Blocks `ready_for_payroll` / `sent_to_accounting` |

Service: `workforce_downstream_identity.py` — `evaluate_*_preparation`, `DownstreamIdentityPrepResult`.

## Next

Additional consumers (export, client_form, permit_application) and merge template variable migration.
