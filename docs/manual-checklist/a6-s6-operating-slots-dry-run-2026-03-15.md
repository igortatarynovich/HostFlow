# A6-S6 Operating Company Slots Dry-Run Report

- Generated at (UTC): `2026-03-15T10:32:38.843479+00:00`
- Tenants audited: `4`
- Overflow tenants (`used > effective_limit`): `0`
- Tenants with legacy slot keys: `0`
- Tenants without `tenant_licenses` row: `1`

## Per-tenant table

| tenant_slug | plan | included | extra(canonical) | effective | used_operating | overflow | suggested_extra_no_data_loss | legacy_keys_present | raw_slot_values |
|---|---:|---:|---:|---:|---:|---|---:|---|---|
| `tenant-01` | `starter` | 1 | 0 | 1 | 0 | NO | 0 | `-` | `{"extra_operating_company_slots":0,"additional_operating_company_slots":0,"operating_company_addon_slots":0}` |
| `tenant-02` | `agency_basic` | 10 | 0 | 10 | 0 | NO | 0 | `-` | `{"extra_operating_company_slots":0,"additional_operating_company_slots":0,"operating_company_addon_slots":0}` |
| `tenant-03` | `trial` | 1 | 0 | 1 | 0 | NO | 0 | `-` | `{"extra_operating_company_slots":0,"additional_operating_company_slots":0,"operating_company_addon_slots":0}` |
| `tenant-04` | `-` | 0 | 0 | ∞ | 0 | NO | 0 | `-` | `{"extra_operating_company_slots":0,"additional_operating_company_slots":0,"operating_company_addon_slots":0}` |

## Recommended transition actions

1. Normalize all tenant subscription payloads to canonical key `extra_operating_company_slots` and remove legacy aliases.
2. For tenants in overflow, do not delete companies; keep data as-is and block only new operating company creation until limits match.
3. If Product approves grace-policy, set temporary `extra_operating_company_slots = suggested_extra_no_data_loss` for overflow tenants.
4. Attach this report to release evidence before switching A6-S6 to DONE.
