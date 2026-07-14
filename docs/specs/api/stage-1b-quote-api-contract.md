# Stage 1B — Quote API Contract

**Status:** design-first (pending review)  
**Base path:** `/api/v1/quotes`  
**Auth:** Bearer session / API key per tenant RBAC  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)

---

## 1. Types

### QuoteStatus

`draft` | `sent` | `accepted` | `rejected` | `expired`

### QuoteOut (eager — no lazy-loading)

Responses **always** embed `current_version` (or `accepted_version` detail for terminal accepted). ORM must not trigger implicit loads beyond this shape.

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "client_account_id": "uuid",
  "own_company_id": "uuid | null",
  "quote_number": "Q-smoke-00042",
  "title": "Oferta — reklama targetowana",
  "status": "draft",
  "currency": "PLN",
  "current_version_id": "uuid",
  "accepted_version_id": "uuid | null",
  "source_lead_id": "uuid | null",
  "valid_until": "2026-08-14",
  "sent_at": null,
  "accepted_at": null,
  "rejected_at": null,
  "expired_at": null,
  "created_by_user_id": "uuid | null",
  "created_at": "2026-07-14T12:00:00Z",
  "updated_at": "2026-07-14T12:00:00Z",
  "current_version": { "...QuoteVersionOut" }
}
```

### QuoteVersionOut

```json
{
  "id": "uuid",
  "quote_id": "uuid",
  "version_number": 1,
  "scope_snapshot": { "...schema v1 — see object model" },
  "subtotal": "1500.0000",
  "tax_total": "345.0000",
  "total": "1845.0000",
  "notes_internal": null,
  "notes_client": "Propozycja ważna 30 dni.",
  "sent_at": null,
  "created_at": "2026-07-14T12:00:00Z"
}
```

Money fields: **decimal strings**, never JSON numbers with float semantics.

---

## 2. Tenant isolation

| Rule | Enforcement |
|------|-------------|
| List/get scoped to `request.tenant_id` | All queries filter `quotes.tenant_id` |
| Cross-tenant id | `404` (not `403`) |
| `client_account_id` on create | Must exist **in same tenant** else `404` |
| `source_lead_id` optional | If present, must be same tenant else `404` |
| Version routes | Verify `quote_versions.tenant_id` via parent quote |

---

## 3. Concurrency

### Optimistic locking

`PATCH` and all transitions accept optional header:

`If-Match: "<quote.updated_at.isoformat()>"`

Mismatch → `409 Conflict` with `{ "code": "stale_quote" }`.

Transitions use `SELECT … FOR UPDATE` on quote row regardless.

---

## 4. Endpoints

### GET `/api/v1/quotes`

**Query:** `status`, `client_account_id`, `cursor`, `limit` (default 50)

**Response:** `{ items: QuoteOut[], next_cursor: string | null }`

---

### POST `/api/v1/quotes`

Create draft quote + version 1.

**Idempotency:** optional header `Idempotency-Key` (UUID). Replay within 24h returns same `201` body.

**Request:**

```json
{
  "client_account_id": "uuid",
  "title": "Oferta — reklama targetowana",
  "currency": "PLN",
  "source_lead_id": "uuid",
  "valid_until": "2026-08-14",
  "scope_snapshot": {
    "schema_version": 1,
    "title": "Oferta — reklama targetowana",
    "description": null,
    "service_family": "targeted_advertising",
    "offering_code": "meta_lead_gen_monthly",
    "currency": "PLN",
    "items": [
      {
        "item_id": "uuid",
        "title": "Konfiguracja kampanii",
        "description": null,
        "quantity": "1",
        "unit": "fixed",
        "unit_price": "1500.0000",
        "tax_rate": "0.23",
        "metadata": {}
      }
    ],
    "parameters": { "channels": ["meta_ads"] },
    "metadata": {}
  },
  "notes_client": "Propozycja ważna 30 dni."
}
```

**Validation:**

- `currency` required (3-letter ISO)
- `scope_snapshot.schema_version === 1`
- `scope_snapshot.items.length >= 1`
- Each item: `title`, `quantity`, `unit`, `unit_price` required
- Server computes `tax_amount`, `line_total`, `subtotal`, `tax_total`, `total`

**Response:** `201 QuoteOut`

---

### GET `/api/v1/quotes/{id}`

**Response:** `QuoteOut`  
**Errors:** cross-tenant → `404`

---

### PATCH `/api/v1/quotes/{id}`

Update draft quote metadata + current draft `scope_snapshot` / notes.

**Precondition:** `status = draft`  
**Concurrency:** `If-Match` on `updated_at`  
**Errors:** `409` if not draft or stale

---

### POST `/api/v1/quotes/{id}/versions`

Create new draft revision (increments `version_number`, sets `current_version_id`).

**Precondition:** `status = draft` only  
**Body:** same commercial payload shape as PATCH snapshot portion  
**Errors:** `409` if not draft

**Note:** Not available after `sent`. Further commercial proposals require a **new Quote** aggregate.

---

### POST `/api/v1/quotes/{id}/send`

`draft → sent`

**Idempotency:** if already `sent` with same `current_version_id` → `200` replay; if `sent` with different version context → `409`

**Side effects:**

- Validate + freeze `scope_snapshot` (inject `client_account`, `captured_at`)
- Set `quote_versions.sent_at` on current version
- Set `quotes.sent_at`, `status=sent`
- Audit `quote.sent`

**Errors:** `409` not draft; `422` invalid snapshot

---

### POST `/api/v1/quotes/{id}/accept`

`sent → accepted`

**Body (optional):** `{ "version_id": "uuid" }` — if omitted, uses `current_version_id`. If provided, **must equal** `current_version_id` else `409 stale_version`.

**Idempotency:** replay on `accepted` → `200` same body

**Sets:** `accepted_version_id = current_version_id`, `accepted_at`

**Does not:** create Service Order

---

### POST `/api/v1/quotes/{id}/reject`

`sent → rejected`  
**Body:** `{ "reason": "optional string" }` → audit only  
**Terminal:** no return to draft

---

### POST `/api/v1/quotes/{id}/expire`

`sent → expired`  
**Actor:** manager / supervisor / admin  
**Audit:** `quote.expired` with `trigger=manual`  
**Future:** scheduled job on `valid_until` uses `trigger=valid_until`

---

### GET `/api/v1/quotes/{id}/versions`

Immutable history, newest first.

### GET `/api/v1/quotes/{id}/versions/{version_id}`

Single version; `404` if not under quote/tenant.

---

## 5. Error model

| Code | When |
|------|------|
| `400` | Validation failure |
| `403` | RBAC |
| `404` | Not found / cross-tenant / foreign ClientAccount |
| `409` | Invalid transition, stale lock, wrong version accept, sent→draft attempt |
| `422` | `scope_snapshot` schema failure |

Conflict body shape:

```json
{
  "code": "invalid_transition | stale_quote | stale_version",
  "message": "human readable",
  "current_status": "sent"
}
```

---

## 6. RBAC matrix

| Role | List/Get | Create/Update draft | Send/Accept/Reject/Expire |
|------|----------|---------------------|---------------------------|
| viewer | ✅ | ❌ | ❌ |
| recruiter | ❌ | ❌ | ❌ |
| supervisor | ✅ | ✅ | ✅ |
| manager | ✅ | ✅ | ✅ |
| admin | ✅ | ✅ | ✅ |

---

## 7. Idempotency summary

| Operation | Behavior |
|-----------|----------|
| POST /quotes | `Idempotency-Key` → same resource |
| POST /send | Replay while `sent` + same version → `200` |
| POST /accept | Replay while `accepted` → `200` |
| POST /reject | Replay while `rejected` → `200` |
| POST /expire | Replay while `expired` → `200` |
| POST /versions | Never idempotent — always new version number |

---

## 8. Audit events

See object model §8. Emitted via existing `log_activity` pattern; include `tenant_id`, `actor_user_id`, `quote_id`, `version_number`.

---

## 9. Out of scope (explicit)

- Public/client portal
- PDF / e-sign
- Webhooks
- `POST /service-orders/from-quote` (next PR)
- Invoice preview
- Cancelling `accepted` quotes
