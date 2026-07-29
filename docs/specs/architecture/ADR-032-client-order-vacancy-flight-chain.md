# ADR-032: Sales Service Order → Order Line → Vacancy → Billable Item

**Status:** Accepted  
**Date:** 2026-07-28  
**Layer of change:** Sales commercial demand · Recruitment vacancy · Acquisition Flight · Finance billing  
**Authors:** Product + Platform architecture  
**Checklist:** [`architecture-review-checklist.md`](architecture-review-checklist.md) (L0 ×10) — completed below  
**Does not amend L0 constitution** — references P-01…P-05 / INV / Catalog only  
**Related:** [ADR-020](ADR-020-sales-to-engagement-commercial-model.md) · [ADR-023](ADR-023-recruitment-sales-module-separation.md) · [ADR-024](ADR-024-acquisition-campaigns-intake-routing.md) · [ADR-004](ADR-004-five-product-modules-and-billing-events.md) · [modules/sales_orders.md](../modules/sales_orders.md)

---

## 1. Context

Growth fulfillment needs a measurable chain from client demand to invoice. An earlier draft locked **1 Client Order = 1 Vacancy** and **order completed → invoice**. That direction is correct for ownership (Sales / Recruitment / Acquisition) but **too rigid and unsafe for billing**:

1. Client payment terms must not silently rewrite historical deals.
2. Closing vacancy headcount is not a universal billable moment.
3. One commercial order often spans multiple roles/rates/locations.

This ADR replaces that draft.

---

## 2. Decision

### 2.1 Ownership

| Entity | Module |
|--------|--------|
| Client Account (+ commercial **defaults**) | **Sales** |
| **Service Order** (deal + commercial **snapshot**) | **Sales** |
| **Order Line** (one demand line) | **Sales** |
| Vacancy | **Recruitment** |
| Campaign / Flight | **Acquisition / Marketing** |
| Billable Item / Invoice | **Finance / Billing** |

### 2.2 Naming (collision)

Product UI term **«Service Order»** (Sales commercial) must **not** overload Services-module table `service_orders` (additional-services catalog).

| Product | Physical table (V1) |
|---------|---------------------|
| Service Order (Sales) | `sales_orders` |
| Order Line | `sales_order_lines` |
| Billable Item | `sales_billable_items` |

Services-module `service_orders` remain catalog-service fulfillment — unchanged.

### 2.3 Strict chain

```text
ClientAccount
  → Service Order (deal snapshot)
    → Order Line* (role / location / qty / rate / billing trigger)
      → Vacancy (1 active Vacancy per Order Line)
        → Campaign / Flight* (executor waves)
          → Recruitment Result (hire / handoff / start / …)
            → Billable Item (billing rules of the Line)
              → Invoice
```

- **Flight** executes Vacancy need (never invents quantity/price).
- **Vacancy** executes **one Order Line** (`headcount` / role / location are **projections** of the Line when linked).
- **Invoice** is assembled from **Billable Items**, never directly from “vacancy filled”.

### 2.4 Client defaults vs Order snapshot

**Client Account** may store **defaults only**: default currency, payment delay, preferred settlement method, payer / bank details, tax defaults, default guarantee period.

**Service Order** stores the **agreed snapshot** for that deal (immutable for billing after first billable event without amendment/version):

- currency  
- payment term  
- payment model  
- payer / VAT  
- guarantee / free-replacement policy  
- when the right to invoice arises (policy header)  
- additional commercial terms  

**Order Line** stores line-specific commercial + fulfillment:

- role / title, location  
- quantity (headcount)  
- rate, unit of charge  
- **billing_trigger** (see §2.5)  
- line guarantee overrides (optional)

Changing Client defaults **must not** rewrite open or historical Orders.

### 2.5 Billable events (not “order completed”)

Closing Order Line / Vacancy headcount is **one possible** trigger, not the only one.

Canonical `billing_trigger` values (V1 closed set, extend via registry later):

