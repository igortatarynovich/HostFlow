# HR Verified Fields Model (PR4+)

**Status:** Implemented.  
**Related:** [Data Verification Workspace](hr-data-verification-workspace.md), [Document verification PR3](hr-review-task-priority-v1.md#pr-3--document-verification-cards-).

## Goal

**Source of truth (SoT)** for employment-case data feeding contracts, ZUS, permit applications, and payroll prep — populated when HR verifies documents, not by re-typing recruitment data.

## Data model

Table: `workforce_hr_verified_fields`

- One row per `(tenant_id, hr_review_id, field_code)`
- Status: `pending` | `verified` | `conflict` | `overridden`
- `verified_value`, `source_document_id`, `source_document_key`
- `document_verification_id` — link to PR3 verification card
- `profile_values_json` — snapshot of confirmed `current_profile_values` at verify time
- `verified_by_user_id`, `verified_at`, `override_reason`, `conflict_reason`
- Audit: `workforce.hr_review.verified_field.*`

## Critical fields (approve gate)

`full_name`, `citizenship`, `work_country`, `pesel`, `document_expiry`, `permit_type`

Approve requires each critical field in `verified` or `overridden`. `conflict` / `pending` blocks approval.

Also surfaced via `data_verification_summary.ready_for_approval` and derived `identity_verified` checklist sync (PR10).

## Population

1. Panel load: `ensure_critical_field_placeholders` → `pending` rows.  
2. Document **Verify** (PR3): confirmed `reviewed_fields_json` → `sync_from_document_verification`.  
3. Second document with conflicting value → `conflict`.  
4. HR **override** → `overridden` with reason.

## Recruiter-facing values (PR11, not SoT until verified)

Displayed in verification UI via `fields_to_review[].current_profile_values` and `data_verification_items[].recruiter_profile_values`.

**Source priority** (`FIELD_SPECS.profile_keys` order):

1. `handoff.candidate.*` — `candidate_handoff_snapshots.payload` ([`hr_handoff_profile_context.py`](../../../backend/app/services/hr_handoff_profile_context.py))  
2. `employee.*`, `eligibility.*`  
3. `snapshot.*` — employee `candidate_snapshot`  
4. `document.*`, `context.*`

SoT remains **`workforce_hr_verified_fields`** only after HR confirm/verify.

## Extended field codes (PR11)

| `field_code` | Typical document |
|--------------|------------------|
| `driver_license_categories` | Driver license |
| `code95_expiry` | Code95 |
| `tacho_card_expiry` | Tacho card |

Catalog: `backend/app/services/hr_verified_field_catalog.py`.

## APIs

- `GET …/hr-review/verified-fields`  
- `POST …/hr-review/verified-fields/{field_code}/override`  
- `HrReviewPanel`: `verified_fields`, `verified_fields_summary`, **`data_verification_items`**, **`data_verification_summary`** (PR10)

## Deploy

Migrations: `202605181400_hr_doc_verify` → `202605181500_hr_verified`.

## Out of scope

- OCR / auto-extraction  
- Automatic profile write-back from verified values  
- Contract send / sign / ePUAP (PR9 preview only)
