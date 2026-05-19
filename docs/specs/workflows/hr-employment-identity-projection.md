# HR Employment Identity Projection (PR5+)

**Status:** Implemented.  
**Related:** [Verified fields](hr-verified-fields-model.md), [Read adapter](hr-employment-identity-read-adapter.md).

## Goal

Canonical **employment identity** derived from `workforce_hr_verified_fields` only. Not hand-editable; no write-back to employee profile.

## Projection

Service: `employment_identity_projection.py`

| Attribute | Verified field | Source documents (typical) |
|-----------|----------------|----------------------------|
| legal_name | full_name | any |
| citizenship | citizenship | Legal stay, … |
| pesel | pesel | Red paper |
| permit_type | permit_type | Work permit |
| permit_expiry | document_expiry | Work permit, Legal stay |
| residence_basis | permit_type / work_country | Legal stay, Work permit |
| medical_expiry | exam_valid_until | Medical |
| psychotests_expiry | exam_valid_until | Psychological |
| driver_license_categories | driver_license_categories | **Driver license** (PR11) |
| code95_expiry | code95_expiry | **Code95** (PR11) |
| tacho_card_expiry | tacho_card_expiry | **Tacho card** (PR11) |
| birth_date, passport_number | reserved | no SoT field yet |

## Status

- `complete` — required attrs present, no conflicts  
- `incomplete` — missing `legal_name` / `citizenship`  
- `conflicted` — mapped source field in conflict  
- `stale` — expiry attribute in the past (`permit_expiry`, `medical_expiry`, `psychotests_expiry`, `code95_expiry`, `tacho_card_expiry`)

## API / UI

- `HrReviewPanel.employment_identity` — on panel build (via adapter, `hr_review_display`)  
- **PR10 UI:** compact strip inside `HrDataVerificationWorkspace` (`HrEmploymentIdentityCompact`), not a full second table  

## Out of scope

- Persisted projection table  
- Direct reads from candidate snapshot in automation (use adapter)

## Consumers

All automation via [employment identity read adapter](hr-employment-identity-read-adapter.md).
