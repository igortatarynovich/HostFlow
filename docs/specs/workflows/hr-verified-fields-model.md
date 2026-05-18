# HR Verified Fields Model (PR4)

## Goal

Establish a **source of truth (SoT)** for employment-case data that will later feed contracts, ZUS, applications, and payroll prep — without OCR or automatic contract push in this phase.

## Data model

Table: `workforce_hr_verified_fields`

- One row per `(tenant_id, hr_review_id, field_code)`
- Status: `pending` | `verified` | `conflict` | `overridden`
- `verified_value`, `source_document_id`, `source_document_key`
- `document_verification_id` — link to PR3 verification card
- `verified_by_user_id`, `verified_at`
- `override_reason`, `conflict_reason`
- Audit via `workforce.hr_review.verified_field.*` activity events

## Critical fields (approve gate)

- `full_name`, `citizenship`, `work_country`, `pesel`, `document_expiry`, `permit_type`
- Approve requires each critical field in `verified` or `overridden`
- `conflict` or `pending` blocks approval

## Population

1. Panel load: `ensure_critical_field_placeholders` creates `pending` rows.
2. Document **Verify** (PR3): confirmed fields from `reviewed_fields_json` upsert into SoT.
3. Conflicting values from a second verified document set `conflict` status.
4. HR **override** endpoint sets `overridden` with reason (audit).

## APIs

- `GET …/hr-review/verified-fields` — list (employee or handoff scope)
- `POST …/hr-review/verified-fields/{field_code}/override` — manual override
- `HrReviewPanel` includes `verified_fields` + `verified_fields_summary`

## Out of scope (PR4)

- OCR / auto-extraction
- Push to merge documents or contracts
- Profile write-back from verified values

## Deploy

Apply migration `202605181500_hr_verified` after `202605181400_hr_doc_verify`.
