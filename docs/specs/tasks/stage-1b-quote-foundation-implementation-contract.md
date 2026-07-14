# Stage 1B — Quote Foundation Implementation Contract

**Status:** design-first — **pending review** (no runtime code until contract approved)  
**Owner:** Services / Sales backend  
**Parent ADR:** [`ADR-020`](../architecture/ADR-020-sales-to-engagement-commercial-model.md)  
**Prerequisite:** Stage 1A merged (ClientAccount), auto-seed merged (services intake)  
**Scope:** Quote persistence + lifecycle + ClientAccount link + `scope_snapshot`. **No** Service Order, Commercial Confirmation, Invoice, Billing.

---

## 1. Goal

Learn to **create and store a commercial proposal** as a first-class domain object after identity (Stage 1A) and intake (auto-seed) are stable.

After Stage 1B PR-1, a manager can:

1. Create a **Quote** for a `ClientAccount`.
2. Maintain **versioned** commercial terms (`QuoteVersion`).
3. Move lifecycle: `draft → sent → accepted | rejected | expired`.
4. Freeze commercial scope in **`scope_snapshot`** at send/accept boundaries.
5. Read/update via tenant-scoped backend CRUD.

**Out of scope (explicit):**

- Service Order creation or Quote → SO transition
- Commercial Confirmation registry
- Invoice / Billing Event / Finance hooks
- Readiness engine / Engagement activation
- Frontend product UI (wireflow only in this phase)
- Questionnaire / form infrastructure changes

---

## 2. Vertical isolation rule

| Layer | Stage | Status after merge #19 |
|-------|-------|------------------------|
| Identity | 1A ClientAccount | ✅ merged |
| Intake | auto-seed targeted-advertising | ✅ merged |
| **Commercial proposal** | **1B Quote Foundation** | 🎯 next PR |
| Order | 1B+ Quote → Service Order | later PR |
| Commerce | Commercial Confirmation | later PR |
| Billing | Invoice / Billing Event | later PR |

Do **not** mix provisioning, forms, Quote, and Service Order in one PR.

---

## 3. Object model (summary)

Full detail: [`stage-1b-quote-object-model.md`](../architecture/stage-1b-quote-object-model.md).

### 3.1 `quotes`

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | UUID | RLS |
| `client_account_id` | UUID | **Required** FK → `client_accounts` |
| `own_company_id` | UUID, nullable | Operating company scope (from account/lead) |
| `quote_number` | string | Human-readable; unique per `(tenant_id, quote_number)` |
| `title` | string | Product label |
| `status` | enum | `draft` \| `sent` \| `accepted` \| `rejected` \| `expired` |
| `currency` | string(3) | **Required** ISO 4217; all money uses this currency |
| `current_version_id` | UUID, nullable | Pointer to active version; FK deferred (see object model §2.3) |
| `accepted_version_id` | UUID, nullable | Frozen on accept; must equal version sent |
| `source_lead_id` | UUID, nullable | Traceability to Sales Inquiry transport |
| `valid_until` | date, nullable | Drives `expired` transition |
| `sent_at` | timestamptz, nullable | Set on `draft → sent` |
| `accepted_at` | timestamptz, nullable | Set on `sent → accepted` |
| `rejected_at` | timestamptz, nullable | Set on `sent → rejected` |
| `expired_at` | timestamptz, nullable | Set on expiry job or manual expire |
| `created_by_user_id` | UUID, nullable | Audit |
| `created_at` / `updated_at` | timestamptz | |

### 3.2 `quote_versions`

Immutable commercial revision rows. **After send, version row is frozen.**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | PK |
| `tenant_id` | UUID | RLS |
| `quote_id` | UUID | FK → `quotes` |
| `version_number` | int | Monotonic per quote; starts at 1 |
| `scope_snapshot` | JSONB | Canonical commercial scope (see §4) — includes `items[]` |
| `subtotal` / `tax_total` / `total` | `NUMERIC(18,4)` | **No float** — server-computed |
| `notes_internal` | text, nullable | Not client-visible |
| `notes_client` | text, nullable | Shown on send |
| `sent_at` | timestamptz, nullable | Set when this version is sent |
| `created_by_user_id` | UUID, nullable | |
| `created_at` | timestamptz | |

**Rules (review-approved):**

- Edit commercial terms **only** while `quote.status = draft` on `current_version`.
- `POST /versions` while `draft` appends a new revision.
- **No** `sent → draft`. **No** new versions after `sent` on the same aggregate.
- Further proposals after `rejected` / `expired` → **new Quote** record.

---

## 4. `scope_snapshot` contract

Structured document — **not arbitrary JSON**. Full schema: object model §4.

Required root keys: `schema_version`, `title`, `service_family`, `offering_code`, `currency`, `items[]`.

Each `items[]` element requires: `item_id`, `title`, `quantity`, `unit`, `unit_price` (decimal strings).

| Transition | Snapshot action |
|------------|-----------------|
| `draft` edits | Rebuild draft snapshot on current version |
| `draft → sent` | Inject `client_account`, `captured_at`; freeze row |
| `sent → accepted` | `accepted_version_id` points to frozen snapshot |
| `sent → rejected` / `expired` | No mutation |

**Acceptance (Sale layer):** `POST /accept` on `sent` quote where `version_id === current_version_id`. Terminal for Quote; cancellation is Order/Commerce concern.

---