| Code | Meaning |
|------|---------|
| `candidate_hired` | Accrue per hired candidate |
| `candidate_started_work` | Accrue when work started |
| `guarantee_period_passed` | Accrue after guarantee |
| `milestone_accepted` | Accrue on accepted milestone |
| `headcount_completed` | Accrue when line quantity filled |
| `monthly_service_period_closed` | Accrue per service month |

```text
Recruitment Result → evaluate Order Line billing rules → Billable Item → Invoice
```

### 2.6 Cardinality

- One **Service Order** → many **Order Lines**.
- One **Order Line** → **at most one active Vacancy**.
- One **Vacancy** → at most one Order Line (`vacancies.order_line_id`).
- One Vacancy → many Flights.
- Freeform Vacancy (no Order Line) remains allowed for internal/test intake — **no commercial fields**.

### 2.7 Vacancy create modes

1. **Freeform** — no client order path; no `order_line_id`; headcount optional/manual; no billing.
2. **Under order** — Client → open Service Order → **free** Order Line → Vacancy binds `order_line_id`; role/location/headcount **read from Line** (not editable as SoT on Vacancy).

### 2.8 Forbidden

- Price / billable quantity SoT on Campaign or Flight.
- Second SoT headcount on Vacancy when linked to Order Line.
- Client fulfillment Vacancy without Order Line.
- Two active Vacancies on the same Order Line.
- Applying **current** Client defaults to an existing Order’s billing.
- Creating Invoice directly from Vacancy/Order “completed”.
- Changing Order commercial snapshot after Billable Items exist without **amendment / version**.

---

## 3. Runtime shape (V1 this PR)

- Tables: `sales_orders`, `sales_order_lines`, `sales_billable_items` (create path stub; full invoice assembly = Finance follow-on).
- `vacancies.order_line_id` nullable FK; **UNIQUE** among non-null (1 Line ↔ 1 Vacancy).
- Sales HTTP: list/create/patch orders & lines; list unlinked lines for Vacancy create.
- Recruitment: Vacancy create/patch bind to Order Line with server enforcement.
- Acquisition: unchanged CampaignTarget(vacancy); Flight remains executor.

Follow-on (explicitly out of V1 merge if needed): Client Account defaults UI, amendment versioning, Flight KPI gap-to-line. Auto billable accrual + Invoice composer from pending billables — **shipped**.

---

## 4. Architecture review checklist (L0 ×10)

| # | Answer |
|---|--------|
| 1 Owner | Sales owns Order/Line; Recruitment Vacancy; Acquisition Flight; Finance Billable/Invoice |
| 2 Existing? | Services `service_orders` ≠ this; ADR-020 Service Order direction aligned, lines + billable add precision |
| 3 Adapter | Module HTTP; Acquisition via vacancy target only |
| 4 Boundary | No commercial SoT in Marketing; no Invoice from Vacancy |
| 5 Settings | Client defaults ≠ Order snapshot |
| 6 SoT | Line = demand qty/rate/trigger; Vacancy projects when linked |
| 7 Events | Billable Item creation from recruitment results (follow-on wiring) |
| 8 Requires | Sales + Recruitment; Finance consumes Billable Items |
| 9 License | No new license |
| 10 Contract | Additive tables/APIs |

**INV:** Does not falsify INV-01…17; ADR-024 Campaign shape unchanged (still no `order_id` on Campaign).

---

## 5. Supersedes (product draft)

Supersedes the interim product lock «1 Client Order = 1 Vacancy → invoice on complete» discussed 2026-07-28 pre-ADR. Any `client_orders` / `vacancies.client_order_id` sketch is **rejected** — do not ship.

---

## History

- 2026-07-28: Accepted — Order + Order Line + Billable Item; Client defaults vs snapshot; Flight executor; naming split from Services `service_orders`.
- 2026-07-28: Runtime — auto Billable Item V1 for `candidate_hired` / `candidate_started_work` / `headcount_completed` via Sales `contracts` facade (Recruitment + HR hooks).
- 2026-07-29: Runtime — Invoice composer from pending `sales_billable_items` (`POST …/sales-orders/{id}/invoices`).
