# Stage 1B — Quote Object Model

**Status:** design-first (pending review)  
**Parent:** [`stage-1b-quote-foundation-implementation-contract.md`](../tasks/stage-1b-quote-foundation-implementation-contract.md)  
**ADR:** [`ADR-020`](ADR-020-sales-to-engagement-commercial-model.md)

---

## 1. Position in commercial stack

```text
Sales Inquiry (Lead transport)
        ↓ convert-client
   ClientAccount  ←── identity anchor (Stage 1A)
        ↓
      Quote  ←── Stage 1B (this document)
        ↓
  ServiceOrder  ←── Stage 1B+ (next PR)
        ↓
CommercialConfirmation → Invoice  ←── later PRs
```

Quote belongs to the **Sale** layer. It records *what we offered* and *whether the client agreed*, without starting execution or billing.

---

## 2. Aggregate design

### 2.1 Quote — stable aggregate root

**Purpose:** long-lived operational handle for one commercial proposal thread per `quote_number`.

| Concern | Owner field |
|---------|-------------|
| Who is the client? | `client_account_id` (required) |
| Who sells? | `own_company_id` (nullable) |
| Lifecycle stage | `status` |
| Active commercial revision | `current_version_id` |
| Traceability | `source_lead_id` (optional) |
| Money context | `currency` (required, ISO 4217) |

**Invariants:**

- `tenant_id` matches `ClientAccount.tenant_id` (service + DB guard).
- `quote_number` unique per `(tenant_id, quote_number)`.
- `currency` required on create; all money in versions uses quote currency.
- Quote row survives `ClientAccount` archive; no cascade delete.

**Not in PR-1:** `service_order_id`, `billing_company_id`, `commercial_confirmation_id`.

### 2.2 QuoteVersion — immutable commercial snapshot

**Purpose:** append-only revision of commercial terms. After a version is **sent**, it is **immutable**.

| Rule | Detail |
|------|--------|
| Sent versions frozen | No PATCH on version row once `sent_at` set on parent quote for that version |
| Monotonic `version_number` | `UNIQUE (quote_id, version_number)` |
| Draft edits | Only `current_version` while `quote.status = draft` |
| New revision | `POST /versions` while `draft` only → increments version, updates `current_version_id` |
| After terminal quote | No new versions on same aggregate — create **new Quote** |

### 2.3 `current_version_id` — pointer without migration cycle

**Problem:** `quotes` and `quote_versions` reference each other.

**Migration order (approved pattern):**

1. `CREATE quotes` — `current_version_id UUID NULL` **without FK**.
2. `CREATE quote_versions` — `quote_id → quotes.id`.
3. `ALTER quotes ADD CONSTRAINT … FOREIGN KEY (current_version_id) REFERENCES quote_versions(id) DEFERRABLE INITIALLY DEFERRED`.

Insert path in one transaction:

```text
INSERT quote (current_version_id=NULL)
INSERT quote_version (quote_id=…)
UPDATE quote SET current_version_id=version.id
COMMIT
```

Deferred FK avoids chicken-and-egg at migration time and runtime.

---

## 3. Relationships

```text
Tenant 1──* Quote
ClientAccount 1──* Quote
Quote 1──* QuoteVersion
Quote 0..1──1 QuoteVersion (current_version_id)
Lead 0..1──* Quote (source_lead_id; logical link, no cascade)
```

---

## 4. `scope_snapshot` schema v1 (canonical — not free-form JSON)

All commercial lines live **inside** `scope_snapshot.items[]`. No parallel unstructured JSON.

### 4.1 Root object

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `schema_version` | int | yes | `1` in PR-1 |
| `title` | string | yes | Proposal title at send time |
| `description` | string, null | no | Client-visible summary |
| `service_family` | string | yes | e.g. `targeted_advertising` |
| `offering_code` | string | yes | Tenant catalog code |
| `currency` | string(3) | yes | Must match `quotes.currency` |
| `items` | array | yes | ≥1 line; see §4.2 |
| `client_account` | object | yes at send | `{ id, display_name }` denormalized |
| `primary_company_id` | string, null | no | From ClientAccount |
| `parameters` | object | no | Service-specific extras |
| `metadata` | object | no | Opaque extensions |
| `captured_at` | ISO datetime | yes at send | Freeze timestamp |

### 4.2 `items[]` element

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `item_id` | string (uuid) | yes | Stable line id |
| `title` | string | yes | Line label |
| `description` | string, null | no | |
| `quantity` | string (decimal) | yes | **No float** — stored as `NUMERIC` / decimal string in API |
| `unit` | string | yes | e.g. `fixed`, `month`, `hour` |
| `unit_price` | string (decimal) | yes | **No float** |
| `tax_rate` | string (decimal), null | no | e.g. `0.23` |
| `tax_amount` | string (decimal), null | no | Computed |
| `line_total` | string (decimal) | yes | Computed |
| `metadata` | object | no | |

