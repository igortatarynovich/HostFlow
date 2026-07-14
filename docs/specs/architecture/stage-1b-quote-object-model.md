# Stage 1B — Quote Object Model

**Status:** design-first  
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

## 2. Entities

### 2.1 Quote (aggregate root)

**Purpose:** operational handle for a commercial proposal tied to one `ClientAccount`.

| Concern | Owner field |
|---------|-------------|
| Who is the client? | `client_account_id` (required) |
| Who sells? | `own_company_id` (nullable, tenant operating company) |
| What stage? | `status` |
| What is current terms revision? | `current_version_id` |
| Traceability | `source_lead_id` (optional) |

**Not in PR-1:**

- `service_order_id`
- `billing_company_id`
- `commercial_confirmation_id`

### 2.2 QuoteVersion (immutable revision)

**Purpose:** versioned commercial terms + frozen `scope_snapshot`.

| Rule | Detail |
|------|--------|
| Append-only after send | Once parent quote is `sent`, existing versions are immutable |
| Monotonic `version_number` | `UNIQUE (quote_id, version_number)` |
| Draft edits | Only the latest version while quote.status = `draft` |

### 2.3 Relationships

```text
Tenant 1──* Quote
ClientAccount 1──* Quote
Quote 1──* QuoteVersion
Quote 0..1──1 QuoteVersion (current_version_id)
Lead 0..1──* Quote (source_lead_id, no FK cascade)
```

**Tenant boundary:** `Quote.tenant_id` must equal `ClientAccount.tenant_id`. Enforced in service layer + DB composite checks where practical.

---

## 3. `scope_snapshot` schema v1

| Key | Type | Required | Notes |
|-----|------|----------|-------|
| `schema_version` | int | yes | Always `1` in PR-1 |
| `service_family` | string | yes | e.g. `targeted_advertising` |
| `offering_code` | string | yes | Tenant-defined code; catalog later |
| `parameters` | object | yes | Service-specific JSON |
| `client_account` | object | yes | `{ id, display_name }` denormalized |
| `primary_company_id` | string, null | no | From ClientAccount shortcut |
| `captured_at` | ISO datetime | yes | Set at send |

**Design intent:** `scope_snapshot` is the handoff artifact for future Service Order PR. SO will **copy** snapshot, not join live Quote rows.

---

## 4. `line_items` schema v1 (MVP)

```json
[
  {
    "line_id": "uuid",
    "kind": "service",
    "code": "meta_campaign_setup",
    "title": "Konfiguracja kampanii Meta",
    "quantity": 1,
    "unit": "fixed",
    "unit_price": 1500.00,
    "currency": "PLN",
    "tax_rate": 0.23,
    "metadata": {}
  }
]
```

Totals on `quote_versions`: `subtotal`, `tax_total`, `total` — computed server-side on write.

---

## 5. Lifecycle semantics

| Event | Quote.status | Version impact |
|-------|--------------|----------------|
| `create` | `draft` | Create v1 |
| `update_draft` | `draft` | Patch v1 (or current draft version) |
| `send` | `sent` | Freeze snapshot on current version |
| `accept` | `accepted` | None |
| `reject` | `rejected` | None |
| `expire` | `expired` | None |

**Quote acceptance ≠ Commercial Confirmation** (ADR-020). Acceptance closes the Sale proposal; legal/financial confirmation is a separate layer.

---

## 6. Module boundaries

| Module | May import Quote? | Notes |
|--------|-------------------|-------|
| `client_accounts` | No | Foundation layer stays independent |
| `quotes` (new) | Yes | Owns models + service |
| `sales` | Read via API | Inquiry may link `source_lead_id` |
| `services` / SO | No in PR-1 | Next PR adds transition service |
| `finance` | No | No invoice hooks |

---

## 7. Auditing

Emit activity events (PR-1 minimum):

| Event | When |
|-------|------|
| `quote.created` | POST /quotes |
| `quote.sent` | send transition |
| `quote.accepted` | accept transition |
| `quote.rejected` | reject transition |
| `quote.expired` | expire transition |

Payload: `{ quote_id, client_account_id, version_number, status }` — no full PII dump.

---

## 8. Open questions (resolve before implementation PR)

| # | Question | PR-1 default |
|---|----------|--------------|
| 1 | Allow `reopen` rejected/expired → draft? | **No** — keep read-only terminal states |
| 2 | Auto-generate `quote_number`? | **Yes** — `Q-{tenant_slug}-{seq}` |
| 3 | Soft-delete quotes? | **No** — status-only |
| 4 | Multi-currency per tenant? | Single quote currency; tenant default |
