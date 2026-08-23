# Entity Workspace D9 — Services Order Cutover (Phase D)

**Status:** **COMPLETE** ([#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) · merge `28978a1f`)  
**Next:** [Documents Platform E1](documents-platform-e1-contract-seal.md) ✅ → [Documents Platform E2](documents-platform-e2-public-contract.md) ✅ → [Documents Platform E3](documents-platform-e3-first-consumer-bind.md) ✅ → [Documents Platform E4](documents-platform-e4-candidate-document-link.md) ✅ → [Documents Platform E5](documents-platform-e5-candidate-storage-bridge.md) ✅ → [Documents Platform E6](documents-platform-e6-document-expiry.md) (brief; feat locked)  
**Branch (docs):** `docs/entity-workspace-d9-services-order-cutover` ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267)  
**Branch (code):** `feat/entity-workspace-d9-services-order-cutover` ✅ [#268](https://github.com/igortatarynovich/HostFlow/pull/268)  
**Parents:** [D8 HR Employee Cutover](entity-workspace-d8-hr-employee-cutover.md) ✅ · [D7 Vacancy Cutover](entity-workspace-d7-vacancy-cutover.md) ✅ · [D6 Sales Order Cutover](entity-workspace-d6-sales-order-cutover.md) ✅ · [D5 Client Cutover](entity-workspace-d5-client-cutover.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [D3 Consumer Cutover](entity-workspace-d3-consumer-cutover.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [D1 Contract Seal](entity-workspace-d1-contract-seal.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [ADR-032](../architecture/ADR-032-client-order-vacancy-flight-chain.md) · [A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md)

> D8 bound HR employee to the D2 slot catalog.  
> D9 binds **Services order** (`ServicesPage` / `/app/orders` · `service_order`) to that catalog — last named consumer, same enabled slots.  
> D9 does **not** enable D2 `documents`, mint Catalog Passport, re-bind Sales Order / HR employee, or cut over `HrHandoffDetailPage`.

**Naming (do not collapse):** this **Entity Workspace D9** is not D8 HR employee cutover, not D7 Vacancy cutover, not D6 Sales Order cutover, not D5 Client cutover, not D4 Candidate cutover, not D3 Sales Inquiry cutover, not D2 composition contract, not D1 contract seal, not PX chrome land, not Documents Phase E, not Billing Platform Phase F. Shell `documents` **nav** ≠ D2 `documents` **composition slot**. Services order here is Services-module fulfillment (`service_order`, live shell `ServicesPage`), **not** ADR-032 Sales Order (`SalesOrderDetailPage` / `/app/sales/orders/:id`), **not** HR employee, **not** `HrHandoffDetailPage`, and **not** Vacancy.

---

## Why this slice

Product Track is Sales → Communication. Named Entity Workspace consumers on tip: Sales Inquiry (D3) · Candidate (D4) · Client (D5) · Sales Order (D6) · Vacancy (D7) · HR employee (D8).  
The remaining hole operators hit next: Services fulfillment order is still a one-off workspace at `/app/orders` (`ServicesPage`, same shell as `/app/services?tab=orders`) beside the D2 catalog.

On tip today:

| Surface | What it is | D9 status |
|---------|------------|-----------|
| Sales Inquiry (`ApplicationSalesDetailPanel`) | D3 first consumer | ✅ leave as-is |
| Candidate `EntityWorkspacePage` | D4 consumer; D1 Shell adapter | ✅ leave as-is |
| Client (`Companies` · `/app/clients/:id`) | D5 consumer | ✅ leave as-is |
| Sales Order (`SalesOrderDetailPage` · `/app/sales/orders/:id`) | D6 consumer; ADR-032 commercial deal | ✅ leave as-is — **not** a re-bind |
| Vacancy (`VacancyDetail` · `/app/vacancies/:id`) | D7 consumer; ADR-032 Recruitment fulfillment | ✅ leave as-is |
| HR employee (`HrEmployeeDetailPage` · `/app/hr/employees/:employeeId`) | D8 consumer | ✅ leave as-is |
| HR handoff (`HrHandoffDetailPage`) | Handoff case card | **Out of D9** |
| Services `/app/orders` (`service_order` · `ServicesPage`) | Services fulfillment; `/app/orders` redirects to `/app/services?tab=orders` | **this consumer** |

Without an explicit Services-order binding, Services will keep a parallel order shell, and a later bind of `HrHandoffDetailPage`, Sales Order (already D6), or the billing tab will be misread as this cutover — or as D2 `documents` enable / Phase F Billing.

---

## Goal

Services order composes D2 **enabled** slots; Shell nav (if adopted) stays adapter-only:

```text
Services order detail (Services-owned overview body)
  ├── overview          ← required; Services-owned
  ├── timeline          ← content slot (not a second Activity product)
  ├── communication     ← Communication public contracts / adapters only
  ├── forms             ← Forms public contracts only
  ├── documents         ← reserved empty (Phase E)
  └── context-rail      ← D1 chrome slot
```

Modules configure **which enabled slots** they turn on. They do **not** invent new platform slot kinds (`contacts` / `relations` / `candidates` / `notes` / `billing` / `catalog` / `analytics` as D2 slots). Services tabs `overview` / `analytics` / `catalog` / `billing` stay **module nav**. Shell `EntityWorkspaceSectionId` stays adapter navigation — **not** the composition SoT.

**Hard distinction (unchanged from D8):**

| Id | Contract | D9 rule |
|----|----------|---------|
| Shell `documents` | `EntityWorkspaceSectionId` adapter nav | May exist as **module nav**; not a D2 slot |
| Services billing tab | `ServicesPage` tab `billing` | Module nav; **not** D2 `documents` enable; **not** Phase F Billing Platform |
| D2 `documents` | `compositionSlots.ts` platform slot | **Must stay reserved** until Phase E |
| Services order | `/app/orders` · `ServicesPage` · `service_order` | **this consumer** |
| Sales Order | ADR-032 `/app/sales/orders/:id` | D6 ✅ — leave as-is — **not** a re-bind |
| HR employee | D8 `HrEmployeeDetailPage` | ✅ leave as-is |
| HR handoff | `HrHandoffDetailPage` | **Out of D9** |
| Vacancy | ADR-032 `/app/vacancies/:id` | D7 ✅ — leave as-is |

D9 **must not** map the billing / catalog / analytics tabs → `ENTITY_WORKSPACE_ENABLED_SLOT_IDS`.

---

## Consumer (normative)

**Services order** (Services-module `service_order`, live route `/app/orders` → `/app/services?tab=orders`, page `ServicesPage`, detail when `order_id` / `selectedOrderId` is live) is the D9 cutover target. Overview body is **Services-owned**. Catalog / analytics / billing tabs on the same page stay module nav.

**Cutover means:**

1. Live Services order detail declares D2 enabled slots ⊆ `{overview, timeline, communication, forms, context-rail}`. Cutover only when a live `selectedOrderId` is present; list / catalog / billing tabs are not the consumer.  
2. Platform slots (`communication`, `forms`) go through public adapters only (Architecture Rule 2).  
3. Communication lists threads via public `listCommunicationThreads`. Fold by the live order id as `entityType: 'service_order'` (existing Communication origin). Do **not** mint a new origin type. Do **not** query ADR-032 Sales Order. If `selectedOrderId` is absent, the slot stays empty / Inbox hub — do not invent a substitute origin.  
4. Forms uses public `listFormsPlatformHandlers()` (`/platform/forms/handlers`). Do **not** invent a Services-order handler; existing handlers are enough to prove the adapter.  
5. Shell `EntityWorkspaceSectionId` is not collapsed into `EntityWorkspaceSlotId`. Services tabs `overview` / `analytics` / `catalog` / `billing` are not D2 slots.  
6. D2 `documents` stays reserved / cannot be enabled. The billing tab is not that enable and is not Phase F.  
7. No parallel Services-order workspace / fifth shell beside this compose. Reusing D1 `EntityWorkspaceShell` as adapter chrome is allowed; inventing a new shell kind is not. A full `ServicesPage` rewrite is **not** required for cutover.  
8. Do **not** re-bind D6 Sales Order. Folding Communication via `service_order` does not make Sales Order the D9 consumer.

**Cutover does not mean:** Documents Phase E; Catalog Passport; `HrHandoffDetailPage` cutover; Sales Order re-bind; HR employee re-bind; Kit Baseline chrome file land; Forms P3–P5; Phase F Billing; treating billing / catalog / analytics tabs as D2 slots.

---

## Locked principle

```text
D1  → who owns Entity Workspace + chrome/adapter boundary
D2  → which slots exist and how platforms compose
D3  → first consumer (Sales Inquiry)
D4  → Candidate binds to D2 slots; Shell nav ≠ composition
D5  → Client binds to D2 slots
D6  → Sales Order binds to D2 slots
D7  → Vacancy binds to D2 slots
D8  → HR employee binds to D2 slots
D9  → Services order binds to D2 slots (this)
```

D9 **must not**:

- enable D2 `documents` or treat the billing / catalog tabs as that enable  
- collapse `EntityWorkspaceSectionId` or Services tabs into `compositionSlots.ts`  
- cut over `HrHandoffDetailPage`  
- re-bind Sales Order / Vacancy / Client / Candidate / Sales Inquiry / HR employee  
- treat `service_order` fold as a D6 Sales Order re-cutover  
- mint Entity Catalog Passport / Manifest  
- land Kit Baseline chrome as a substitute for cutover  
- open Documents Phase E, Billing Platform, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- invent a second Services-order shell or promote Services workspace into the kit  
- rewrite `ServicesPage` as the definition of cutover  

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
| **D9** | Services order cutover | ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) |

---

## Entity Workspace D9 Cutover Gate (CI — mandatory after feat)

Named step: **Entity Workspace D9 Cutover Gate**  
(`tests/platform/test_entity_workspace_d9_cutover_gate.py`). Full-repo pytest red does not waive it. D1 / D2 / D3 / D4 / D5 / D6 / D7 / D8 gates stay green.

- Consumer = Services order (`ServicesPage` / `/app/orders`); Sales Order and `HrHandoffDetailPage` not cut over  
- D2 slot catalog unchanged; D2 `documents` still cannot be enabled  
- Shell `EntityWorkspaceSectionId` not collapsed into composition slots  
- Billing / catalog / analytics tabs ≠ D2 slots  
- Sales Order page is not re-bound; Communication fold = `service_order` via live order id; no new origin type  
- No Entity Catalog Passport mint  
- Entity Foundation maturity stays 🔄 (not ✅)

---

## In scope (this docs PR)

1. This brief.  
2. Close D8 with merge refs [#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266).  
3. Point Product Track / queue / roadmap / AGENTS here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Named **Entity Workspace D9 Cutover Gate** — Services order bound to D2 enabled slots; reserved D2 `documents` cannot be enabled; Shell nav not collapsed; no Catalog Passport; D1–D8 gates still green.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. Services order detail (`ServicesPage` / `/app/orders`) composes D2 slots via public adapters — **no** Sales Order / handoff-page cutover, **no** D2 `documents` enable, **no** HR employee re-bind.  
4. Pointers stay on D9 until Documents Phase E opens. ← done — [E1](documents-platform-e1-contract-seal.md)

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| `HrHandoffDetailPage` cutover | later D / out |
| D2 `documents` enable / Documents lifecycle | Phase E |
| Catalog Passport / Manifest | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land | Engineering / Kit sync |
| Full `ServicesPage` rewrite onto Shell | Not required for D9 cutover |
| New Communication origin type | Out — fold via existing `service_order` |
| Sales Order re-bind | D6 already |
| Forms P3 / P4 / P5 | Locked |
| Billing Platform | Phase F |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace (ADR-010); Services owns order overview body; platform slots owned by their platforms |
| 2 Exists? | D1 Shell adapter yes; D2 catalog yes; Sales Inquiry D3 bound; Candidate D4 bound; Client D5 bound; Sales Order D6 bound; Vacancy D7 bound; HR employee D8 bound; Services order D2 compose **new** (this) |
| 3 Adapter | EntityWorkspaceShell optional reuse (D1 adapter, not a new shell); Communication / Forms via their public adapters only |
| 4 Boundary | No Sales Order re-bind; no `HrHandoffDetailPage`; no HR employee re-bind; no Shell/D2 collapse; no D2 `documents` enable; no Passport; no Forms P3–P5; no Phase F Billing; no fifth shell |
| 5 Settings | No new Manifest keys |
| 6 SoT | Slot catalog = D2 + `compositionSlots.ts`; Shell nav = adapter; Services order overview body stays Services-owned |
| 7 Events | None new |
| 8 Requires | D8 ✅ · D7 ✅ · D6 ✅ · D5 ✅ · D4 ✅ · D3 ✅ · D2 ✅ · D1 ✅ · Forms Foundation ✅ · Communication foundation for compose |
| 9 License | None new |
| 10 Public contract | Additive Services-order binding; no Catalog Passport; no DTO bump; no new Communication origin type |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged
- [x] Named Entity Workspace D9 Cutover Gate (feat)
- [x] Consumer = Services order; Sales Order and `HrHandoffDetailPage` not cut over
- [x] D2 `documents` cannot be enabled; billing / catalog tabs are not that enable
- [x] Shell `EntityWorkspaceSectionId` not collapsed into D2 slots
- [x] No Catalog Passport mint
- [x] D1–D8 gates still green; Entity Foundation remains 🔄
- [x] Forms P3–P5 and Documents Phase E stay out of Product Track (until D9 feat merged)
- [x] Product Track stays D9 until Documents Phase E opens — next = [E1](documents-platform-e1-contract-seal.md)

---

## DoD

- [x] Brief sealed with Services-order consumer + Shell≠D2 distinction + Services order≠Sales Order≠handoff≠HR employee + in/out + acceptance  
- [x] Queue + roadmap + AGENTS point at this brief  
- [x] D8 marked complete with #266 merge ref  
- [x] Feat: Services order bound to D2 enabled slots; named Cutover Gate  

---

## History

- 2026-08-18: D9 ✅ [#267](https://github.com/igortatarynovich/HostFlow/pull/267)/[#268](https://github.com/igortatarynovich/HostFlow/pull/268) (`28978a1f`). Next = [Documents Platform E1](documents-platform-e1-contract-seal.md) (feat locked).
- 2026-08-17: D9 feat — named **Entity Workspace D9 Cutover Gate**; Services order bound to D2 enabled slots; `HrHandoffDetailPage` / Sales Order out; no Passport. Next = Documents Phase E (locked).
- 2026-08-17: D9 brief opened — Services order cutover; `HrHandoffDetailPage` / Documents Phase E locked. Feat locked. D8 ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266) (`24d758f0` / merge `fae8202e`).
