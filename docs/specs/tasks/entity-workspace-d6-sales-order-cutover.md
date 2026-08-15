# Entity Workspace D6 — Sales Order Cutover (Phase D)

**Status:** **COMPLETE** ([#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262) · `346f6fcc` · merge `bc819768`)  
**Next:** [D7 Vacancy Cutover](entity-workspace-d7-vacancy-cutover.md) (brief; feat locked)  
**Branch (docs):** `docs/entity-workspace-d6-sales-order-cutover` ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261)  
**Branch (code):** `feat/entity-workspace-d6-sales-order-cutover` ✅ [#262](https://github.com/igortatarynovich/HostFlow/pull/262)  
**Parents:** [D5 Client Cutover](entity-workspace-d5-client-cutover.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [D3 Consumer Cutover](entity-workspace-d3-consumer-cutover.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [D1 Contract Seal](entity-workspace-d1-contract-seal.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [ADR-032](../architecture/ADR-032-client-order-vacancy-flight-chain.md) · [A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md)

> D5 bound Client to the D2 slot catalog.  
> D6 binds **Sales Order** (`SalesOrder` / `/app/sales/orders/:orderId`) to that catalog — one consumer, same enabled slots.  
> D6 does **not** enable D2 `documents`, mint Catalog Passport, or cut over HR / Vacancy / Services `/app/orders`.

**Naming (do not collapse):** this **Entity Workspace D6** is not D5 Client cutover, not D4 Candidate cutover, not D3 Sales Inquiry cutover, not D2 composition contract, not D1 contract seal, not PX chrome land, not Documents Phase E. Shell `documents` **nav** ≠ D2 `documents` **composition slot**. Sales Order here is ADR-032 commercial deal (`/app/sales/orders`), **not** Services-module `service_order` (`/app/orders`) and **not** the PX mock `order` / `MOCK_ORDER_MODEL`.

---

## Why this slice

Product Track is Sales → Communication. D3 bound Sales Inquiry. D5 bound Client.  
The remaining Sales hole: Sales Order detail is still a one-off card at `/app/sales/orders/:orderId` (`SalesOrderDetailPage`) beside the D2 catalog.

On tip today:

| Surface | What it is | D6 status |
|---------|------------|-----------|
| Sales Inquiry (`ApplicationSalesDetailPanel`) | D3 first consumer | ✅ leave as-is |
| Candidate `EntityWorkspacePage` | D4 consumer; D1 Shell adapter | ✅ leave as-is |
| Client (`Companies` · `/app/clients/:id`) | D5 consumer | ✅ leave as-is |
| Sales Order (`SalesOrderDetailPage` · `/app/sales/orders/:id`) | ADR-032 commercial deal; not on D2 catalog | **this consumer** |
| HR / Vacancy / Services `/app/orders` | module workspaces | **Out of D6** |

Without an explicit Sales Order binding, Sales will keep a parallel order shell, and a later bind of Services `/app/orders` (or PX mock `order`) will be misread as this cutover — or as D2 `documents` enable.

---

## Goal

Sales Order composes D2 **enabled** slots; Shell nav (if adopted) stays adapter-only:

```text
Sales Order detail (Sales-owned overview body)
  ├── overview          ← required; Sales-owned
  ├── timeline          ← content slot (not a second Activity product)
  ├── communication     ← Communication public contracts / adapters only
  ├── forms             ← Forms public contracts only
  ├── documents         ← reserved empty (Phase E)
  └── context-rail      ← D1 chrome slot
```

Modules configure **which enabled slots** they turn on. They do **not** invent new platform slot kinds (`contacts` / `relations` / `billing` as D2 slots). Shell `EntityWorkspaceSectionId` stays adapter navigation — **not** the composition SoT.

**Hard distinction (unchanged from D5):**

| Id | Contract | D6 rule |
|----|----------|---------|
| Shell `documents` | `EntityWorkspaceSectionId` adapter nav | May exist as **module nav**; not a D2 slot |
| D2 `documents` | `compositionSlots.ts` platform slot | **Must stay reserved** until Phase E |
| Sales Order | ADR-032 `/app/sales/orders/:id` | **this consumer** |
| Services order | `/app/orders` · `service_order` | **Out of D6** |
| PX mock `order` | `MOCK_ORDER_MODEL` (`service_orders`) | Chrome mock; **not** this consumer |

D6 **must not** map any Sales Order docs surface → `ENTITY_WORKSPACE_ENABLED_SLOT_IDS`.

---

## Consumer (normative)

**Sales Order** (`SalesOrder`, live route `/app/sales/orders/:orderId`, page `SalesOrderDetailPage`) is the D6 cutover target.

**Cutover means:**

1. Sales Order detail declares D2 enabled slots ⊆ `{overview, timeline, communication, forms, context-rail}`.  
2. Platform slots (`communication`, `forms`) go through public adapters only (Architecture Rule 2).  
3. Communication lists threads via public `listCommunicationThreads`. Fold by `SalesOrder.company_id` as `entityType: 'company'` (same fold as D5 Client). Do **not** mint a new `sales_order` Communication origin. Do **not** query `entityType: 'service_order'`.  
4. Forms uses public `listFormsPlatformHandlers()` (`/platform/forms/handlers`). Do **not** invent a Sales Order handler; Sales Inquiry `creates` includes `'sales_inquiry'` is enough to prove the adapter.  
5. Shell `EntityWorkspaceSectionId` is not collapsed into `EntityWorkspaceSlotId`.  
6. D2 `documents` stays reserved / cannot be enabled.  
7. No parallel Sales Order workspace / fifth shell beside this compose. Reusing D1 `EntityWorkspaceShell` as adapter chrome is allowed; inventing a new shell kind is not. A full `SalesOrderDetailPage` rewrite is **not** required for cutover.

**Cutover does not mean:** Documents Phase E; Catalog Passport; HR / Vacancy / Services `/app/orders` cutover; Kit Baseline chrome file land; Forms P3–P5; collapsing PX mock `order` into this consumer; treating invoice compose as a D2 slot.

---

## Locked principle

```text
D1  → who owns Entity Workspace + chrome/adapter boundary
D2  → which slots exist and how platforms compose
D3  → first consumer (Sales Inquiry)
D4  → Candidate binds to D2 slots; Shell nav ≠ composition
D5  → Client binds to D2 slots
D6  → Sales Order binds to D2 slots (this)
D7  → Vacancy binds to D2 slots
D8+ → remaining consumers (HR employee / Services /app/orders)
```

D6 **must not**:

- enable D2 `documents` or treat an order docs surface as that enable  
- collapse `EntityWorkspaceSectionId` into `compositionSlots.ts`  
- cut over HR / Vacancy / Services-module `/app/orders`  
- bind PX mock `order` / `MOCK_ORDER_MODEL` as the D6 consumer  
- mint Entity Catalog Passport / Manifest  
- mint a new Communication origin type for `sales_order`  
- land Kit Baseline chrome as a substitute for cutover  
- open Documents Phase E, Billing, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- invent a second Sales Order shell or promote Sales Order Workspace into the kit  
- rewrite `SalesOrderDetailPage` as the definition of cutover  

---

## Phase D ladder

| Slice | Focus | Status |
|-------|--------|--------|
| **D1** | Contract seal | ✅ [#251](https://github.com/igortatarynovich/HostFlow/pull/251)/[#252](https://github.com/igortatarynovich/HostFlow/pull/252) |
| **D2** | Composition contract (slots) | ✅ [#253](https://github.com/igortatarynovich/HostFlow/pull/253)/[#254](https://github.com/igortatarynovich/HostFlow/pull/254) |
| **D3** | First consumer (Sales Inquiry) | ✅ [#255](https://github.com/igortatarynovich/HostFlow/pull/255)/[#256](https://github.com/igortatarynovich/HostFlow/pull/256) |
| **D4** | Candidate cutover (Shell ≠ D2 slots) | ✅ [#257](https://github.com/igortatarynovich/HostFlow/pull/257)/[#258](https://github.com/igortatarynovich/HostFlow/pull/258) |
| **D5** | Client cutover | ✅ [#259](https://github.com/igortatarynovich/HostFlow/pull/259)/[#260](https://github.com/igortatarynovich/HostFlow/pull/260) |
| **D6** | Sales Order cutover | ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262) |
| **D7** | Vacancy cutover | [brief](entity-workspace-d7-vacancy-cutover.md) (feat locked) |

---

## Entity Workspace D6 Cutover Gate (CI — mandatory after feat)

Named step: **Entity Workspace D6 Cutover Gate**  
(`tests/platform/test_entity_workspace_d6_cutover_gate.py`). Full-repo pytest red does not waive it. D1 / D2 / D3 / D4 / D5 gates stay green.

- Consumer = Sales Order (`SalesOrderDetailPage`); HR / Vacancy / Services `/app/orders` not cut over  
- D2 slot catalog unchanged; D2 `documents` still cannot be enabled  
- Shell `EntityWorkspaceSectionId` not collapsed into composition slots  
- PX mock `order` ≠ D6 consumer  
- Communication fold = `company` via `company_id`; not `service_order`  
- No Entity Catalog Passport mint  
- Entity Foundation maturity stays 🔄 (not ✅)

---

## In scope (this docs PR)

1. This brief.  
2. Close D5 with merge refs [#259](https://github.com/igortatarynovich/HostFlow/pull/259)/[#260](https://github.com/igortatarynovich/HostFlow/pull/260).  
3. Point Product Track / queue / roadmap / AGENTS here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Named **Entity Workspace D6 Cutover Gate** — Sales Order bound to D2 enabled slots; reserved D2 `documents` cannot be enabled; Shell nav not collapsed; no Catalog Passport; D1–D5 gates still green.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. Sales Order detail (`SalesOrderDetailPage` / `/app/sales/orders/:id`) composes D2 slots via public adapters — **no** HR/Vacancy/Services-order cutover, **no** D2 `documents` enable.  
4. Pointers stay on D6 until D7 brief opens. *(closed — Product Track → D7 brief)*

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Vacancy cutover | D7 brief |
| HR employee / Services `/app/orders` cutover | D8+ |
| D2 `documents` enable / Documents lifecycle | Phase E |
| Catalog Passport / Manifest | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land | Engineering / Kit sync |
| Full `SalesOrderDetailPage` rewrite onto Shell | Not required for D6 cutover |
| New Communication origin `sales_order` | Out — fold via `company` |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace (ADR-010); Sales owns Sales Order overview body; platform slots owned by their platforms |
| 2 Exists? | D1 Shell adapter yes; D2 catalog yes; Sales Inquiry D3 bound; Candidate D4 bound; Client D5 bound; Sales Order D2 compose **new** (this) |
| 3 Adapter | EntityWorkspaceShell optional reuse (D1 adapter, not a new shell); Communication / Forms via their public adapters only |
| 4 Boundary | No HR/Vacancy/Services `/app/orders`; no Shell/D2 collapse; no D2 `documents` enable; no Passport; no Forms P3–P5; no fifth shell; PX mock `order` ≠ this consumer |
| 5 Settings | No new Manifest keys |
| 6 SoT | Slot catalog = D2 + `compositionSlots.ts`; Shell nav = adapter; Sales Order overview body stays module-owned |
| 7 Events | None new |
| 8 Requires | D5 ✅ · D4 ✅ · D3 ✅ · D2 ✅ · D1 ✅ · Forms Foundation ✅ · Communication foundation for compose |
| 9 License | None new |
| 10 Public contract | Additive Sales Order binding; no Catalog Passport; no DTO bump; no new Communication origin type |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged ([#261](https://github.com/igortatarynovich/HostFlow/pull/261))
- [x] Named Entity Workspace D6 Cutover Gate (feat)
- [x] Consumer = Sales Order; HR / Vacancy / Services `/app/orders` not cut over
- [x] D2 `documents` cannot be enabled; order docs surface is not that enable
- [x] Shell `EntityWorkspaceSectionId` not collapsed into D2 slots
- [x] No Catalog Passport mint
- [x] D1–D5 gates still green; Entity Foundation remains 🔄
- [x] Forms P3–P5 and Documents Phase E stay out of Product Track
- Product Track → [D7 Vacancy Cutover](entity-workspace-d7-vacancy-cutover.md) (brief; feat locked)

---

## DoD

- [x] Brief sealed with Sales Order consumer + Shell≠D2 distinction + Sales≠Services order + in/out + acceptance  
- [x] Queue + roadmap + AGENTS point at this brief  
- [x] D5 marked complete with #260 merge ref  
- [x] Feat: Sales Order bound to D2 enabled slots; named Cutover Gate  

---

## History

- 2026-08-15: D6 ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262) (`346f6fcc` / merge `bc819768`). Next = [D7 Vacancy Cutover](entity-workspace-d7-vacancy-cutover.md) (brief; feat locked).
- 2026-08-15: D6 feat — named **Entity Workspace D6 Cutover Gate**; Sales Order bound to D2 enabled slots; HR/Vacancy/Services `/app/orders` out; no Passport. Next = D7 brief (locked).
- 2026-08-15: D6 brief opened — Sales Order cutover; HR / Vacancy / Services `/app/orders` locked as D7+. Feat locked. D5 ✅ [#259](https://github.com/igortatarynovich/HostFlow/pull/259)/[#260](https://github.com/igortatarynovich/HostFlow/pull/260) (`64289c22` / merge `069f441d`).
