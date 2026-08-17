# Entity Workspace D7 — Vacancy Cutover (Phase D)

**Status:** **COMPLETE** ([#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264) · `9582c00d` · merge `7484f98e`)  
**Next:** [D8 HR Employee Cutover](entity-workspace-d8-hr-employee-cutover.md) ✅ → [D9 Services Order Cutover](entity-workspace-d9-services-order-cutover.md) (brief; feat locked)  
**Branch (docs):** `docs/entity-workspace-d7-vacancy-cutover` ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263)  
**Branch (code):** `feat/entity-workspace-d7-vacancy-cutover` ✅ [#264](https://github.com/igortatarynovich/HostFlow/pull/264)  
**Parents:** [D6 Sales Order Cutover](entity-workspace-d6-sales-order-cutover.md) ✅ · [D5 Client Cutover](entity-workspace-d5-client-cutover.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [D3 Consumer Cutover](entity-workspace-d3-consumer-cutover.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [D1 Contract Seal](entity-workspace-d1-contract-seal.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [ADR-032](../architecture/ADR-032-client-order-vacancy-flight-chain.md) · [A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md)

> D6 bound Sales Order to the D2 slot catalog.  
> D7 binds **Vacancy** (`Vacancy` / `/app/vacancies/:id`) to that catalog — one remaining consumer, same enabled slots.  
> D7 does **not** enable D2 `documents`, mint Catalog Passport, or cut over HR employee / Services `/app/orders`.

**Naming (do not collapse):** this **Entity Workspace D7** is not D6 Sales Order cutover, not D5 Client cutover, not D4 Candidate cutover, not D3 Sales Inquiry cutover, not D2 composition contract, not D1 contract seal, not PX chrome land, not Documents Phase E. Shell `documents` **nav** ≠ D2 `documents` **composition slot**. Vacancy here is ADR-032 Recruitment fulfillment of a Sales Order Line (`/app/vacancies/:id`), **not** HR employee, **not** Services-module `service_order` (`/app/orders`), and **not** the PX mock vacancy relation on `MOCK_ORDER_MODEL`.

---

## Why this slice

Product Track is Sales → Communication. ADR-032 chain: Client → Sales Order → **Vacancy**.  
D3 bound Sales Inquiry. D5 bound Client. D6 bound Sales Order.  
The remaining Sales-chain hole: Vacancy detail is still a one-off card at `/app/vacancies/:id` (`VacancyDetail`) beside the D2 catalog.

On tip today:

| Surface | What it is | D7 status |
|---------|------------|-----------|
| Sales Inquiry (`ApplicationSalesDetailPanel`) | D3 first consumer | ✅ leave as-is |
| Candidate `EntityWorkspacePage` | D4 consumer; D1 Shell adapter | ✅ leave as-is |
| Client (`Companies` · `/app/clients/:id`) | D5 consumer | ✅ leave as-is |
| Sales Order (`SalesOrderDetailPage` · `/app/sales/orders/:id`) | D6 consumer; ADR-032 commercial deal | ✅ leave as-is |
| Vacancy (`VacancyDetail` · `/app/vacancies/:id`) | ADR-032 Recruitment fulfillment of a Sales Order Line; not on D2 catalog | **this consumer** |
| HR employee (`HrEmployeeDetailPage`) | HR module workspace | **Out of D7** |
| Services `/app/orders` (`service_order`) | Services fulfillment; not Sales Order | **Out of D7** |

Without an explicit Vacancy binding, Recruitment will keep a parallel vacancy shell, and a later bind of HR employee or Services `/app/orders` (or PX mock vacancy-on-order) will be misread as this cutover — or as D2 `documents` enable.

---

## Goal

Vacancy composes D2 **enabled** slots; Shell nav (if adopted) stays adapter-only:

```text
Vacancy detail (Recruitment-owned overview body)
  ├── overview          ← required; Recruitment-owned
  ├── timeline          ← content slot (not a second Activity product)
  ├── communication     ← Communication public contracts / adapters only
  ├── forms             ← Forms public contracts only
  ├── documents         ← reserved empty (Phase E)
  └── context-rail      ← D1 chrome slot
```

Modules configure **which enabled slots** they turn on. They do **not** invent new platform slot kinds (`contacts` / `relations` / `candidates` / `notes` / `billing` as D2 slots). Vacancy tabs `info` / `candidates` / `notes` stay **module nav**. Shell `EntityWorkspaceSectionId` stays adapter navigation — **not** the composition SoT.

**Hard distinction (unchanged from D6):**

| Id | Contract | D7 rule |
|----|----------|---------|
| Shell `documents` | `EntityWorkspaceSectionId` adapter nav | May exist as **module nav**; not a D2 slot |
| Vacancy docs section | `VacancyDetail` info-tab link to Documents hub | Module nav; **not** D2 `documents` enable |
| D2 `documents` | `compositionSlots.ts` platform slot | **Must stay reserved** until Phase E |
| Vacancy | ADR-032 `/app/vacancies/:id` | **this consumer** |
| HR employee | `HrEmployeeDetailPage` | **Out of D7** |
| Services order | `/app/orders` · `service_order` | **Out of D7** |
| Sales Order | ADR-032 `/app/sales/orders/:id` | D6 ✅ — leave as-is |
| PX mock vacancy relation | `MOCK_ORDER_MODEL` relation `kind: 'vacancy'` | Chrome mock; **not** this consumer |

D7 **must not** map the Vacancy docs section / `requires_documents` criteria → `ENTITY_WORKSPACE_ENABLED_SLOT_IDS`.

---

## Consumer (normative)

**Vacancy** (`Vacancy`, live route `/app/vacancies/:id`, page `VacancyDetail` via `VacancyDetailRoute`) is the D7 cutover target. Overview body is **Recruitment-owned** (ADR-032).

**Cutover means:**

1. Vacancy detail declares D2 enabled slots ⊆ `{overview, timeline, communication, forms, context-rail}`.  
2. Platform slots (`communication`, `forms`) go through public adapters only (Architecture Rule 2).  
3. Communication lists threads via public `listCommunicationThreads`. Fold by `Vacancy.company_id` as `entityType: 'company'` (same fold as D5 Client / D6 Sales Order). Do **not** mint a new `vacancy` Communication origin. Do **not** query `entityType: 'service_order'`.  
4. Forms uses public `listFormsPlatformHandlers()` (`/platform/forms/handlers`). Do **not** invent a Vacancy handler; existing handlers are enough to prove the adapter.  
5. Shell `EntityWorkspaceSectionId` is not collapsed into `EntityWorkspaceSlotId`. Vacancy tabs `info` / `candidates` / `notes` are not D2 slots.  
6. D2 `documents` stays reserved / cannot be enabled. The Vacancy info-tab documents section is not that enable.  
7. No parallel Vacancy workspace / fifth shell beside this compose. Reusing D1 `EntityWorkspaceShell` as adapter chrome is allowed; inventing a new shell kind is not. A full `VacancyDetail` rewrite is **not** required for cutover.

**Cutover does not mean:** Documents Phase E; Catalog Passport; HR employee / Services `/app/orders` cutover; Kit Baseline chrome file land; Forms P3–P5; collapsing PX mock vacancy-on-order into this consumer; promoting Vacancy Workspace into the kit; treating pipeline `candidates` tab as a D2 slot.

---

## Locked principle

```text
D1  → who owns Entity Workspace + chrome/adapter boundary
D2  → which slots exist and how platforms compose
D3  → first consumer (Sales Inquiry)
D4  → Candidate binds to D2 slots; Shell nav ≠ composition
D5  → Client binds to D2 slots
D6  → Sales Order binds to D2 slots
D7  → Vacancy binds to D2 slots (this)
D8  → HR employee (opened as D8 brief)
D9  → Services order (opened as D9 brief)
```

D7 **must not**:

- enable D2 `documents` or treat the Vacancy docs section as that enable  
- collapse `EntityWorkspaceSectionId` or Vacancy tabs into `compositionSlots.ts`  
- cut over HR employee or Services-module `/app/orders`  
- re-bind Sales Order / Client / Candidate / Sales Inquiry  
- bind PX mock vacancy relation / `MOCK_ORDER_MODEL` as the D7 consumer  
- mint Entity Catalog Passport / Manifest  
- mint a new Communication origin type for `vacancy`  
- land Kit Baseline chrome as a substitute for cutover  
- open Documents Phase E, Billing, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- invent a second Vacancy shell or promote Vacancy Workspace into the kit  
- rewrite `VacancyDetail` as the definition of cutover  

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
| **D7** | Vacancy cutover | ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264) |
| **D8** | HR employee cutover | ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266) |
| **D9** | Services `/app/orders` | [brief](entity-workspace-d9-services-order-cutover.md) (feat locked) |

---

## Entity Workspace D7 Cutover Gate (CI — mandatory after feat)

Named step: **Entity Workspace D7 Cutover Gate**  
(`tests/platform/test_entity_workspace_d7_cutover_gate.py`). Full-repo pytest red does not waive it. D1 / D2 / D3 / D4 / D5 / D6 gates stay green.

- Consumer = Vacancy (`VacancyDetail`); HR employee / Services `/app/orders` not cut over  
- D2 slot catalog unchanged; D2 `documents` still cannot be enabled  
- Shell `EntityWorkspaceSectionId` not collapsed into composition slots  
- Vacancy tabs `info` / `candidates` / `notes` ≠ D2 slots  
- PX mock vacancy relation ≠ D7 consumer  
- Communication fold = `company` via `company_id`; not `service_order`; no new `vacancy` origin  
- No Entity Catalog Passport mint  
- Entity Foundation maturity stays 🔄 (not ✅)

---

## In scope (this docs PR)

1. This brief.  
2. Close D6 with merge refs [#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262).  
3. Point Product Track / queue / roadmap / AGENTS here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Named **Entity Workspace D7 Cutover Gate** — Vacancy bound to D2 enabled slots; reserved D2 `documents` cannot be enabled; Shell nav not collapsed; no Catalog Passport; D1–D6 gates still green.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. Vacancy detail (`VacancyDetail` / `/app/vacancies/:id`) composes D2 slots via public adapters — **no** HR employee / Services-order cutover, **no** D2 `documents` enable.  
4. Pointers moved to D8 when the D8 brief opened.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| HR employee / Services `/app/orders` cutover | D8+ |
| D2 `documents` enable / Documents lifecycle | Phase E |
| Catalog Passport / Manifest | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land | Engineering / Kit sync |
| Full `VacancyDetail` rewrite onto Shell | Not required for D7 cutover |
| New Communication origin `vacancy` | Out — fold via `company` |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace (ADR-010); Recruitment owns Vacancy overview body; platform slots owned by their platforms |
| 2 Exists? | D1 Shell adapter yes; D2 catalog yes; Sales Inquiry D3 bound; Candidate D4 bound; Client D5 bound; Sales Order D6 bound; Vacancy D2 compose **new** (this) |
| 3 Adapter | EntityWorkspaceShell optional reuse (D1 adapter, not a new shell); Communication / Forms via their public adapters only |
| 4 Boundary | No HR employee / Services `/app/orders`; no Shell/D2 collapse; no D2 `documents` enable; no Passport; no Forms P3–P5; no fifth shell; PX mock vacancy ≠ this consumer |
| 5 Settings | No new Manifest keys |
| 6 SoT | Slot catalog = D2 + `compositionSlots.ts`; Shell nav = adapter; Vacancy overview body stays Recruitment-owned |
| 7 Events | None new |
| 8 Requires | D6 ✅ · D5 ✅ · D4 ✅ · D3 ✅ · D2 ✅ · D1 ✅ · Forms Foundation ✅ · Communication foundation for compose |
| 9 License | None new |
| 10 Public contract | Additive Vacancy binding; no Catalog Passport; no DTO bump; no new Communication origin type |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged ([#263](https://github.com/igortatarynovich/HostFlow/pull/263))
- [x] Named Entity Workspace D7 Cutover Gate (feat)
- [x] Consumer = Vacancy; HR employee / Services `/app/orders` not cut over
- [x] D2 `documents` cannot be enabled; Vacancy docs section is not that enable
- [x] Shell `EntityWorkspaceSectionId` not collapsed into D2 slots
- [x] No Catalog Passport mint
- [x] D1–D6 gates still green; Entity Foundation remains 🔄
- [x] Forms P3–P5 and Documents Phase E stay out of Product Track
- [x] Product Track stays D7 until D8 brief opens

---

## DoD

- [x] Brief sealed with Vacancy consumer + Shell≠D2 distinction + Vacancy≠HR≠Services order + in/out + acceptance  
- [x] Queue + roadmap + AGENTS point at this brief  
- [x] D6 marked complete with #262 merge ref  
- [x] Feat: Vacancy bound to D2 enabled slots; named Cutover Gate  

---

## History

- 2026-08-17: D7 ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264) (`9582c00d` / merge `7484f98e`). Next = [D8 HR Employee Cutover](entity-workspace-d8-hr-employee-cutover.md) (feat locked).
- 2026-08-15: D7 feat — named **Entity Workspace D7 Cutover Gate**; Vacancy bound to D2 enabled slots; HR employee / Services `/app/orders` out; no Passport. Next = D8 brief (locked).
- 2026-08-15: D7 brief opened — Vacancy cutover; HR employee / Services `/app/orders` locked as D8+. Feat locked. D6 ✅ [#261](https://github.com/igortatarynovich/HostFlow/pull/261)/[#262](https://github.com/igortatarynovich/HostFlow/pull/262) (`346f6fcc` / merge `bc819768`).
