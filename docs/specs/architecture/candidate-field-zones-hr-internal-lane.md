# Candidate field zones — HR internal-lane PATCH (v1)

This document defines **who may change which candidate fields** when an agency user is on the **internal HR handoff lane** (`agency_candidate_has_internal_hr_handoff_lane` is true).

Enforcement lives in **`assert_hr_internal_lane_patch_keys_allowed`** (see `backend/app/services/candidate_hr_internal_lane_patch.py`), invoked from **`update_candidate_full`** when `actor_role == hr_officer` and the lane is active.

## Zones (conceptual)

| Zone | Examples (candidate row / JSON) | Who may change (typical) |
|------|-----------------------------------|---------------------------|
| **recruitment** | `source`, `origin`, `vacancy_id`, `company_id`, `funnel_id`, `recruiter_id`, `manager` / `manager_id`, `stage`, `status`, `status_reason`, `tags`, `is_favorite`, `languages` | Recruiter / manager **before** recruitment is locked; not `hr_officer` on internal-HR lane |
| **shared_identity** | `first_name`, `last_name`, `phone`, `phone_country_code`, `email`, `birth_date`, `country_code`, `city`, `address`, `personal_data`, `contacts` | **v1:** read-only for `hr_officer` on internal-HR lane (identity participated in recruitment, documents, handoff). Corrections go through a dedicated flow or return-to-recruiter. |
| **hr_workforce** (candidate surface) | `note`, `extra`, `docs_progress` | `hr_officer` **only** when internal-HR lane is active; allowlist is intentionally minimal until workforce UI owns more fields |
| **system_only** | `tenant_id`, `id`, `short_id`, tokens, audit columns | System / migrations only — not via public PATCH |

## HR internal-lane allowlist (v1)

Only these PATCH keys are accepted for `hr_officer` when the lane is active:

- `note` — operational HR notes on the candidate card  
- `extra` — structured JSON used for HR/workspace metadata (bounded by product conventions)  
- `docs_progress` — recruitment document pipeline snapshot HR may adjust operationally  

Any other key in the PATCH body → **HTTP 422** with `detail.code == "hr_field_not_allowed"` and `detail.fields` listing disallowed keys.

## Evolution

- **Identity correction** and **return for recruitment fix** should be first-class actions instead of widening HR PATCH on PII.  
- After workforce modules own employment / ZUS / medical state, candidate-row PATCH for HR may shrink further in favour of workforce APIs.
