# Stage 1B — Quote API Contract

**Status:** design-first (OpenAPI-aligned draft)  
**Base path:** `/api/v1/quotes`  
**Auth:** Bearer session / API key per tenant RBAC  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)

---

## 1. Types

### QuoteStatus

`draft` | `sent` | `accepted` | `rejected` | `expired`

### QuoteOut

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
  "status": "draft",
  "scope_snapshot": { "...see object model" },
  "line_items": [],
  "subtotal": "1500.00",
  "tax_total": "345.00",
  "total": "1845.00",
  "notes_internal": null,
  "notes_client": "Propozycja ważna 30 dni.",
  "created_at": "2026-07-14T12:00:00Z"
}
```

---

## 2. Endpoints

### GET `/api/v1/quotes`

List quotes for current tenant.

**Query:** `status`, `client_account_id`, `cursor`, `limit` (default 50)

**Response:** `{ items: QuoteOut[], next_cursor: string | null }`

---

### POST `/api/v1/quotes`

Create draft quote with version 1.

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
    "service_family": "targeted_advertising",
    "offering_code": "meta_lead_gen_monthly",
    "parameters": { "channels": ["meta_ads"] }
  },
  "line_items": [
    {
      "kind": "service",
      "code": "meta_campaign_setup",
      "title": "Konfiguracja kampanii",
      "quantity": 1,
      "unit": "fixed",
      "unit_price": 1500,
      "tax_rate": 0.23
    }
  ],
  "notes_client": "Propozycja ważna 30 dni."
}
```

**Validation:**

- `client_account_id` must exist in tenant
- `scope_snapshot.schema_version` must be `1`
- At least one `line_items` entry

**Response:** `201` + `QuoteOut`

---

### GET `/api/v1/quotes/{id}`

**Response:** `QuoteOut` with embedded `current_version`

**Errors:** `404` cross-tenant

---

### PATCH `/api/v1/quotes/{id}`

Update draft metadata only (`title`, `valid_until`, `notes_*` on current version).

**Precondition:** `status = draft`

**Response:** `QuoteOut`

**Errors:** `409` if not draft

---

### POST `/api/v1/quotes/{id}/send`

Transition `draft → sent`.

**Side effects:**

- Freeze `scope_snapshot` on current version (merge `client_account` + `captured_at`)
- Set `sent_at`, `status = sent`

**Response:** `QuoteOut`

**Errors:** `409` if not draft; `422` if snapshot invalid

---

### POST `/api/v1/quotes/{id}/accept`

Transition `sent → accepted`.

**Response:** `QuoteOut`

**Errors:** `409` if not sent

**Explicit non-behavior:** does **not** create Service Order.

---

### POST `/api/v1/quotes/{id}/reject`

Transition `sent → rejected`. Optional body: `{ "reason": "..." }` (stored in audit only).

---

### POST `/api/v1/quotes/{id}/expire`

Transition `sent → expired`. Manual operator action in PR-1; cron later.

---

### GET `/api/v1/quotes/{id}/versions`

Version history, newest first.

### GET `/api/v1/quotes/{id}/versions/{version_id}`

Single immutable version.

---

## 3. Error model

| Code | When |
|------|------|
| `400` | Validation failure |
| `403` | RBAC |
| `404` | Not found / cross-tenant |
| `409` | Invalid lifecycle transition |
| `422` | `scope_snapshot` schema failure |

---

## 4. RBAC matrix

| Role | List/Get | Create/Update draft | Send/Accept/Reject/Expire |
|------|----------|---------------------|---------------------------|
| viewer | ✅ | ❌ | ❌ |
| recruiter | ❌ | ❌ | ❌ |
| supervisor | ✅ | ✅ | ✅ |
| manager | ✅ | ✅ | ✅ |
| admin | ✅ | ✅ | ✅ |

---

## 5. Idempotency

| Operation | Idempotency |
|-----------|-------------|
| POST /quotes | No — creates new quote |
| POST /send | Re-post on `sent` → `409` (not duplicate send) |
| POST /accept | Re-post on `accepted` → `200` same body (safe replay) |

---

## 6. Out of scope (explicit)

- Public/client portal quote view
- PDF generation
- E-signature
- Webhooks
- Service Order endpoints
- Invoice preview