### 4.3 Denormalized totals on `quote_versions`

| Column | SQL type | Rule |
|--------|----------|------|
| `subtotal` | `NUMERIC(18,4)` | Sum of line totals pre-tax |
| `tax_total` | `NUMERIC(18,4)` | Sum of tax |
| `total` | `NUMERIC(18,4)` | subtotal + tax_total |

**Never use float/double** in DB or API wire format for money.

---

## 5. Lifecycle semantics (review decisions)

### 5.1 State machine

```text
draft → sent → accepted | rejected | expired
```

| Decision | Resolution |
|----------|------------|
| `sent → draft`? | **No** — no rollback to draft |
| Accept stale version? | **No** — accept must target `current_version_id` while `status=sent` |
| New version after `sent`? | **No** on same aggregate — negotiate reject/expiry, then **new Quote** |
| New version while `draft`? | **Yes** — `POST /versions` appends revision, updates `current_version_id` |
| `accepted` cancellable? | **No** in Quote layer — cancellation belongs to Order/Commerce PR |
| Who sets `expired`? | Manager/supervisor/admin via `POST /expire`; future cron on `valid_until` emits same audit event |

### 5.2 What counts as **acceptance**

**Quote acceptance (Sale layer):**

- Operator calls `POST /quotes/{id}/accept` on a `sent` quote.
- `accepted_version_id` implicit = `current_version_id` at accept time.
- Sets `quote.status = accepted`, `accepted_at`, freezes aggregate as **terminal**.
- Does **not** create Service Order, Commercial Confirmation, or Invoice.

**Not acceptance:** payment, signature, PO upload — those are Commerce milestones (later ADR).

### 5.3 Event table

| Event | Quote.status | Version impact |
|-------|--------------|----------------|
| `create` | `draft` | v1 draft |
| `update_draft` | `draft` | Patch current draft version + rebuild snapshot draft |
| `new_version` | `draft` | Append vN, set `current_version_id` |
| `send` | `sent` | Freeze `scope_snapshot` on current version |
| `accept` | `accepted` | Record `accepted_version_id` (= current) |
| `reject` | `rejected` | Terminal |
| `expire` | `expired` | Terminal |

---

## 6. Quote → Service Order handoff (next PR — design hook)

PR-1 stores everything SO needs inside frozen `scope_snapshot` on the **accepted version**.

Next PR contract (preview):

```text
POST /api/v1/service-orders/from-quote/{quote_id}
Preconditions:
  - quote.status = accepted
  - quote.accepted_version_id is set
Action:
  - COPY scope_snapshot → service_order.scope_snapshot (new row, no FK mutation)
  - SET service_order.client_account_id = quote.client_account_id
  - SET service_order.source_quote_id = quote.id
  - Do NOT mutate Quote
```

Quote remains immutable terminal record; SO owns execution lifecycle.

---

## 7. Module boundaries

| Module | May import Quote? | Notes |
|--------|-------------------|-------|
| `client_accounts` | No | Foundation stays independent |
| `quotes` (new) | Yes | Owns models + service |
| `sales` | API read only | `source_lead_id` traceability |
| `services` / SO | Next PR only | `from-quote` transition |
| `finance` | No | No invoice hooks in PR-1 |

---

## 8. Auditing

| Event | When | Payload minimum |
|-------|------|-----------------|
| `quote.created` | POST /quotes | quote_id, client_account_id, version_number |
| `quote.version_created` | POST /versions | quote_id, version_number |
| `quote.sent` | send | quote_id, version_id, version_number |
| `quote.accepted` | accept | quote_id, accepted_version_id |
| `quote.rejected` | reject | quote_id, reason? |
| `quote.expired` | expire / cron | quote_id, trigger=`manual\|valid_until` |

No full snapshot or PII in audit payload.

---

## 9. Resolved design decisions (review checklist)

| # | Topic | Decision |
|---|-------|----------|
| 1 | Aggregate stability | Quote is stable root; versions are append-only snapshots |
| 2 | Post-send immutability | Sent version rows are immutable |
| 3 | `current_version_id` | Deferred FK; set after version insert |
| 4 | `scope_snapshot` | Schema v1 with required `items[]`; not arbitrary JSON |
| 5 | Money | `NUMERIC` / decimal strings only |
| 6 | Currency | Required on quote |
| 7 | `quote_number` | Unique per tenant |
| 8 | `sent → draft` | Forbidden |
| 9 | Accept target | Current sent version only |
| 10 | `accepted` terminal | Yes for Sale layer |
| 11 | Post-accept cancel | Order/Commerce PR, not Quote |
