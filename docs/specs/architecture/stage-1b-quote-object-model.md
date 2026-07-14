# Stage 1B — Quote Object Model

**Status:** design-first (revision 3)  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)  
**ADR:** [`ADR-020`](ADR-020-sales-to-engagement-commercial-model.md)  
**Money:** [`stage-1b-quote-money-arithmetic.md`](stage-1b-quote-money-arithmetic.md)

---

## 1. One Quote = one negotiation thread

All rounds (v1 sent → revise → v2 sent → …) stay on the **same Quote**. Older sent rows → `superseded`, immutable, not acceptable in MVP.

---

## 2. Quote fields

| Concern | Field |
|---------|-------|
| Client | `client_account_id` |
| Seller | `own_company_id` (required before send) |
| Lifecycle | `status` |
| Working version | `current_version_id` (composite FK) |
| Accepted version | `accepted_version_id` (= latest sent at accept) |
| List helper | `current_valid_until` (denorm; not source of truth) |
| Last events | `last_sent_at`, `last_rejected_at`, `last_expired_at` |
| Terminal | `accepted_at`, `acceptance_source`, `accepted_by_user_id` |
| Concurrency | `lock_version` |
| Money | `currency` (required) |

**Removed from Quote:** `valid_until`, `sent_at`, `rejected_at`, `expired_at`.

---

## 3. QuoteVersion fields

| Field | Notes |
|-------|-------|
| `version_number` | Monotonic from 1 |
| `version_status` | `draft` \| `sent` \| `superseded` |
| `valid_until` | **Source of truth**; frozen on send |
| `sent_at` | Per-version send time |
| `scope_snapshot` | Schema v1 + `items[]` |

Sending v2 does **not** change v1 `valid_until`.

---

## 4. Composite FK

```sql
UNIQUE (quote_id, id) ON quote_versions;

FOREIGN KEY (id, current_version_id)
  REFERENCES quote_versions (quote_id, id) DEFERRABLE INITIALLY DEFERRED;

FOREIGN KEY (id, accepted_version_id)
  REFERENCES quote_versions (quote_id, id) DEFERRABLE INITIALLY DEFERRED;
```

---

## 5. Lifecycle operations

| Op | Effect |
|----|--------|
| `PATCH` | Edit current draft + `valid_until` |
| `send` | Freeze version; supersede prior sent; `last_sent_at`; `current_valid_until` |
| `revise` | New draft version |
| `accept` | Latest sent only |
| `reject` | `last_rejected_at` |
| `expire` | Latest sent `valid_until`; `last_expired_at` |

---

## 6. Acceptance (MVP)

| `version_id` | Result |
|--------------|--------|
| omitted | Latest sent |
| = latest sent | Accept |
| ≠ latest / superseded | `409 stale_version` |

**Future:** `restore-version` → new draft from old snapshot (not accept).

---

## 7. Timestamps

| Data | Owner |
|------|-------|
| `sent_at`, `valid_until` | QuoteVersion |
| `last_sent_at`, `last_rejected_at`, `last_expired_at` | Quote |
| `accepted_at` | Quote (once) |
| Full round history | Audit events |

---

## 8. `quote_number_sequences`

`PRIMARY KEY (tenant_id, year)` — `FOR UPDATE` increment → `Q-{year}-{seq:06d}`.

---

## 9. Idempotency

`UNIQUE (tenant_id, quote_id, endpoint, idempotency_key)` — endpoint includes quote id for `/send`, `/accept`.

---

## 10. Revision 3 resolved

Latest-sent accept · version `valid_until` · `last_*` timestamps · sequence PK · idempotency `quote_id`.
