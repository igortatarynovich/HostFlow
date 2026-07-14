# Stage 1B — Quote Foundation Implementation Contract

**Status:** design-first — **revision 2, pending re-review** (no runtime until approved)  
**Owner:** Services / Sales backend  
**Parent ADR:** [`ADR-020`](../architecture/ADR-020-sales-to-engagement-commercial-model.md)  
**Review:** addresses PR #20 REQUEST_CHANGES (4 blocks + clarifications)

---

## 0. Revision 2 changelog

| Block | Issue | Fix |
|-------|-------|-----|
| 1 | Quote/version contradiction | **One Quote = one negotiation thread**; `revise` after send; reject/expired continue same Quote |
| 2 | Weak version FK | Composite FK `(quote.id, current_version_id) → quote_versions(quote_id, id)` |
| 3 | Fragile `If-Match` | `lock_version INTEGER` on quotes |
| 4 | Money undefined | [`stage-1b-quote-money-arithmetic.md`](../architecture/stage-1b-quote-money-arithmetic.md) |
| + | Acceptance metadata | `acceptance_source`, `accepted_by_user_id` |
| + | `quote_number` | Per-tenant sequence + `FOR UPDATE` |
| + | Idempotency | `quote_idempotency_keys`; tenant+endpoint+key; hash mismatch → 409 |
| + | `own_company_id` | Required before `send` |

---

## 1. Goal

Create and store a **versioned commercial proposal** on a **single negotiation thread** per Quote.

After PR-1:

1. Create Quote for `ClientAccount` (v1 draft).
2. `send` → immutable sent version.
3. `revise` → counter-offer as new draft version **same Quote**.
4. `accept` → pin specific **sent** version; Sale terminal.
5. Full sent history preserved for audit and future SO handoff.

**Out of scope:** Service Order, Commercial Confirmation, Invoice, Billing, frontend, questionnaire.

---

## 2. Object model (summary)

Full detail: [`stage-1b-quote-object-model.md`](../architecture/stage-1b-quote-object-model.md).

### 2.1 `quotes` (additions in revision 2)

| Field | Type | Notes |
|-------|------|-------|
| `lock_version` | int | Starts at 1; `If-Match` target |
| `status` | enum | `draft` \| `revision_draft` \| `sent` \| `accepted` \| `rejected` \| `expired` |
| `acceptance_source` | enum, null | Set on accept |
| `accepted_by_user_id` | UUID, null | Actor on accept |
| `current_version_id` | UUID | Composite FK to `quote_versions(quote_id, id)` |
| `accepted_version_id` | UUID, null | Composite FK; must be **sent** version |

### 2.2 `quote_versions`

| Field | Notes |
|-------|-------|
| `version_status` | `draft` \| `sent` |
| `scope_snapshot` | Schema v1 with `items[]` |
| totals | Per money arithmetic doc |

**Removed:** separate `line_items` column — lines live in `scope_snapshot.items[]` only.

---

## 3. Lifecycle

```text
draft → sent → accepted | rejected | expired
              ↘ revision_draft → sent → …
rejected / expired → revision_draft (same Quote)
```

| Rule | Decision |
|------|----------|
| `sent → draft` | **Forbidden** |
| Counter-offer | `POST /revise` → `revision_draft` + new draft version |
| Accept target | Specific **sent** `version_id` (default: latest sent) |
| `accepted` | **Terminal** for Sale |
| Reject/expired | **Not terminal for thread** — `revise` continues negotiation |
| New Quote | Only for **new business opportunity**, not reject recovery |

---

## 4. `scope_snapshot` + money

- Structured schema v1 — not arbitrary JSON
- [`stage-1b-quote-money-arithmetic.md`](../architecture/stage-1b-quote-money-arithmetic.md) is normative
- `scope_snapshot.currency` must equal `quotes.currency`
- `unit_price` tax-exclusive; per-line rounding then sum

---

## 5. API (summary)

[`stage-1b-quote-api-contract.md`](../api/stage-1b-quote-api-contract.md)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/` | Create quote + v1 draft |
| PATCH | `/{id}` | Edit draft / revision_draft |
| POST | `/{id}/send` | Freeze version → sent |
| POST | `/{id}/revise` | New draft version after sent/reject/expired |
| POST | `/{id}/accept` | Accept sent version |
| POST | `/{id}/reject` | Reject latest sent round |
| POST | `/{id}/expire` | Expire sent round |
| GET | `/{id}/versions` | Full history |

**Removed:** `POST /versions` (contradicted thread model).

---

## 6. Planned migrations

| Revision | Purpose |
|----------|---------|
| `202607141600_quote_foundation` | `quotes`, `quote_versions`, composite FKs, `lock_version` |
| `202607141601_quote_sequences` | `quote_number_sequences`, `quote_idempotency_keys` |
| `202607141602_quote_constraints` | status checks, `version_status`, money NUMERIC types |

**Composite FK (required):**

```sql
UNIQUE (quote_id, id) ON quote_versions;

ALTER TABLE quotes ADD CONSTRAINT fk_quotes_current_version
  FOREIGN KEY (id, current_version_id)
  REFERENCES quote_versions (quote_id, id)
  DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE quotes ADD CONSTRAINT fk_quotes_accepted_version
  FOREIGN KEY (id, accepted_version_id)
  REFERENCES quote_versions (quote_id, id)
  DEFERRABLE INITIALLY DEFERRED;
```

---

## 7. Required tests (implementation PR)

| Scenario | Expected |
|----------|----------|
| draft → send → sent v1 frozen | immutable version row |
| sent → revise → revision_draft v2 draft | v1 still sent in history |
| revision_draft → send → v2 sent | two sent versions in history |
| accept latest sent version | `accepted_version_id` set; terminal |
| accept old sent version (not latest) | `409 stale_version` if not latest and not allowed — **default: only latest sent** |
| reject → revise → send → accept | same `quote_id` throughout |
| composite FK violation attempt | DB rejects wrong version pointer |
| stale `If-Match` | `409 stale_quote` |
| idempotency same key different body | `409 idempotency_key_reused` |
| send without own_company | `422` |
| currency mismatch snapshot | `422` |
| money test vectors | per arithmetic doc |

---

## 8. Merge gate

- [x] PR #18, #19 merged
- [x] Auto-seed smoke passed
- [ ] **Design PR #20 approved (revision 2)**
- [ ] SPA path literals chore PR (separate)
- [ ] Implementation branch after approval

---

## 9. References

- [`stage-1b-quote-object-model.md`](../architecture/stage-1b-quote-object-model.md)
- [`stage-1b-quote-money-arithmetic.md`](../architecture/stage-1b-quote-money-arithmetic.md)
- [`stage-1b-quote-api-contract.md`](../api/stage-1b-quote-api-contract.md)
- [`stage-1b-quote-ui-wireflow.md`](../ux/stage-1b-quote-ui-wireflow.md)
- [`stage-1b-quote-lifecycle-sequences.md`](../workflows/stage-1b-quote-lifecycle-sequences.md)
