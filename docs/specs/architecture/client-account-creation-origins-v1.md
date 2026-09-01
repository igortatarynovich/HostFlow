# ClientAccount Creation Origins v1

**Status:** **NORMATIVE (L2 — Product / architecture canon)**  
**Date:** 2026-07-20  
**Trusted base:** `integration/release-product-a-b` @ `328506f7`+  
**Parents:** [Sales Domain Pipeline v1](sales-domain-pipeline-v1.md) · [ADR-020](ADR-020-sales-to-engagement-commercial-model.md) · [Stage 1A ClientAccount contract](../tasks/stage-1a-client-account-implementation-contract.md) · [Phase 2 Flow Spec](../workflows/adr022-phase2-sales-only-capability-flow.md)  
**Implements later:** Sales application service `create_client_account_manually` (not in this docs-slice)

> Every `ClientAccount` has a **truthful immutable origin**.  
> **Not** every `ClientAccount` must come from a `SalesInquiry`.

---

## 1. Purpose

Fix two independent ways a Sales-owned `ClientAccount` may appear, without collapsing them into one fake intake path.

Phase 2 sealed the **inquiry → conversion** spine. This document adds the second first-class origin — **manual creation** — and forbids inventing Lead / SalesInquiry / Flights provenance for it.

---

## 2. Canonical origins (v1)

| `origin_type` | Path | Lineage shape |
|---------------|------|---------------|
| `sales_inquiry_conversion` | SalesInquiry → Review? → Convert Mapping → ClientAccount | Full conversion chain (Pipeline v1) |
| `manual_creation` | Manual Client Creation → ClientAccount | Short: creation event → ClientAccount |

```text
1) From appeal / advertising intake
   SalesInquiry → Review? → Convert → ClientAccount
   origin_type = sales_inquiry_conversion

2) Hand-created by operator
   Manual Client Creation → ClientAccount
   origin_type = manual_creation
```

Both produce the **same** Sales-owned object type (`ClientAccount`). Origins differ; validation / ownership / permissions / audit / idempotency concepts are shared where possible.

---

## 3. Invariants

1. **INV-CAO-01** — Every ClientAccount has exactly one immutable `origin_type` recorded at creation (or migrated explicitly later).  
2. **INV-CAO-02** — `sales_inquiry_conversion` is written only by Convert Mapping (`convert_sales_inquiry_mapping`) after Pipeline v1 gates.  
3. **INV-CAO-03** — `manual_creation` must **not** create a fictitious Lead, SalesInquiry, Flights dispatch, or convert mapping.  
4. **INV-CAO-04** — Manual creation must **not** imitate advertising / intake provenance.  
5. **INV-CAO-05** — Duplicate handling for manual create is **Sales-owned** (not Flights review, not Recruitment).  
6. **INV-CAO-06** — Traceability for conversion remains Pipeline v1 write-once lineage; manual origin uses a **separate shorter** creation record (see §5).  
7. **INV-CAO-07** — Pre-origins paths (`create_client_account_service`, Lead `convert-client`, entity-profile conversion) are **non-canonical** until rewired or migrated to a named origin.

---

## 4. Origin: `sales_inquiry_conversion`

**Owner:** Sales Convert Mapping.  
**Canon:** [Pipeline v1](sales-domain-pipeline-v1.md) · [convert mapping task](../tasks/sales-questionnaire-convert-mapping.md) · [traceability](../tasks/sales-inquiry-traceability.md).

**Must:**

- Pass review gate when review is required.  
- Require confirmed Sales destination + opaque Flights ledger.  
- Stamp `convert_mapping_v1` + `sales_inquiry_lineage_v1`.  
- Fail-closed on missing context / Recruitment destination / unresolved review.

**Must not:**

- Re-run Flights.  
- Rematch as part of convert (apply Review SoT when present).  
- Invent Recruitment context.

---

## 5. Origin: `manual_creation`

**Owner:** Sales application service (logical name: `create_client_account_manually`).  
**Not** Convert Mapping. **Not** Flights. **Not** a fake SalesInquiry.

### 5.1 Shared concerns (reuse conceptually)

| Concern | Expectation |
|---------|-------------|
| Field validation | Same ClientAccount validation rules as Sales |
| Duplicate checks | Same identity evidence matrix as Sales match policy allows for *existing* ClientAccounts |
| Tenant / own-company ownership | Identical isolation rules |
| Permissions | Sales operator permission to create clients |
| Audit | Actor + timestamp + decision trail |
| Idempotency | Client-supplied or server-issued idempotency key |

