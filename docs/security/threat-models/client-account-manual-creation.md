# Threat Model — Manual ClientAccount creation (Origins v1)

## Assets

- `ClientAccount` rows and origin provenance (`origin_type`, `creation_ref`, `creation_origin_v1`)
- Tenant / company ownership binding
- Operator audit trail for manual creates
- Idempotency keys (replay safety)

## Trust boundaries

- Authenticated Sales operator (admin / manager / supervisor) ↔ tenant-scoped API ↔ DB
- No public / unauthenticated surface in this slice
- No Lead / SalesInquiry / Flights / Convert Mapping invent on this path

## Surface

- `POST /api/v1/client-accounts` → `create_client_account_manually`
- Alembic: origin columns + tenant-unique idempotency

## Угрозы

| ID | Угроза | Вектор |
|----|--------|--------|
| MCA-1 | Cross-tenant create / company bind | `company_id` outside caller tenant |
| MCA-2 | Privilege bypass | create without create-role guard |
| MCA-3 | Silent duplicate pollution | create when normalized `display_name` already exists |
| MCA-4 | Force-create without explicit decision | `force_create` without `duplicate_decision.action=create_new` |
| MCA-5 | Idempotency collision / replay confusion | reuse key maps to different payload or other tenant |
| MCA-6 | Provenance forgery | invent `source_lead_id` / non-`manual_creation` origin |
| MCA-7 | Audit gap | successful create without `client_account.manual_creation` |

## Митигации (this slice)

- Tenant filter on all reads/writes; company asserted in same tenant before create
- Existing create roles enforced on the HTTP endpoint (no new role invent)
- Exact normalized `display_name` duplicate detection → `409` + candidates unless explicit force + `create_new`
- Immutable `creation_ref` (UUID) + `origin_type=manual_creation` stamped at create
- Tenant-unique `idempotency_key`; replay returns prior account
- Schema/service reject inventing Lead provenance on this path
- Activity audit `client_account.manual_creation` on successful create

## Out of scope (explicit)

- Manual-create UI
- Pipeline product wiring (Stage 3)
- Universal duplicate review engine
- import / API origins

## Связанные спеки

- `docs/specs/architecture/client-account-creation-origins-v1.md`
- `docs/specs/tasks/stage-2-manual-client-account-creation.md`
- `docs/specs/tasks/sales-to-comms-sequential-queue.md`
