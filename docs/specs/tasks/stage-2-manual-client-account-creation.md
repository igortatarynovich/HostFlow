# Stage 2 — Manual ClientAccount creation (backend contract)

**Status:** Implementation slice (product queue Stage 2)  
**Branch:** `feat/manual-client-account-creation`  
**Parents:** [Sequential queue](sales-to-comms-sequential-queue.md) · [Creation Origins v1](../architecture/client-account-creation-origins-v1.md)

## Scope (this PR)

Canonical Sales service `create_client_account_manually` + `POST /api/v1/client-accounts` rewire.

| Required | Done via |
|----------|----------|
| `origin_type = manual_creation` | column + stamp |
| actor / tenant / company / timestamp | `creation_origin_v1` |
| immutable `creation_ref` | UUID at create |
| idempotency | `idempotency_key` + tenant unique (PG) |
| tenant / company ownership | tenant filter; company assert |
| permissions | existing create roles (admin/manager/supervisor) |
| duplicate detection | exact normalized `display_name` in tenant/`own_company` |
| explicit force-create | `force_create` + `duplicate_decision.action=create_new` |
| audit | `client_account.manual_creation` |
| no Lead / SI / Flights / Convert | never sets `source_lead_id`; schema rejects inventing it |

## Out of scope

- Manual-create UI  
- Pipeline product wiring (Stage 3)  
- Communication  
- import / API origins  
- Universal duplicate review engine  

## HTTP

- Success: `201` + `ClientAccountOut` (includes origin fields)  
- Duplicate without force: `409` + candidates  
- Force without `create_new`: `422` / `409` with reason  

## Gate note

`make repo-health` on this feature branch is **not** the merge gate when the gate requires the integration branch tip. Final PASS is after merge + FF `integration/release-product-a-b`.
