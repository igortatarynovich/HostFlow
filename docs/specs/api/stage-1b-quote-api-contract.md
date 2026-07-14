# Stage 1B — Quote API Contract

**Status:** design-first (revision 2 — addresses PR #20 review)  
**Base path:** `/api/v1/quotes`  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)  
**Money:** [`stage-1b-quote-money-arithmetic.md`](../architecture/stage-1b-quote-money-arithmetic.md)

---

## 1. Types

### QuoteStatus

`draft` | `revision_draft` | `sent` | `accepted` | `rejected` | `expired`

### AcceptanceSource

`manager_phone` | `manager_email` | `client_in_person` | `client_portal` | `other`

### QuoteOut (eager — no lazy-loading)

```json
{
  "id": "uuid",
  "tenant_id": "uuid",
  "client_account_id": "uuid",
  "own_company_id": "uuid | null",
  "quote_number": "Q-2026-000042",
  "title": "Oferta — reklama targetowana",
  "status": "draft",
  "currency": "PLN",
  "lock_version": 3,
  "current_version_id": "uuid",
  "accepted_version_id": "uuid | null",
  "acceptance_source": null,
  "accepted_by_user_id": null,
  "source_lead_id": "uuid | null",
  "valid_until": "2026-08-14",
  "sent_at": null,
  "accepted_at": null,
  "rejected_at": null,
  "expired_at": null,
  "created_by_user_id": "uuid | null",
  "created_at": "2026-07-14T12:00:00Z",
  "updated_at": "2026-07-14T12:00:00Z",
  "current_version": { "...QuoteVersionOut" },
  "latest_sent_version": { "...QuoteVersionOut | null" }
}
```

`latest_sent_version` populated when ≥1 sent revision exists (for accept default).

### QuoteVersionOut

```json
{
  "id": "uuid",
  "quote_id": "uuid",
  "version_number": 2,
  "version_status": "draft",
  "scope_snapshot": { "...schema v1" },
  "subtotal": "1500.0000",
  "tax_total": "345.0000",
  "total": "1845.0000",
  "notes_internal": null,
  "notes_client": "Propozycja ważna 30 dni.",
  "sent_at": null,
  "created_at": "2026-07-14T12:00:00Z"
}
```

Money: **decimal strings** per money arithmetic doc.

---

## 2. Tenant isolation

| Rule | Enforcement |
|------|-------------|
| All reads/writes | `quotes.tenant_id = request.tenant_id` |
| Cross-tenant id | `404` |
| Foreign `client_account_id` | Must exist in tenant else `404` |
| Version routes | Composite ownership via parent quote |

---

## 3. Concurrency

### Optimistic locking

Header: `If-Match: "<lock_version>"` (integer string, e.g. `"3"`)

- Required on `PATCH`, `send`, `revise`, `accept`, `reject`, `expire`
- Mismatch → `409` `{ "code": "stale_quote", "lock_version": 4 }`
- Successful mutation increments `lock_version` by 1

### Pessimistic locking

All transitions: `SELECT quotes … FOR UPDATE` in addition to `If-Match`.

---

## 4. Endpoints

### POST `/api/v1/quotes`

Create Quote + version 1 (`draft`).

**Idempotency-Key** (optional): see §7.

**Response:** `201 QuoteOut` with `lock_version: 1`

---

### PATCH `/api/v1/quotes/{id}`

Edit current **draft** version + quote metadata.

**Precondition:** `status IN (draft, revision_draft)` and `current_version.version_status = draft`

**If-Match:** required

---

### POST `/api/v1/quotes/{id}/send`

`draft | revision_draft → sent`

**Preconditions:**

- `current_version.version_status = draft`
- `own_company_id` resolved (else `422 own_company_required`)
- `scope_snapshot.currency == quote.currency`
- Valid `items[]` per money arithmetic

**Side effects:**

- Freeze snapshot; set version `version_status=sent`, `sent_at=now()`
- `quote.status = sent`

**Idempotency-Key:** replay same send → `200` if same version already sent

---

### POST `/api/v1/quotes/{id}/revise`

`sent | rejected | expired → revision_draft`

Creates **new draft version** (vN+1) on same Quote. Previous sent versions unchanged.

**Body (optional):** seed snapshot from latest sent or empty template.

**Forbidden when:** `status = accepted`

**Not idempotent** — each call appends version (use with care; typically once per negotiation round).

---

### POST `/api/v1/quotes/{id}/accept`

`sent → accepted`

**Body:**

```json
{
  "version_id": "uuid",
  "acceptance_source": "manager_phone"
}
```

- `version_id` optional — defaults to latest sent version
- If provided: must be `version_status=sent` for this quote else `409 stale_version`
- `acceptance_source` required
- `accepted_by_user_id` = authenticated actor

**Terminal** for Sale layer.

---

### POST `/api/v1/quotes/{id}/reject` / `/expire`

From `sent` only. Recoverable via `/revise`.

---

### GET `/api/v1/quotes/{id}/versions`

All versions newest-first; includes full sent history.

---

## 5. Error model

| Code | When |
|------|------|
| `409` | `stale_quote`, `stale_version`, `invalid_transition`, `idempotency_key_reused` |
| `422` | `own_company_required`, `currency_mismatch`, money validation |

---

## 6. Idempotency (normative)

**Storage:** `quote_idempotency_keys` table.

**Scope:** `(tenant_id, endpoint, idempotency_key)` unique.

**Supported endpoints (PR-1):** `POST /quotes`, `POST /quotes/{id}/send`, `POST /quotes/{id}/accept`

| Same key + same `request_hash` | Replay stored status + body |
| Same key + different hash | `409 idempotency_key_reused` |
| TTL | 24 hours |

`request_hash` = SHA-256 of canonical JSON (sorted keys, normalized decimals).

---

## 7. Removed from revision 1

- `POST /versions` — replaced by `PATCH` (pre-send) and `POST /revise` (post-send)
- `If-Match` on `updated_at` — replaced by `lock_version`

---

## 8. Audit events

Include `lock_version`, `version_number`, `acceptance_source` on accept.

---

## 9. Out of scope

Unchanged: no SO, Invoice, public portal accept in PR-1.
