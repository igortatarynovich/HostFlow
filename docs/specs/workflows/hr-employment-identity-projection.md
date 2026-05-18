# HR Employment Identity Projection (PR5)

## Goal

Derive a **canonical employment identity** read-model from `workforce_hr_verified_fields` only. Not hand-editable; not written back to employee profile.

## Projection

Service: `employment_identity_projection.py`

Attributes (v1):

| Attribute | Verified field source |
|-----------|----------------------|
| legal_name | full_name |
| citizenship | citizenship |
| pesel | pesel |
| permit_type | permit_type |
| permit_expiry | document_expiry (Work permit / Legal stay) |
| residence_basis | permit_type or work_country |
| medical_expiry | exam_valid_until (Medical) |
| psychotests_expiry | exam_valid_until (Psychological) |
| birth_date, passport_number, driver_license_categories, code95_expiry | reserved (no SoT field yet) |

## Status

- `complete` — required attrs present, no conflicts
- `incomplete` — missing required (`legal_name`, `citizenship`)
- `conflicted` — any mapped source field in conflict
- `stale` — required complete but an expiry attribute is in the past

## API / UI

- `HrReviewPanel.employment_identity` — computed on panel build
- Case workspace: **Employment identity summary** (read-only)

## Out of scope (PR5)

- Contract / ZUS / payroll consumers
- Persisted projection table
- Field history UI (provenance detail is in `attribute_meta` only)

## Next

Downstream modules read `employment_identity` (or re-call builder) instead of candidate snapshot.