### 5.2 Forbidden

| Forbidden | Why |
|-----------|-----|
| Create dummy Lead | False transport; pollutes intake |
| Create dummy SalesInquiry | False appeal; breaks SoT |
| Create Flights dispatch / ledger | False advertising provenance |
| Call convert mapping | Wrong contract |
| Stamp conversion lineage as if inquiry existed | False traceability |
| Set `source_lead_id` to invent linkage | Lie about origin |

### 5.3 Lineage / creation record (short)

Immutable creation reference (Sales-owned; storage shape left to implementation PR):

| Field | Required |
|-------|----------|
| `origin_type` | `manual_creation` |
| `actor_user_id` | yes |
| `tenant_id` / `own_company_id` | yes |
| `created_at` | yes |
| `idempotency_key` | yes |
| `reason` / `source_note` | optional |
| `creation_ref` | immutable id of this creation event |
| `duplicate_decision` | when force-create or match-open (see §6) |

```text
Manual creation event → ClientAccount
```

No Flights node. No SalesInquiry node. No convert mapping node.

---

## 6. Duplicate policy (manual create)

Sales-owned flow — **not** Flights ambiguous-match review (that review is SalesInquiry-scoped).

| Situation | Behaviour |
|-----------|-----------|
| No clear existing ClientAccount match | Create with `origin_type=manual_creation` |
| Exactly one strong existing ClientAccount | Offer **open existing** (do not auto-create) |
| Several possible matches | **Manual duplicate review** (operator chooses open / create-new / cancel) |
| Operator explicitly confirms create-new despite candidates | Create with recorded `duplicate_decision` |

Fail-closed: silent merge, silent attach, or auto-create on ambiguous evidence are forbidden.

---

## 7. Reserved future origins (names only)

| `origin_type` | Intent |
|---------------|--------|
| `import` | Bulk / migration import with import batch ref |
| `api` | External API partner create with API credential ref |
| `partner_referral` | Partner-attributed create without Flights advertising spine |

Do not implement in v1. Do not overload `manual_creation` for these.

---

## 8. Relationship to existing code (honest)

| Path today | Status under this canon |
|------------|-------------------------|
| `convert_sales_inquiry_mapping` | Canonical writer for `sales_inquiry_conversion` |
| `create_client_account_manually` / ClientAccounts POST | Canonical writer for `manual_creation` |
| Operator Add Client (`POST /tenants/{id}/links` with `display_name`, `POST /companies` with `company_role=client`) | Creates Company (and optional tenant link) **and** stamps `manual_creation` ClientAccount linked via `primary_company_id` |
| `POST /client-accounts/ensure-from-client-companies` | Backfill for local client companies created before that wiring |
| Lead `convert_client_lead` HTTP / Sales mutations via Lead | Non-canonical for Sales spine — rewire to Convert Mapping (Pipeline v1 §3) |
| Entity-profile `create_client_from_lead_conversion` | Pre-origins / migrate |

The original 2026-07-20 slice did not change runtime. Operator Add Client wiring (2026-08-18) does: a local client company is not campaign-ready until a `manual_creation` ClientAccount exists.

---

## 9. Implementation order (after this PR)

**Superseded for global sequencing** by [`../tasks/sales-to-comms-sequential-queue.md`](../tasks/sales-to-comms-sequential-queue.md).

Locked product order (relevant excerpt):

1. **Capability UI** (`feat/sales-capability-ui`) — display-only.  
2. **Manual ClientAccount creation** (`feat/manual-client-account-creation`) — implement `create_client_account_manually` per §5–§6; optional persist `origin_type`; rewire ClientAccounts create HTTP.  
3. **Pipeline v1 product wiring** — convert via mapping; consume Review SoT; demote Lead UI.  
4. Communication Stages 4–7 (after Sales 1–3).

This Origins document remains the **contract** for `manual_creation`; it no longer defines queue order ahead of Capability UI.

---

## 10. History

- 2026-07-20: Origins v1 docs-slice — `sales_inquiry_conversion` + `manual_creation`; forbid fake Lead/SI/Flights for manual path.  
- 2026-07-20: §9 order superseded by Sales→Comms sequential queue (Capability UI before manual create runtime).
- 2026-08-18: Operator Add Client (no client tenant required) wires `manual_creation` ClientAccount so campaigns/ads can target the same client shown on Sales → Clients.
- 2026-09-01: Restored Add Client → ClientAccount wiring after it failed to land on `integration/release-product-a-b`.
