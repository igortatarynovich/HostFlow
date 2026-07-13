# Stage 1A — ClientAccount Implementation Contract

**Status:** canonical (L3 implementation contract)  
**Owner:** Services / Sales backend  
**Parent ADR:** [`ADR-020`](../architecture/ADR-020-sales-to-engagement-commercial-model.md) §3.4, §14  
**Scope:** `Lead / Sales Inquiry → ClientAccount → Company link` only. No Quote, CommercialConfirmation, Readiness, Engagement.

---

## 1. Goal

Introduce **`ClientAccount`** as a first-class domain entity without breaking legacy `Company`-based client screens. After Stage 1A, every client-lead conversion produces a stable `client_account_id` suitable for Stage 1B (Quote → ServiceOrder).

**Out of scope:** Opportunity, Quote, billing_company_id on finance flows, CommercialConfirmation registry, Readiness engine, Engagement, party graph (`ClientAccountPartyLink`).

---

## 2. Entities and fields

### 2.1 `client_accounts`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | PK |
| `tenant_id` | UUID string | RLS |
| `own_company_id` | UUID string, nullable | Operating company scope (from Lead) |
| `display_name` | string | Product label; **not auto-synced** with Company.name after create |
| `status` | enum | `prospect` \| `active` \| `inactive` |
| `owner_user_id` | UUID string, nullable | Account manager |
| `primary_contact_id` | UUID string, nullable | Phase 1: opaque id / future Contact FK |
| `primary_company_id` | UUID string, nullable | Shortcut to main billing/legal party |
| `source_lead_id` | UUID string, nullable | Originating Lead (Sales Inquiry transport) |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**Indexes:**

- `UNIQUE (tenant_id, source_lead_id) WHERE source_lead_id IS NOT NULL` — idempotent conversion guard
- `(tenant_id, status)`
- `(tenant_id, display_name)`

**Schema ownership:** `client_accounts` and link columns (`leads.client_account_id`, `companies.client_account_id`) are owned exclusively by Alembic (`202607131400`, `202607131401`). No startup `ensure_schema` DDL for these objects.

### 2.2 Link columns (additive)

| Table | Column | Notes |
|-------|--------|-------|
| `leads` | `client_account_id` nullable | Set on conversion |
| `companies` | `client_account_id` nullable | **Stage 1 temporary** link; not 1:1 constraint |

---

## 3. Invariants

1. `ClientAccount` **may exist without** `Company`.
2. `Company` **may exist without** `ClientAccount` (legacy parties, non-client roles).
3. `ClientAccount` has **at most one** `primary_company_id`, but may link multiple `Company` rows in Stage 2.
4. Deleting/archiving `Company` does **not** delete `ClientAccount`.
5. Archiving `ClientAccount` does **not** delete `Company`, `Lead`, Quote, or ServiceOrder.
6. `display_name` is **not** auto-synced with `Company.name` after creation.
7. All linked rows (`Lead`, `ClientAccount`, `Company`) must share the same `tenant_id`.
8. `Company.client_account_id` is a **compatibility shortcut**, not «one account — one company» forever.

---

## 4. `convert-client` behavior

Single transaction; **idempotent**; **row lock** on Lead (`SELECT … FOR UPDATE`).

### Algorithm

1. Lock Lead; validate tenant, `own_company_id`, `lead_type=client`, `lead_target_type=client_lead`.
2. Resolve existing `ClientAccount`:
   - by `lead.client_account_id`, or
   - by `(tenant_id, source_lead_id=lead.id)`.
3. If account missing → create `ClientAccount` (`display_name` from company name or contact name).
4. If `company_name` present → find or create `Company` (legacy `create_company_service` path).
5. If Company created/found → set `company.client_account_id`; set `account.primary_company_id` **only if empty**.
6. Set `lead.client_account_id`; preserve `lead.converted_client_id` when Company exists (legacy).
7. Update lead status/stage/normalized (legacy fields).
8. Emit audit event `client_lead.converted_to_client_account`.
9. Return `{ client_account_id, company_id?, idempotent_replay }`.

### Replay / legacy backfill

- Replay with existing `client_account_id` → return same ids, `idempotent_replay=true`.
- Legacy row with `converted_client_id` but no `client_account_id` → create/link account on replay (backfill).

### Account-only path

When inquiry has contact but **no** `company_name` → create `ClientAccount` only; skip Company.

---

## 5. API (MVP)

Prefix: `/api/v1/client-accounts`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List (paginated, filter by status) |
| POST | `/` | Manual create |
| GET | `/{id}` | Detail |
| PATCH | `/{id}` | Update operational fields |
| GET | `/{id}/primary-company` | Primary Company or 404 |

Conversion stays on existing routes (legacy compatibility):

- `POST /api/v1/leads/{id}/convert-client`
- `POST /api/v1/sales/inquiries/{id}/convert-client`

RBAC: `admin`, `manager`, `supervisor` for convert; `viewer` read-only on list/get.

---

## 6. PR split

| PR | Deliverables |
|----|--------------|
| **PR-1** | Model, Alembic migration, repository/service, API, RBAC, audit, unit tests |
| **PR-2** | `convert-client` refactor, idempotency, `lead_client_conversion` delegation, regression tests |
| **PR-3** | Sales Inquiry exposes `client_account_id` in ApplicationOut; workflow extensions; no Quote/SO changes |

---

## 7. Required tests

| Scenario | Expected |
|----------|----------|
| New lead conversion | 1 ClientAccount + 1 Company (when company_name present) |
| Replay conversion | No duplicates |
| Company create fails | ClientAccount not orphaned (full rollback) |
| Company already exists | ClientAccount created + linked |
| No legal name / company_name | ClientAccount only, no Company |
| Cross-tenant link | Forbidden |
| Company archived | ClientAccount preserved |
| Parallel convert (2 requests) | 1 ClientAccount (DB unique index + row lock) |
| Legacy frontend | `converted_client_id` / LeadOut unchanged when Company exists |

---

## 8. Security & tenant boundaries

| Rule | Requirement |
|------|-------------|
| Tenant ownership | Every `ClientAccount` row is scoped by `tenant_id` (RLS) |
| Cross-tenant access | Forbidden: `Lead`, `Company`, and `ClientAccount` links must share `tenant_id` |
| Cascade delete | **No** cascade delete from `Company` to `ClientAccount` |
| RBAC | `viewer` read-only; `admin` / `manager` / `supervisor` for create, update, convert |

---

## 9. References

- [`ADR-020`](../architecture/ADR-020-sales-to-engagement-commercial-model.md)
- [`ui-constitution-v1.md`](../architecture/ui-constitution-v1.md) — «Клиент» = ClientAccount
- [`module-scope.md`](../../services/module-scope.md)
