# Staging acceptance — targeted-advertising questionnaire (PR-2b)

**Date (UTC):** 2026-07-14T17:06:10Z  
**Environment:** local Docker (`hostflow-backend-1`, `hostflow-db-1`, Caddy → `hostflow.cc`)  
**Branch:** `stage-1a/pr-1-client-account-foundation`  
**Verdict:** **PASS** (API runbook 12/12; UI verified after `npm run build`)

## Identifiers

| Item | Value |
|------|-------|
| Tenant ID | `11111111-1111-1111-1111-111111111111` |
| Own company (active session) | `188b1b20-1948-4017-ada0-c0c838281e7b` (Host Flow) |
| Lead ID (acceptance run) | `aa93bdde-baf6-4fd4-a673-98634e284f4e` |
| Sales inquiry path | `/app/sales/inquiries/aa93bdde-baf6-4fd4-a673-98634e284f4e` |
| Invite token | `eM0A9CWJBfLsYnBsVg9bNAYYTTLeHJ8h` |
| Public apply URL | `/public/apply/eM0A9CWJBfLsYnBsVg9bNAYYTTLeHJ8h` |
| Converted ClientAccount ID | `98c2e6cd-4dff-4f8c-b151-14e3e600e86f` |

UI spot-check lead/token (pre-submit): `c135c88f-56ae-4174-8d7a-9236754324fa` / `TqK0AebHIRG1eGyPyMIzrvvG2QSVkn4n`

## Network evidence (Sales questionnaire-invite contract)

Actor: active tenant admin `uos-rec-3bad7c63@hostflow.test` with `X-Own-Company-Id: 188b1b20-…`.

### Before Wyślij (step 3)

```
POST /api/v1/leads/{lead_id}/questionnaire-invite  {"mark_sent": false}
→ 404  {"detail":"No questionnaire invite exists for this lead"}
```

No invite row created; no status/token mutation.

### After Wyślij (step 4)

```
POST /api/v1/leads/{lead_id}/questionnaire-invite  {"mark_sent": true}
→ 200
{
  "token": "eM0A9CWJBfLsYnBsVg9bNAYYTTLeHJ8h",
  "status": "sent",
  "sent_at": "2026-07-14T17:06:11.284426Z",
  "apply_url": "/public/apply/eM0A9CWJBfLsYnBsVg9bNAYYTTLeHJ8h"
}
```

### After refresh (step 5)

```
POST /api/v1/leads/{lead_id}/questionnaire-invite  {"mark_sent": false}
→ 200  (same token, status still "sent")
```

Token stable: **yes** (`eM0A9C…` unchanged).

### After submit (step 10)

```
POST /api/v1/leads/{lead_id}/questionnaire-invite  {"mark_sent": false}
→ 404  (no new invite; row count = 1)
```

## Public form (steps 6–9)

- `GET /api/v1/public/apply/{token}` → **29** fields, **18** `single_select`/`multi_select`, API `options: null` (frontend catalogs).
- UI (`https://hostflow.cc/public/apply/TqK0Aeb…`) after dist rebuild: **radio** widgets with PL labels (not text enum inputs).
- Submit payload (client_acquisition branch, hidden fields omitted):

```json
{
  "service_sales.targeted_advertising.need_type": "client_acquisition",
  "service_sales.targeted_advertising.primary_outcome": "more_inquiries",
  "service_sales.targeted_advertising.promotion_subject": "service",
  "service_sales.targeted_advertising.industry": "transport",
  "service_sales.targeted_advertising.client_geo_scope": "poland",
  "service_sales.targeted_advertising.conversion_destination": "whatsapp",
  "service_sales.targeted_advertising.offer_ready": "ready",
  "service_sales.targeted_advertising.marketing_materials": ["photos", "logo"],
  "service_sales.targeted_advertising.prior_ads_experience": "no",
  "service_sales.targeted_advertising.monthly_ad_budget": "2000_5000",
  "service_sales.targeted_advertising.start_timeline": "two_weeks",
  "service_sales.targeted_advertising.decision_maker": "owner",
  "service_sales.targeted_advertising.contact_full_name": "Staging Runbook",
  "service_sales.targeted_advertising.contact_company_name": "Staging Runbook Sp. z o.o.",
  "service_sales.targeted_advertising.contact_phone": "+48111222333",
  "service_sales.targeted_advertising.contact_email": "staging-runbook@example.com"
}
```

```
POST /api/v1/public/apply/{token}/submit → 200
lead.normalized.sales_questionnaire_status → "submitted"
sales_questionnaire.recruitment_roles → absent
```

## convert-client (steps 11–12)

Requires **active** converting user (`administrator@hostflow.dev` is `is_active=false` → 422 "Company owner/manager must be active"; not a questionnaire defect).

With active admin `3bad7c63-ae7a-4015-b8b9-b9d444a6d96d`:

```
POST /api/v1/leads/{lead_id}/convert-client → 200  converted_client_id=98c2e6cd-4dff-4f8c-b151-14e3e600e86f
POST /api/v1/leads/{lead_id}/convert-client → 200  same converted_client_id (idempotent)
```

## Defects / notes

| # | Severity | Finding |
|---|----------|---------|
| — | — | **No blocking defects** in questionnaire capability path. |
| N1 | Ops | Stale `hostflow-frontend/dist` before `npm run build` served text inputs on public form; rebuild required for UI acceptance. |
| N2 | Data | Default staging admin `administrator@hostflow.dev` is inactive; use active tenant user for convert-client smoke. |

## Runbook script

Reproducible API trace: `backend/scripts/staging_questionnaire_runbook.sh` (logs `EVIDENCE|…` lines).

## Next step (post-merge only)

Auto-seed `targeted-advertising` intake form on tenant provisioning (idempotent; lazy backfill for legacy tenants).
