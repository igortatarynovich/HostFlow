# Stage 1B — Quote API Contract

**Status:** design-first (revision 3)  
**Base path:** `/api/v1/quotes`  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)

---

## 1. Response shape

**QuoteOut** includes: `lock_version`, `current_valid_until`, `last_sent_at`, `last_rejected_at`, `last_expired_at`, `accepted_at`, `latest_sent_version`.

**No** quote-level `valid_until` / `sent_at` / `rejected_at` / `expired_at`.

**QuoteVersionOut** includes: `valid_until`, `version_status` (`draft` | `sent` | `superseded`), `sent_at`.

---

## 2. PATCH `/{id}`

- `status IN (draft, revision_draft)`
- Edits current draft version including **`valid_until`**
- `If-Match: lock_version` (integer)

---

## 3. POST `/{id}/send`

- Freeze `quote_versions.valid_until`
- Version → `sent`; prior sent → `superseded`
- Quote: `last_sent_at`, `current_valid_until`, `status=sent`

---

## 4. POST `/{id}/accept` — latest sent only

```json
{
  "version_id": "uuid",
  "acceptance_source": "manager_phone"
}
```

- `version_id` omitted → latest sent
- `version_id` must equal latest sent else `409 stale_version`
- `accepted_by_user_id` = actor

---

## 5. POST `/{id}/expire`

Evaluates **latest sent** `valid_until`. Sets `last_expired_at`.

---

## 6. Idempotency

`UNIQUE (tenant_id, quote_id, endpoint, idempotency_key)`

Examples:
- `POST /api/v1/quotes/{quote_id}/send`
- `POST /api/v1/quotes/{quote_id}/accept`

Same key + different `request_hash` → `409 idempotency_key_reused`.

---

## 7. Future

`POST /quotes/{id}/restore-version/{version_id}` — out of PR-1.
