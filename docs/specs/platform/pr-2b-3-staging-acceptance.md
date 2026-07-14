# Staging acceptance — targeted-advertising questionnaire (PR-2b)

**Date (UTC):** 2026-07-14T17:06:10Z  
**Environment:** local Docker (`hostflow-backend-1`, `hostflow-db-1`, Caddy → `hostflow.cc`)  
**Branch:** `stage-1a/pr-1-client-account-foundation` (merged via PR #3)  
**Verdict:** **PASS** (API runbook 12/12; UI verified after `npm run build`)

> **Security:** acceptance invite tokens were revoked after the run. This document stores masked identifiers only — no live public bearer tokens, PII, or full submit payloads.

## Identifiers

| Item | Value |
|------|-------|
| Tenant ID | `11111111-1111-1111-1111-111111111111` |
| Own company (active session) | `188b1b20-1948-4017-ada0-c0c838281e7b` (Host Flow) |
| Lead ID (acceptance run) | `aa93bdde-baf6-4fd4-a673-98634e284f4e` |
| Sales inquiry path | `/app/sales/inquiries/aa93bdde-baf6-4fd4-a673-98634e284f4e` |
| Invite token (masked) | `eM0A9C…HJ8h` — **revoked** |
| Public apply URL | `/public/apply/{token}` (token not persisted) |
| Converted ClientAccount ID | `98c2e6cd-4dff-4f8c-b151-14e3e600e86f` |

UI spot-check lead (pre-submit): `c135c88f-56ae-4174-8d7a-9236754324fa` with token `TqK0Aeb…kn4n` — **revoked**.

## Network evidence (Sales questionnaire-invite contract)

Actor: active tenant admin (`uos-rec-…@hostflow.test`, ID `3bad7c63-…`) with `X-Own-Company-Id: 188b1b20-…`.

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
  "token": "eM0A9C…HJ8h",
  "status": "sent",
  "sent_at": "2026-07-14T17:06:11Z",
  "apply_url": "/public/apply/{token}"
}
```

### After refresh (step 5)

```
POST /api/v1/leads/{lead_id}/questionnaire-invite  {"mark_sent": false}
→ 200  (same token, status still "sent")
```

Token stable: **yes** (prefix `eM0A9C…` unchanged after refresh).

### After submit (step 10)

```
POST /api/v1/leads/{lead_id}/questionnaire-invite  {"mark_sent": false}
→ 404  (no new invite; row count = 1)
```

## Public form (steps 6–9)

- `GET /api/v1/public/apply/{token}` → **29** fields, **18** `single_select`/`multi_select`, API `options: null` (frontend catalogs).
- UI (`hostflow.cc/public/apply/{token}`) after dist rebuild: **radio** widgets with PL labels (not text enum inputs).
- Submit: `client_acquisition` branch; hidden recruitment fields omitted from payload; `sales_questionnaire_status → submitted`; `recruitment_roles` absent from summary.

## convert-client (steps 11–12)

Requires **active** converting user (`administrator@hostflow.dev` is `is_active=false` → 422; environment note, not questionnaire defect).

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

Reproducible API trace: `backend/scripts/staging_questionnaire_runbook.sh` (generates ephemeral tokens; do not commit script output).

## Next step (post-merge only)

Auto-seed `targeted-advertising` intake form on tenant provisioning (idempotent; lazy backfill for legacy tenants).
