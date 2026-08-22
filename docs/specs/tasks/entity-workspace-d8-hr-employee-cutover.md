# Entity Workspace D8 — HR Employee Cutover (Phase D)

**Status:** **COMPLETE** ([#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266) · `24d758f0` · merge `fae8202e`)  
**Next:** [D9 Services Order Cutover](entity-workspace-d9-services-order-cutover.md) ✅ → [Documents Platform E1](documents-platform-e1-contract-seal.md) ✅ → [Documents Platform E2](documents-platform-e2-public-contract.md) ✅ → [Documents Platform E3](documents-platform-e3-first-consumer-bind.md) ✅ → [Documents Platform E4](documents-platform-e4-candidate-document-link.md) (Candidate Document Link; feat locked)  
**Branch (docs):** `docs/entity-workspace-d8-hr-employee-cutover` ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265)  
**Branch (code):** `feat/entity-workspace-d8-hr-employee-cutover` ✅ [#266](https://github.com/igortatarynovich/HostFlow/pull/266)  
**Parents:** [D7 Vacancy Cutover](entity-workspace-d7-vacancy-cutover.md) ✅ · [D6 Sales Order Cutover](entity-workspace-d6-sales-order-cutover.md) ✅ · [D5 Client Cutover](entity-workspace-d5-client-cutover.md) ✅ · [D4 Candidate Cutover](entity-workspace-d4-candidate-cutover.md) ✅ · [D3 Consumer Cutover](entity-workspace-d3-consumer-cutover.md) ✅ · [D2 Composition Contract](entity-workspace-d2-composition-contract.md) ✅ · [D1 Contract Seal](entity-workspace-d1-contract-seal.md) ✅ · [Sequential queue](sales-to-comms-sequential-queue.md) · [Platform Completion Roadmap § Phase D](../architecture/platform-completion-roadmap.md) · [ADR-010](../architecture/ADR-010-unified-resource-list-shell.md) · [A2-F7](../gates/platform-governance-review-a2.md) · [UI constitution §3.3](../architecture/ui-constitution-v1.md)

> D7 bound Vacancy to the D2 slot catalog.  
> D8 binds **HR employee** (`HrEmployeeDetailPage` / `/app/hr/employees/:employeeId`) to that catalog — one remaining consumer, same enabled slots.  
> D8 does **not** enable D2 `documents`, mint Catalog Passport, re-bind Candidate, or cut over Services `/app/orders`.

**Naming (do not collapse):** this **Entity Workspace D8** is not D7 Vacancy cutover, not D6 Sales Order cutover, not D5 Client cutover, not D4 Candidate cutover, not D3 Sales Inquiry cutover, not D2 composition contract, not D1 contract seal, not PX chrome land, not Documents Phase E. Shell `documents` **nav** ≠ D2 `documents` **composition slot**. HR employee here is the workforce operational card (`HrEmployeeDetailPage`), **not** Candidate `EntityWorkspacePage`, **not** `HrHandoffDetailPage`, **not** Services-module `service_order` (`/app/orders`), and **not** ADR-032 Vacancy.

---

## Why this slice

Product Track is Sales → Communication. ADR-032 Sales chain is bound: Client (D5) → Sales Order (D6) → Vacancy (D7).  
The remaining Entity Workspace hole that operators hit next: HR employee detail is still a one-off card at `/app/hr/employees/:employeeId` (`HrEmployeeDetailPage`) beside the D2 catalog.

On tip today:

| Surface | What it is | D8 status |
|---------|------------|-----------|
| Sales Inquiry (`ApplicationSalesDetailPanel`) | D3 first consumer | ✅ leave as-is |
| Candidate `EntityWorkspacePage` | D4 consumer; D1 Shell adapter | ✅ leave as-is |
| Client (`Companies` · `/app/clients/:id`) | D5 consumer | ✅ leave as-is |
| Sales Order (`SalesOrderDetailPage` · `/app/sales/orders/:id`) | D6 consumer; ADR-032 commercial deal | ✅ leave as-is |
| Vacancy (`VacancyDetail` · `/app/vacancies/:id`) | D7 consumer; ADR-032 Recruitment fulfillment | ✅ leave as-is |
| HR employee (`HrEmployeeDetailPage` · `/app/hr/employees/:employeeId`) | Workforce operational workspace; not on D2 catalog | **this consumer** |
| HR handoff (`HrHandoffDetailPage`) | Handoff case card | **Out of D8** |
| Services `/app/orders` (`service_order`) | Services fulfillment; not Sales Order | **Out of D8** |

Without an explicit HR employee binding, HR will keep a parallel employee shell, and a later bind of `HrHandoffDetailPage`, Candidate (already D4), or Services `/app/orders` will be misread as this cutover — or as D2 `documents` enable (dossier / `#hr-employee-linked-documents` / Documents hub).

---

## Goal

HR employee composes D2 **enabled** slots; Shell nav (if adopted) stays adapter-only:

```text
HR employee detail (HR-owned overview body)
  ├── overview          ← required; HR-owned
  ├── timeline          ← content slot (not a second Activity product)
  ├── communication     ← Communication public contracts / adapters only
  ├── forms             ← Forms public contracts only
  ├── documents         ← reserved empty (Phase E)
  └── context-rail      ← D1 chrome slot
```

Modules configure **which enabled slots** they turn on. They do **not** invent new platform slot kinds (`contacts` / `relations` / `candidates` / `notes` / `billing` / `dossier` / `payroll` / `zus` as D2 slots). Dossier sections, employment decision, work-eligibility journey, contract preview, post-approval payroll/ZUS, and `#hr-employee-linked-documents` stay **module nav**. Shell `EntityWorkspaceSectionId` stays adapter navigation — **not** the composition SoT.

**Hard distinction (unchanged from D7):**

| Id | Contract | D8 rule |
|----|----------|---------|
| Shell `documents` | `EntityWorkspaceSectionId` adapter nav | May exist as **module nav**; not a D2 slot |
| HR dossier / `#hr-employee-linked-documents` / Documents hub links | `HrEmployeeDetailPage` / `EmployeeDossierView` | Module nav; **not** D2 `documents` enable |
| D2 `documents` | `compositionSlots.ts` platform slot | **Must stay reserved** until Phase E |
| HR employee | `/app/hr/employees/:employeeId` · `HrEmployeeDetailPage` | **this consumer** |
| Candidate | D4 `EntityWorkspacePage` | ✅ leave as-is — **not** a re-bind |
| HR handoff | `HrHandoffDetailPage` | **Out of D8** |
| Vacancy | ADR-032 `/app/vacancies/:id` | D7 ✅ — leave as-is |
| Services order | `/app/orders` · `service_order` | **Out of D8** |

D8 **must not** map the dossier / linked-documents section / Documents hub → `ENTITY_WORKSPACE_ENABLED_SLOT_IDS`.

---

## Consumer (normative)

**HR employee** (workforce operational profile, live route `/app/hr/employees/:employeeId`, page `HrEmployeeDetailPage`) is the D8 cutover target. Overview body is **HR-owned**. Employment-case mode on the same page (inbox review case) is still this consumer.

**Cutover means:**

1. HR employee detail declares D2 enabled slots ⊆ `{overview, timeline, communication, forms, context-rail}`.  
2. Platform slots (`communication`, `forms`) go through public adapters only (Architecture Rule 2).  
3. Communication lists threads via public `listCommunicationThreads`. Fold by `employee.candidate_id` as `entityType: 'candidate'` (existing Communication origin; same fold family as D4 Candidate). Do **not** mint a new `workforce_employee` / `hr_employee` Communication origin. Do **not** query `entityType: 'service_order'`. If `candidate_id` is absent, the slot stays empty / Inbox hub — do not invent a substitute origin.  
4. Forms uses public `listFormsPlatformHandlers()` (`/platform/forms/handlers`). Do **not** invent an HR-employee handler; existing handlers are enough to prove the adapter.  
5. Shell `EntityWorkspaceSectionId` is not collapsed into `EntityWorkspaceSlotId`. Dossier / payroll / ZUS / eligibility / `#hr-employee-linked-documents` are not D2 slots.  
6. D2 `documents` stays reserved / cannot be enabled. The dossier documents section is not that enable.  
7. No parallel HR employee workspace / fifth shell beside this compose. Reusing D1 `EntityWorkspaceShell` as adapter chrome is allowed; inventing a new shell kind is not. A full `HrEmployeeDetailPage` rewrite is **not** required for cutover.  
8. Do **not** re-bind D4 Candidate. Folding Communication via `candidate` does not make Candidate the D8 consumer.

**Cutover does not mean:** Documents Phase E; Catalog Passport; Services `/app/orders` cutover; `HrHandoffDetailPage` cutover; Kit Baseline chrome file land; Forms P3–P5; collapsing Candidate into this consumer; promoting HR Workspace into the kit; treating dossier / payroll / ZUS as D2 slots.

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
D9  → Services order (opened as D9 brief)
```

D8 **must not**:

- enable D2 `documents` or treat the dossier / `#hr-employee-linked-documents` / Documents hub as that enable  
- collapse `EntityWorkspaceSectionId` or HR dossier sections into `compositionSlots.ts`  
- cut over Services-module `/app/orders` or `HrHandoffDetailPage`  
- re-bind Vacancy / Sales Order / Client / Candidate / Sales Inquiry  
- treat Candidate fold as a D4 re-cutover  
- mint Entity Catalog Passport / Manifest  
- mint a new Communication origin type for `workforce_employee` / `hr_employee`  
- land Kit Baseline chrome as a substitute for cutover  
- open Documents Phase E, Billing, or AI  
- reopen Forms P3 Publish UI / P4 Themes / P5 Analytics  
- invent a second HR employee shell or promote HR Workspace into the kit  
- rewrite `HrEmployeeDetailPage` as the definition of cutover  

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

## Entity Workspace D8 Cutover Gate (CI — mandatory after feat)

Named step: **Entity Workspace D8 Cutover Gate**  
(`tests/platform/test_entity_workspace_d8_cutover_gate.py`). Full-repo pytest red does not waive it. D1 / D2 / D3 / D4 / D5 / D6 / D7 gates stay green.

- Consumer = HR employee (`HrEmployeeDetailPage`); Services `/app/orders` and `HrHandoffDetailPage` not cut over  
- D2 slot catalog unchanged; D2 `documents` still cannot be enabled  
- Shell `EntityWorkspaceSectionId` not collapsed into composition slots  
- Dossier / payroll / ZUS / `#hr-employee-linked-documents` ≠ D2 slots  
- Candidate page is not re-bound; Communication fold = `candidate` via `candidate_id`; not `service_order`; no new `workforce_employee` origin  
- No Entity Catalog Passport mint  
- Entity Foundation maturity stays 🔄 (not ✅)

---

## In scope (this docs PR)

1. This brief.  
2. Close D7 with merge refs [#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264).  
3. Point Product Track / queue / roadmap / AGENTS here.  
4. Feat locked until this brief merges.

## In scope (feat PR — after this brief)

1. Named **Entity Workspace D8 Cutover Gate** — HR employee bound to D2 enabled slots; reserved D2 `documents` cannot be enabled; Shell nav not collapsed; no Catalog Passport; D1–D7 gates still green.  
2. Architecture Review Checklist (10 questions) in the feat PR description.  
3. HR employee detail (`HrEmployeeDetailPage` / `/app/hr/employees/:employeeId`) composes D2 slots via public adapters — **no** Services-order / handoff-page cutover, **no** D2 `documents` enable, **no** Candidate re-bind.  
4. Pointers moved to D9 when the D9 brief opened.

---

## Out of this slice

| Deferred | Owner |
|----------|--------|
| Services `/app/orders` cutover | [D9 brief](entity-workspace-d9-services-order-cutover.md) |
| `HrHandoffDetailPage` cutover | later D / out |
| D2 `documents` enable / Documents lifecycle | Phase E |
| Catalog Passport / Manifest | Later D slice (+ RFC if Catalog shape) |
| Kit Baseline chrome file land | Engineering / Kit sync |
| Full `HrEmployeeDetailPage` rewrite onto Shell | Not required for D8 cutover |
| New Communication origin `workforce_employee` | Out — fold via `candidate` |
| Forms P3 / P4 / P5 | Locked |
| Stage 5 settings / R6 | Unchanged |
| C2.4 Scheduling | Frozen |

---

## Architecture Review (L0 — this feat)

| # | Answer |
|---|--------|
| 1 Owner | Platform UI / Workspace (ADR-010); HR owns employee overview body; platform slots owned by their platforms |
| 2 Exists? | D1 Shell adapter yes; D2 catalog yes; Sales Inquiry D3 bound; Candidate D4 bound; Client D5 bound; Sales Order D6 bound; Vacancy D7 bound; HR employee D2 compose **new** (this) |
| 3 Adapter | EntityWorkspaceShell optional reuse (D1 adapter, not a new shell); Communication / Forms via their public adapters only |
| 4 Boundary | No Services `/app/orders`; no `HrHandoffDetailPage`; no Candidate re-bind; no Shell/D2 collapse; no D2 `documents` enable; no Passport; no Forms P3–P5; no fifth shell |
| 5 Settings | No new Manifest keys |
| 6 SoT | Slot catalog = D2 + `compositionSlots.ts`; Shell nav = adapter; HR employee overview body stays HR-owned |
| 7 Events | None new |
| 8 Requires | D7 ✅ · D6 ✅ · D5 ✅ · D4 ✅ · D3 ✅ · D2 ✅ · D1 ✅ · Forms Foundation ✅ · Communication foundation for compose |
| 9 License | None new |
| 10 Public contract | Additive HR employee binding; no Catalog Passport; no DTO bump; no new Communication origin type |

Does **not** amend L0 P-rules. Does **not** rewrite Catalog.

---

## Acceptance

- [x] Brief merged ([#265](https://github.com/igortatarynovich/HostFlow/pull/265))
- [x] Named Entity Workspace D8 Cutover Gate (feat)
- [x] Consumer = HR employee; Services `/app/orders` and `HrHandoffDetailPage` not cut over
- [x] D2 `documents` cannot be enabled; dossier / linked-documents / Documents hub are not that enable
- [x] Shell `EntityWorkspaceSectionId` not collapsed into D2 slots
- [x] No Catalog Passport mint
- [x] D1–D7 gates still green; Entity Foundation remains 🔄
- [x] Forms P3–P5 and Documents Phase E stay out of Product Track
- [x] Product Track stays D8 until D9 brief opens

---

## DoD

- [x] Brief sealed with HR employee consumer + Shell≠D2 distinction + HR employee≠Candidate≠handoff≠Services order + in/out + acceptance  
- [x] Queue + roadmap + AGENTS point at this brief  
- [x] D7 marked complete with #264 merge ref  
- [x] Feat: HR employee bound to D2 enabled slots; named Cutover Gate  

---

## History

- 2026-08-17: D8 ✅ [#265](https://github.com/igortatarynovich/HostFlow/pull/265)/[#266](https://github.com/igortatarynovich/HostFlow/pull/266) (`24d758f0` / merge `fae8202e`). Next = [D9 Services Order Cutover](entity-workspace-d9-services-order-cutover.md) (feat locked).
- 2026-08-17: D8 feat — named **Entity Workspace D8 Cutover Gate**; HR employee bound to D2 enabled slots; Services `/app/orders` / `HrHandoffDetailPage` out; no Passport. Next = D9 brief (locked).
- 2026-08-17: D8 brief opened — HR employee cutover; Services `/app/orders` locked as D9+. Feat locked. D7 ✅ [#263](https://github.com/igortatarynovich/HostFlow/pull/263)/[#264](https://github.com/igortatarynovich/HostFlow/pull/264) (`9582c00d` / merge `7484f98e`).