## 5. Lifecycle state machine

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> sent: send()
    sent --> accepted: accept(current_version)
    sent --> rejected: reject()
    sent --> expired: expire()
    accepted --> [*]
    rejected --> [*]
    expired --> [*]
```

| Status | Meaning | Allowed mutations |
|--------|---------|-------------------|
| `draft` | Composing proposal | PATCH; POST /versions |
| `sent` | Delivered to client | accept / reject / expire only |
| `accepted` | Sale layer terminal | Read-only; cancel → Order PR |
| `rejected` | Declined terminal | Read-only; new proposal → new Quote |
| `expired` | Validity ended terminal | Read-only; new proposal → new Quote |

**Forbidden:** `sent → draft`, accepting non-current version, mutating sent snapshot.

**Invariant:** `accepted` does **not** create Service Order (next PR). SO copies `accepted_version.scope_snapshot`.

---

## 6. API contract (summary)

Full detail: [`stage-1b-quote-api-contract.md`](../api/stage-1b-quote-api-contract.md).

Prefix: `/api/v1/quotes`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | List (filter: status, client_account_id) |
| POST | `/` | Create draft quote + v1 |
| GET | `/{id}` | Detail + current version |
| PATCH | `/{id}` | Update draft metadata only |
| POST | `/{id}/versions` | New draft revision (only while `status=draft`) |
| POST | `/{id}/send` | `draft → sent`, freeze snapshot |
| POST | `/{id}/accept` | `sent → accepted` |
| POST | `/{id}/reject` | `sent → rejected` |
| POST | `/{id}/expire` | `sent → expired` (manual; job later) |
| GET | `/{id}/versions` | Version history |
| GET | `/{id}/versions/{version_id}` | Version detail |

RBAC: `viewer` read; `manager` / `supervisor` / `admin` write + transitions.

---

## 7. UI wireflow (design only)

Full detail: [`stage-1b-quote-ui-wireflow.md`](../ux/stage-1b-quote-ui-wireflow.md).

PR-1 ships **no frontend**. Wireflow defines Stage 1B-UI follow-up.

---

## 8. Sequences

Full detail: [`stage-1b-quote-lifecycle-sequences.md`](../workflows/stage-1b-quote-lifecycle-sequences.md).

---

## 9. Planned migrations (list only — no Alembic in design branch)

| Revision | Purpose |
|----------|---------|
| `202607141600_quote_foundation` | `quotes`, `quote_versions` tables, indexes, FKs |
| `202607141601_quote_status_check` | DB check constraints on status enum + version_number uniqueness |

**Indexes:**

- `UNIQUE (tenant_id, quote_number)`
- `UNIQUE (quote_id, version_number)`
- `(tenant_id, client_account_id, status)`
- `(tenant_id, status, updated_at DESC)`

**FK rules:**

- `quotes.client_account_id` → `client_accounts.id` (no cascade delete)
- `quote_versions.quote_id` → `quotes.id` (restrict delete)

---

## 10. PR-1 deliverables (first implementation PR)

| Include | Exclude |
|---------|---------|
| Alembic migrations §9 | Service Order tables/API |
| SQLAlchemy models | Commercial Confirmation |
| Repository + service layer | Invoice / billing hooks |
| `/api/v1/quotes` CRUD + transitions | Frontend pages |
| RBAC + tenant guards | Questionnaire changes |
| Unit + API tests (lifecycle matrix) | General provisioning engine |

---

## 11. Required tests (implementation PR)

| Scenario | Expected |
|----------|----------|
| Create draft for ClientAccount | Quote + version 1 in `draft` |
| Update draft line items | Mutates current draft version |
| Send quote | `sent`, snapshot frozen, `sent_at` set |
| Accept sent quote | `accepted`, `accepted_at` set; no SO row |
| Reject sent quote | `rejected` |
| Expire sent quote | `expired` |
| Cross-tenant read | 404 / forbidden |
| Delete ClientAccount | Quote preserved (no cascade) |
| Invalid transition (accept draft) | 409 conflict |
| Replay send on sent | `200` idempotent same version |
| Accept with wrong version_id | `409 stale_version` |
| POST /versions while sent | `409` |
| New quote after rejected | Allowed (new aggregate) |
| Optimistic lock stale PATCH | `409 stale_quote` |

---

## 12. Merge gate (before starting implementation)

- [x] PR #18 cleanup merged
- [x] PR #19 auto-seed merged
- [x] Post-merge smoke: services tenant provisioning tests pass
- [x] Legacy tenant recovery test passes
- [ ] **Design PR reviewed and contract status → approved**
- [ ] Integration CI green — fix SPA path literals in **separate chore PR** (not design / not Stage 1B runtime)
- [ ] `feat/stage-1b-quote-foundation` branched from updated integration line

---

## 13. Follow-on PRs (ordered)

1. **PR-1:** Quote Foundation (this contract)
2. **PR-2:** Quote → Service Order transition
3. **PR-3:** Commercial Confirmation registry
4. **PR-4:** Billing Event / Invoice handoff

---

## 14. References

- [`ADR-020`](../architecture/ADR-020-sales-to-engagement-commercial-model.md)
- [`stage-1a-client-account-implementation-contract.md`](stage-1a-client-account-implementation-contract.md)
- [`stage-1b-quote-object-model.md`](../architecture/stage-1b-quote-object-model.md)
- [`stage-1b-quote-api-contract.md`](../api/stage-1b-quote-api-contract.md)
- [`ui-constitution-v1.md`](../architecture/ui-constitution-v1.md) — Клиент → Заказ vocabulary
