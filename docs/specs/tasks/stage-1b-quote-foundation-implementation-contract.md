# Stage 1B — Quote Foundation Implementation Contract

**Status:** design-first — **revision 3, pending re-review** (no runtime until approved)  
**Owner:** Services / Sales backend  
**Parent ADR:** [`ADR-020`](../architecture/ADR-020-sales-to-engagement-commercial-model.md)

---

## 0. Revision changelog

### Revision 3

| # | Issue | Fix |
|---|-------|-----|
| 1 | Accept any historical sent version | **Latest sent only**; else `409 stale_version` |
| 2 | `quotes.valid_until` wrong level | **`quote_versions.valid_until`**; denorm `current_valid_until` |
| 3 | Ambiguous quote timestamps | Version: `sent_at`, `valid_until`; Quote: `last_*` + `accepted_at` |
| 4 | Sequence PK unclear | **`PRIMARY KEY (tenant_id, year)`** |
| 5 | Idempotency scope | **`(tenant_id, quote_id, endpoint, key)`** |

### Revision 2

One Quote = one negotiation thread; composite version FK; `lock_version`; money arithmetic doc.

---

## 1. Goal

Versioned commercial proposal on a **single negotiation thread** per Quote.

After PR-1:

1. Create Quote + v1 draft.
2. `send` → immutable sent version with frozen `valid_until`.
3. `revise` → counter-offer (new draft version, same Quote).
4. `accept` → **latest sent version only**; Sale terminal.
5. Sent history preserved (`superseded` older rounds).

**Out of scope:** Service Order, Commercial Confirmation, Invoice, Billing, frontend, questionnaire.

---

## 2. Object model (summary)

[`stage-1b-quote-object-model.md`](../architecture/stage-1b-quote-object-model.md)

### 2.1 `quotes`

| Field | Notes |
|-------|-------|
| `lock_version` | Optimistic lock (`If-Match`) |
| `status` | `draft` \| `revision_draft` \| `sent` \| `accepted` \| `rejected` \| `expired` |
| `current_version_id` | Composite FK |
| `accepted_version_id` | Latest sent at accept |
| `current_valid_until` | Denorm from latest sent version (list UX) |
| `last_sent_at` / `last_rejected_at` / `last_expired_at` | Latest event timestamps |
| `accepted_at` | Terminal acceptance |

**Not on quotes:** `valid_until`, `sent_at`, `rejected_at`, `expired_at`.

### 2.2 `quote_versions`

| Field | Notes |
|-------|-------|
| `version_status` | `draft` \| `sent` \| `superseded` |
| `valid_until` | **Source of truth**; frozen on send |
| `sent_at` | Per-version send time |
| `scope_snapshot` | Schema v1 + `items[]` |

On new send: prior `sent` rows → `superseded`.

---

## 3. Lifecycle rules

| Rule | Decision |
|------|----------|
| Accept | **Latest sent version only**; `version_id` must match else `409` |
| `valid_until` | Version field; expire checks latest sent |
| Timestamps | `last_*` on Quote; per-version `sent_at` |
| `sent → draft` | Forbidden |
| `accepted` | Terminal for Sale |
| Old terms | Future `restore-version` → new draft (not accept) |

---

## 4. Money & snapshot

[`stage-1b-quote-money-arithmetic.md`](../architecture/stage-1b-quote-money-arithmetic.md)

---

## 5. API

[`stage-1b-quote-api-contract.md`](../api/stage-1b-quote-api-contract.md)

---

## 6. Migrations (planned)

- `quote_number_sequences PRIMARY KEY (tenant_id, year)`
- `quote_idempotency_keys UNIQUE (tenant_id, quote_id, endpoint, idempotency_key)`
- Composite FKs on version pointers

---

## 7. Required tests

| Scenario | Expected |
|----------|----------|
| accept latest sent | `accepted_version_id` = latest |
| accept v1 after v2 sent | `409 stale_version` |
| v2 send freezes v2 `valid_until` only | v1 unchanged |
| v2 send marks v1 `superseded` | v1 not acceptable |
| expire | uses latest sent `valid_until` |
| idempotency same key, different quotes | no collision |
| stale `If-Match` | `409 stale_quote` |

---

## 8. Merge gate

- [ ] **Design PR #20 approved (revision 3)**
- [ ] SPA path literals chore PR (separate)
- [ ] Implementation after approval

---

## 9. References

- [`stage-1b-quote-object-model.md`](../architecture/stage-1b-quote-object-model.md)
- [`stage-1b-quote-money-arithmetic.md`](../architecture/stage-1b-quote-money-arithmetic.md)
- [`stage-1b-quote-api-contract.md`](../api/stage-1b-quote-api-contract.md)
- [`stage-1b-quote-lifecycle-sequences.md`](../workflows/stage-1b-quote-lifecycle-sequences.md)
